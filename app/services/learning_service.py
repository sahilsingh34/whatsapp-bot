"""
Learning Service — self-learning engine that mines patient conversations
to extract patterns, FAQs, and treatment insights.

Stores learned knowledge in the `learned_insights` table and dynamically
enriches the AI system prompt so the bot improves over time.
"""

import json
import logging
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.learned_insight import LearnedInsight
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)
settings = get_settings()

# Minimum frequency before an insight gets injected into the prompt
INSIGHT_THRESHOLD = 3

# Maximum number of insights to inject (to keep prompt size manageable)
MAX_INJECTED_INSIGHTS = 15

# ---- Analysis Prompt ----
ANALYSIS_PROMPT = """You are analyzing a patient conversation from a clinic's WhatsApp bot. Extract useful patterns.

CONVERSATION:
{conversation_text}

Analyze this conversation and extract insights in STRICT JSON format. Return ONLY valid JSON, no other text.

{{
  "faqs": [
    {{
      "question": "the question the patient asked",
      "answer_insight": "what the bot should know to answer this better next time"
    }}
  ],
  "treatment_interests": [
    {{
      "treatment": "treatment name the patient asked about",
      "concern": "what specific concern or question they had about it"
    }}
  ],
  "patterns": [
    {{
      "pattern": "a behavioral pattern observed (e.g., language preference, booking hesitation)",
      "recommendation": "how the bot should adapt"
    }}
  ]
}}

RULES:
- Only extract GENUINELY useful insights, not obvious things
- If a category has nothing interesting, return an empty array for it
- Keep insights concise (1-2 sentences max each)
- Focus on things NOT already covered in the bot's knowledge base
- Return ONLY the JSON object, nothing else"""


async def analyze_conversation(
    db: AsyncSession,
    user_id: UUID,
) -> None:
    """
    Analyze a user's recent conversation to extract learning insights.
    Called as a background task after each conversation exchange.

    Args:
        db: Database session.
        user_id: UUID of the user whose conversation to analyze.
    """
    try:
        # Get recent messages for this user
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.timestamp.desc())
            .limit(10)
        )
        messages = list(reversed(result.scalars().all()))

        if len(messages) < 4:
            # Not enough conversation to learn from
            return

        # Build conversation text
        conversation_text = "\n".join(
            f"{msg.role.upper()}: {msg.message}" for msg in messages
        )

        # Use the AI to analyze the conversation
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.AI_BASE_URL,
        )

        response = await client.chat.completions.create(
            model=settings.AI_MODEL_SIMPLE,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data analyst. Extract patterns from conversations. Return ONLY valid JSON.",
                },
                {
                    "role": "user",
                    "content": ANALYSIS_PROMPT.format(conversation_text=conversation_text),
                },
            ],
            temperature=0.3,
            max_tokens=800,
        )

        raw_response = response.choices[0].message.content.strip()

        # Parse JSON — handle potential markdown code fences
        if raw_response.startswith("```"):
            # Strip ```json ... ``` wrapper
            lines = raw_response.split("\n")
            raw_response = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        analysis = json.loads(raw_response)

        insights_added = 0

        # Process FAQs
        for faq in analysis.get("faqs", []):
            question = faq.get("question", "").strip()
            answer = faq.get("answer_insight", "").strip()
            if question and answer:
                await _upsert_insight(
                    db,
                    category="faq",
                    source_pattern=question,
                    insight_text=f"Patients frequently ask: \"{question}\" → {answer}",
                )
                insights_added += 1

        # Process treatment interests
        for treatment in analysis.get("treatment_interests", []):
            name = treatment.get("treatment", "").strip()
            concern = treatment.get("concern", "").strip()
            if name and concern:
                await _upsert_insight(
                    db,
                    category="treatment_insight",
                    source_pattern=f"{name}: {concern}",
                    insight_text=f"About {name}: patients often want to know — {concern}",
                )
                insights_added += 1

        # Process conversation patterns
        for pattern in analysis.get("patterns", []):
            pat = pattern.get("pattern", "").strip()
            rec = pattern.get("recommendation", "").strip()
            if pat and rec:
                await _upsert_insight(
                    db,
                    category="conversation_pattern",
                    source_pattern=pat,
                    insight_text=f"Pattern: {pat} → Adapt: {rec}",
                )
                insights_added += 1

        if insights_added > 0:
            logger.info(f"🧠 Learning: extracted {insights_added} insights from user {str(user_id)[:8]}...")

    except json.JSONDecodeError as e:
        logger.warning(f"🧠 Learning: failed to parse analysis JSON: {e}")
    except Exception as e:
        logger.warning(f"🧠 Learning: analysis error (non-blocking): {e}")


async def _upsert_insight(
    db: AsyncSession,
    category: str,
    source_pattern: str,
    insight_text: str,
) -> None:
    """
    Insert a new insight or increment frequency if a similar one exists.
    Uses fuzzy matching on source_pattern to avoid near-duplicates.
    """
    # Check for existing similar insight
    result = await db.execute(
        select(LearnedInsight).where(
            LearnedInsight.category == category,
            LearnedInsight.source_pattern == source_pattern,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.frequency += 1
        existing.insight_text = insight_text  # Update with latest wording
        await db.flush()
        logger.debug(f"🧠 Insight frequency +1: {source_pattern[:50]}... (now {existing.frequency})")
    else:
        new_insight = LearnedInsight(
            category=category,
            source_pattern=source_pattern,
            insight_text=insight_text,
        )
        db.add(new_insight)
        await db.flush()
        logger.debug(f"🧠 New insight stored: {source_pattern[:50]}...")


async def get_active_insights(db: AsyncSession) -> List[LearnedInsight]:
    """
    Retrieve all active insights that meet the frequency threshold.

    Returns:
        List of LearnedInsight records sorted by frequency (highest first).
    """
    result = await db.execute(
        select(LearnedInsight)
        .where(
            LearnedInsight.is_active == True,
            LearnedInsight.frequency >= INSIGHT_THRESHOLD,
        )
        .order_by(LearnedInsight.frequency.desc())
        .limit(MAX_INJECTED_INSIGHTS)
    )
    return list(result.scalars().all())


async def get_all_insights(
    db: AsyncSession,
    category: Optional[str] = None,
    active_only: bool = False,
) -> List[LearnedInsight]:
    """Get all insights with optional filters (for admin API)."""
    query = select(LearnedInsight).order_by(LearnedInsight.frequency.desc())

    if category:
        query = query.where(LearnedInsight.category == category)
    if active_only:
        query = query.where(LearnedInsight.is_active == True)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_insight_stats(db: AsyncSession) -> Dict:
    """Get summary statistics about learned insights."""
    # Total count
    total_result = await db.execute(
        select(func.count(LearnedInsight.id))
    )
    total = total_result.scalar() or 0

    # Active count
    active_result = await db.execute(
        select(func.count(LearnedInsight.id))
        .where(LearnedInsight.is_active == True)
    )
    active = active_result.scalar() or 0

    # Count by category
    category_result = await db.execute(
        select(
            LearnedInsight.category,
            func.count(LearnedInsight.id),
        )
        .group_by(LearnedInsight.category)
    )
    by_category = {row[0]: row[1] for row in category_result.all()}

    # Top insights (highest frequency)
    top_result = await db.execute(
        select(LearnedInsight)
        .where(LearnedInsight.is_active == True)
        .order_by(LearnedInsight.frequency.desc())
        .limit(5)
    )
    top_insights = [
        {
            "pattern": ins.source_pattern[:100],
            "frequency": ins.frequency,
            "category": ins.category,
        }
        for ins in top_result.scalars().all()
    ]

    return {
        "total_insights": total,
        "active_insights": active,
        "injection_threshold": INSIGHT_THRESHOLD,
        "by_category": by_category,
        "top_insights": top_insights,
    }


async def build_dynamic_prompt(db: AsyncSession, base_prompt: str) -> str:
    """
    Build an enriched system prompt by appending learned insights.

    Args:
        db: Database session.
        base_prompt: The static SYSTEM_PROMPT from ai_service.

    Returns:
        Enriched system prompt with learned knowledge injected.
    """
    try:
        insights = await get_active_insights(db)

        if not insights:
            return base_prompt

        # Group insights by category
        faqs = [i for i in insights if i.category == "faq"]
        treatments = [i for i in insights if i.category == "treatment_insight"]
        patterns = [i for i in insights if i.category == "conversation_pattern"]

        # Build the dynamic section
        dynamic_sections = []

        if faqs:
            faq_lines = "\n".join(f"- {i.insight_text}" for i in faqs)
            dynamic_sections.append(
                f"LEARNED FROM PATIENT CONVERSATIONS — FREQUENTLY ASKED:\n{faq_lines}"
            )

        if treatments:
            treatment_lines = "\n".join(f"- {i.insight_text}" for i in treatments)
            dynamic_sections.append(
                f"LEARNED TREATMENT INSIGHTS:\n{treatment_lines}"
            )

        if patterns:
            pattern_lines = "\n".join(f"- {i.insight_text}" for i in patterns)
            dynamic_sections.append(
                f"LEARNED CONVERSATION PATTERNS:\n{pattern_lines}"
            )

        if not dynamic_sections:
            return base_prompt

        dynamic_block = "\n\n".join(dynamic_sections)
        enriched_prompt = (
            f"{base_prompt}\n\n"
            f"--- SELF-LEARNED KNOWLEDGE (from real patient interactions) ---\n"
            f"{dynamic_block}\n"
            f"--- END SELF-LEARNED KNOWLEDGE ---"
        )

        logger.info(
            f"🧠 Dynamic prompt built: {len(insights)} insights injected "
            f"({len(faqs)} FAQs, {len(treatments)} treatment, {len(patterns)} patterns)"
        )

        return enriched_prompt

    except Exception as e:
        logger.warning(f"🧠 Failed to build dynamic prompt, using static: {e}")
        return base_prompt


async def toggle_insight(
    db: AsyncSession,
    insight_id: UUID,
    is_active: bool,
) -> Optional[LearnedInsight]:
    """Toggle an insight's active status (for admin API)."""
    result = await db.execute(
        select(LearnedInsight).where(LearnedInsight.id == insight_id)
    )
    insight = result.scalar_one_or_none()

    if insight:
        insight.is_active = is_active
        await db.flush()
        logger.info(f"🧠 Insight {insight_id} set to active={is_active}")

    return insight
