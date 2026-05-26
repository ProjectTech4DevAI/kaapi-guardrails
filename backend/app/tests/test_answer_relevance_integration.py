"""
Integration tests for the answer_relevance_custom_llm validator, alone and combined
with other output-side validators (ban_list, profanity_free, uli_slur_match, nsfw_text).

When answer_relevance_custom_llm is present, the route passes payload.output as the
validation data so every chained validator also runs on the LLM response text.

The litellm completion call is mocked to control YES / NO verdicts without requiring
a live OpenAI key, while all other validators run their real implementations.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.tests.seed_data import (
    VALIDATOR_INTEGRATION_ORGANIZATION_ID,
    VALIDATOR_INTEGRATION_PROJECT_ID,
)
from app.tests.utils.constants import SAFE_TEXT_FIELD, VALIDATE_API_PATH

pytestmark = pytest.mark.integration

_PATCH_TARGET = "app.core.validators.answer_relevance_custom_llm.completion"
_SETTINGS_PATH = (
    "app.core.validators.config"
    ".answer_relevance_custom_llm_safety_validator_config.settings"
)


@pytest.fixture(autouse=True)
def _mock_openai_key():
    """Inject a dummy API key so build() doesn't raise in the test environment."""
    with patch(_SETTINGS_PATH) as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        yield


organization_id = VALIDATOR_INTEGRATION_ORGANIZATION_ID
project_id = VALIDATOR_INTEGRATION_PROJECT_ID

QUERY = "What are the common symptoms of diabetes?"
RELEVANT_ANSWER = (
    "Common symptoms of diabetes include increased thirst, frequent urination, "
    "unexplained weight loss, and fatigue."
)
IRRELEVANT_ANSWER = (
    "The Eiffel Tower was built in 1889 and is located in Paris, France."
)


def _llm_yes():
    choice = MagicMock()
    choice.message.content = "YES"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _llm_no():
    choice = MagicMock()
    choice.message.content = "NO"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _payload(input_text, output_text, validators):
    return {
        "request_id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "project_id": project_id,
        "input": input_text,
        "output": output_text,
        "validators": validators,
    }


# ---------------------------------------------------------------------------
# answer_relevance alone
# ---------------------------------------------------------------------------


def test_answer_relevance_alone_passes_for_relevant_output(integration_client):
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY, RELEVANT_ANSWER, [{"type": "answer_relevance_custom_llm"}]
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == RELEVANT_ANSWER


def test_answer_relevance_alone_fails_for_irrelevant_output(integration_client):
    with patch(_PATCH_TARGET, return_value=_llm_no()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                IRRELEVANT_ANSWER,
                [{"type": "answer_relevance_custom_llm", "on_fail": "exception"}],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False
    assert "not relevant" in body["error"]


def test_answer_relevance_alone_fails_when_output_is_missing(integration_client):
    """No output field → validator receives empty string → non-empty guard triggers."""
    response = integration_client.post(
        VALIDATE_API_PATH,
        json={
            "request_id": str(uuid.uuid4()),
            "organization_id": organization_id,
            "project_id": project_id,
            "input": QUERY,
            "validators": [
                {"type": "answer_relevance_custom_llm", "on_fail": "exception"}
            ],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False
    assert "non-empty" in body["error"]


def test_answer_relevance_alone_uses_custom_prompt_template(integration_client):
    custom_template = (
        "Question: {query}\n"
        "Answer: {answer}\n"
        "Does the answer address the question? Reply YES or NO."
    )
    with patch(_PATCH_TARGET, return_value=_llm_yes()) as mock_llm:
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                RELEVANT_ANSWER,
                [
                    {
                        "type": "answer_relevance_custom_llm",
                        "prompt_template": custom_template,
                    }
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == RELEVANT_ANSWER
    prompt_sent = mock_llm.call_args.kwargs["messages"][0]["content"]
    assert QUERY in prompt_sent
    assert RELEVANT_ANSWER in prompt_sent


# ---------------------------------------------------------------------------
# 2 validators
# ---------------------------------------------------------------------------


def test_answer_relevance_and_ban_list_both_pass_on_clean_relevant_output(
    integration_client,
):
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                RELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "ban_list", "banned_words": ["cancer", "tumor"]},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == RELEVANT_ANSWER


def test_answer_relevance_and_ban_list_fail_when_output_irrelevant(integration_client):
    """answer_relevance raises; ban_list never executes."""
    with patch(_PATCH_TARGET, return_value=_llm_no()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                IRRELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm", "on_fail": "exception"},
                    {"type": "ban_list", "banned_words": ["Paris"]},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False
    assert "not relevant" in body["error"]


def test_answer_relevance_and_ban_list_removes_banned_word_from_relevant_output(
    integration_client,
):
    """Relevant output that contains a banned word: relevance passes, ban_list fixes."""
    output_with_banned = RELEVANT_ANSWER + " Visit badclinic for more info."
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                output_with_banned,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "ban_list", "banned_words": ["badclinic"]},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert "badclinic" not in body["data"][SAFE_TEXT_FIELD]


def test_answer_relevance_and_profanity_free_both_pass_on_clean_relevant_output(
    integration_client,
):
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                RELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "profanity_free"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == RELEVANT_ANSWER


def test_answer_relevance_and_profanity_free_fixes_profanity_in_relevant_output(
    integration_client,
):
    """Relevant output containing profanity: relevance passes, profanity_free cleans it."""
    profane_relevant = "Diabetes symptoms include fuck fatigue."
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                profane_relevant,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "profanity_free"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert "fuck" not in body["data"][SAFE_TEXT_FIELD].lower()


def test_answer_relevance_and_slur_match_both_pass_on_clean_relevant_output(
    integration_client,
):
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                RELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "uli_slur_match", "severity": "all"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == RELEVANT_ANSWER


def test_answer_relevance_and_slur_match_redacts_slur_in_relevant_output(
    integration_client,
):
    """Relevant output containing a slur: relevance passes, slur_match redacts it."""
    slurred_relevant = "Diabetes symptoms include chakki fatigue and increased thirst."
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                slurred_relevant,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "uli_slur_match", "severity": "all"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    safe = body["data"][SAFE_TEXT_FIELD]
    assert "chakki" not in safe
    assert "[REDACTED_SLUR]" in safe


def test_answer_relevance_and_profanity_free_fail_when_profanity_on_fail_exception(
    integration_client,
):
    """Relevant but profane output: profanity_free raises → overall failure."""
    profane_relevant = "Bloody hell, the symptoms include thirst and fatigue."
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                profane_relevant,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "profanity_free", "on_fail": "exception"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False


# ---------------------------------------------------------------------------
# 3 validators
# ---------------------------------------------------------------------------


def test_answer_relevance_ban_list_profanity_free_all_pass_on_clean_relevant_output(
    integration_client,
):
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                RELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "ban_list", "banned_words": ["cancer"]},
                    {"type": "profanity_free"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == RELEVANT_ANSWER


def test_answer_relevance_ban_list_profanity_free_fail_on_irrelevant_output(
    integration_client,
):
    with patch(_PATCH_TARGET, return_value=_llm_no()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                IRRELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm", "on_fail": "exception"},
                    {"type": "ban_list", "banned_words": ["Paris"]},
                    {"type": "profanity_free"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False
    assert "not relevant" in body["error"]


def test_answer_relevance_profanity_free_slur_match_fix_both_issues_in_relevant_output(
    integration_client,
):
    """Relevant output with both a slur and profanity: both get fixed."""
    dirty_relevant = "Diabetes symptoms include chakki fatigue and fuck thirst."
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                dirty_relevant,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "profanity_free"},
                    {"type": "uli_slur_match", "severity": "all"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    safe = body["data"][SAFE_TEXT_FIELD]
    assert "chakki" not in safe
    assert "fuck" not in safe.lower()


def test_answer_relevance_ban_list_slur_match_all_pass_on_clean_relevant_output(
    integration_client,
):
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                RELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "ban_list", "banned_words": ["poison"]},
                    {"type": "uli_slur_match", "severity": "all"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == RELEVANT_ANSWER


# ---------------------------------------------------------------------------
# 4 validators
# ---------------------------------------------------------------------------


def test_answer_relevance_ban_list_profanity_free_slur_match_all_pass(
    integration_client,
):
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                RELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "ban_list", "banned_words": ["cancer"]},
                    {"type": "profanity_free"},
                    {"type": "uli_slur_match", "severity": "all"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == RELEVANT_ANSWER


def test_answer_relevance_ban_list_profanity_free_slur_match_fix_all_issues(
    integration_client,
):
    """4 validators: relevant output with slur + banned word + profanity, all get fixed."""
    messy_relevant = "Diabetes symptoms include chakki fatigue and fuck thirst."
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                messy_relevant,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "profanity_free"},
                    {"type": "uli_slur_match", "severity": "all"},
                    {"type": "ban_list", "banned_words": ["badword"]},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    safe = body["data"][SAFE_TEXT_FIELD]
    assert "chakki" not in safe
    assert "fuck" not in safe.lower()


def test_answer_relevance_ban_list_profanity_free_slur_match_fail_on_irrelevant(
    integration_client,
):
    with patch(_PATCH_TARGET, return_value=_llm_no()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                IRRELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm", "on_fail": "exception"},
                    {"type": "ban_list", "banned_words": ["Paris"]},
                    {"type": "profanity_free"},
                    {"type": "uli_slur_match", "severity": "all"},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False
    assert "not relevant" in body["error"]


# ---------------------------------------------------------------------------
# 5 validators
# ---------------------------------------------------------------------------


def test_five_validators_all_pass_on_clean_relevant_output(integration_client):
    """answer_relevance + ban_list + profanity_free + uli_slur_match + gender_assumption_bias
    all pass on clean, relevant, unbiased output."""
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                RELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "ban_list", "banned_words": ["cancer"]},
                    {"type": "profanity_free"},
                    {"type": "uli_slur_match", "severity": "all"},
                    {"type": "gender_assumption_bias", "categories": ["all"]},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == RELEVANT_ANSWER


def test_five_validators_fail_on_irrelevant_output(integration_client):
    with patch(_PATCH_TARGET, return_value=_llm_no()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                IRRELEVANT_ANSWER,
                [
                    {"type": "answer_relevance_custom_llm", "on_fail": "exception"},
                    {"type": "ban_list", "banned_words": ["Paris"]},
                    {"type": "profanity_free"},
                    {"type": "uli_slur_match", "severity": "all"},
                    {"type": "gender_assumption_bias", "categories": ["all"]},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False
    assert "not relevant" in body["error"]


def test_five_validators_fix_multiple_issues_in_relevant_output(integration_client):
    """5 validators: relevant output with slur + gender-biased language — both get fixed."""
    noisy_relevant = (
        "Diabetes symptoms include chakki fatigue and thirst. "
        "The policeman confirmed these symptoms."
    )
    with patch(_PATCH_TARGET, return_value=_llm_yes()):
        response = integration_client.post(
            VALIDATE_API_PATH,
            json=_payload(
                QUERY,
                noisy_relevant,
                [
                    {"type": "answer_relevance_custom_llm"},
                    {"type": "profanity_free"},
                    {"type": "uli_slur_match", "severity": "all"},
                    {"type": "ban_list", "banned_words": ["fever"]},
                    {"type": "gender_assumption_bias", "categories": ["all"]},
                ],
            ),
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    safe = body["data"][SAFE_TEXT_FIELD]
    assert "chakki" not in safe
    assert "policeman" not in safe
