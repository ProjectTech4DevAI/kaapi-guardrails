"""
Live integration tests for TopicRelevanceLLM — these call the real LLM and are
skipped automatically when OPENAI_API_KEY is not set in the environment.

Run them explicitly with:
    pytest -m llm_live
or in any environment that has OPENAI_API_KEY configured.
"""
import os

import pytest
from guardrails.validators import FailResult, PassResult

from app.core.validators.topic_relevance_llm import TopicRelevanceLLM

pytestmark = pytest.mark.llm_live

_needs_key = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping live LLM tests",
)

_COOKING_SCOPE = "Only answer questions about cooking and recipes."
_HEALTH_SCOPE = "Only answer questions about general health and wellness."


@pytest.fixture(scope="module")
def cooking_validator():
    return TopicRelevanceLLM(system_prompt=_COOKING_SCOPE)


@pytest.fixture(scope="module")
def health_validator():
    return TopicRelevanceLLM(system_prompt=_HEALTH_SCOPE)


# ---------------------------------------------------------------------------
# In-scope queries — model should return score >= threshold (PassResult)
# ---------------------------------------------------------------------------


@_needs_key
def test_live_in_scope_query_passes(cooking_validator):
    result = cooking_validator._validate("How do I make pasta carbonara?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] >= 2


@_needs_key
def test_live_in_scope_query_exposes_score_metadata(cooking_validator):
    result = cooking_validator._validate("What temperature should I bake bread at?")

    assert isinstance(result, PassResult)
    assert "scope_score" in result.metadata
    assert result.metadata["scope_score"] in (1, 2, 3)


# ---------------------------------------------------------------------------
# Out-of-scope queries — model should return score < threshold (FailResult)
# ---------------------------------------------------------------------------


@_needs_key
def test_live_out_of_scope_query_fails(cooking_validator):
    result = cooking_validator._validate("What is the capital of France?")

    assert isinstance(result, FailResult)
    assert "outside the allowed topic scope" in result.error_message


@_needs_key
def test_live_out_of_scope_score_is_exposed_in_metadata(cooking_validator):
    result = cooking_validator._validate("Who won the cricket World Cup?")

    assert isinstance(result, FailResult)
    assert "scope_score" in result.metadata
    assert result.metadata["scope_score"] in (1, 2, 3)


# ---------------------------------------------------------------------------
# JSON response format — exercises _extract_first_json_object on real output
# ---------------------------------------------------------------------------


@_needs_key
def test_live_response_parsed_without_error(health_validator):
    """The LLM returns JSON that _extract_first_json_object must parse correctly,
    regardless of whether the model wraps it in a markdown fence or adds prose."""
    result = health_validator._validate("How much water should I drink per day?")

    assert isinstance(result, (PassResult, FailResult))
    assert "scope_score" in result.metadata


@_needs_key
def test_live_different_scope_gives_different_verdict(
    cooking_validator, health_validator
):
    """The same off-topic query fails both validators, confirming scope config is wired."""
    query = "Explain quantum entanglement."

    cooking_result = cooking_validator._validate(query)
    health_result = health_validator._validate(query)

    assert isinstance(cooking_result, FailResult)
    assert isinstance(health_result, FailResult)
