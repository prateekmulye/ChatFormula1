"""Tests for the F1 expert system prompt."""

import pytest

from chatf1_agent.prompts import F1_EXPERT_SYSTEM_PROMPT


@pytest.mark.unit
class TestSystemPrompt:
    """Tests for F1_EXPERT_SYSTEM_PROMPT content."""

    def test_identity_and_domain(self):
        """Prompt establishes the ChatFormula1 persona and F1 domain."""
        assert "ChatFormula1" in F1_EXPERT_SYSTEM_PROMPT
        assert "Formula 1" in F1_EXPERT_SYSTEM_PROMPT
        assert "expert" in F1_EXPERT_SYSTEM_PROMPT.lower()

    def test_accuracy_guidelines(self):
        """Prompt demands accuracy and source citation."""
        assert "accuracy" in F1_EXPERT_SYSTEM_PROMPT.lower()
        assert "cite sources" in F1_EXPERT_SYSTEM_PROMPT.lower()

    def test_off_topic_handling(self):
        """Prompt includes off-topic redirection guidance."""
        assert "Off-Topic" in F1_EXPERT_SYSTEM_PROMPT
        assert "specialize in Formula 1" in F1_EXPERT_SYSTEM_PROMPT

    def test_prediction_uncertainty(self):
        """Prompt requires reasoning and uncertainty for predictions."""
        assert "prediction" in F1_EXPERT_SYSTEM_PROMPT.lower()
        assert "uncertainty" in F1_EXPERT_SYSTEM_PROMPT.lower()

    def test_substantial_content(self):
        """Prompt is detailed enough to anchor the persona."""
        assert len(F1_EXPERT_SYSTEM_PROMPT) > 500
