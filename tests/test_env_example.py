"""
Tests for environment example placeholders.
"""

from pathlib import Path


def test_nvidia_api_key_in_env_example_is_placeholder():
    """The example env should use a placeholder, not a key-like value."""
    env_example_path = Path(__file__).parent.parent / ".env.example"
    env_example = env_example_path.read_text(encoding="utf-8")
    nvidia_key_line = next(
        (line for line in env_example.splitlines() if line.startswith("NVIDIA_API_KEY=")),
        None,
    )
    assert nvidia_key_line is not None
    assert nvidia_key_line == "NVIDIA_API_KEY=your-nvidia-api-key"
