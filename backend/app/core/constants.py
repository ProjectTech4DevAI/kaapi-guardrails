BAN_LIST = "ban_list"

LANG_HINDI = "hi"
LANG_ENGLISH = "en"
LABEL = "label"
SCORE = "score"

REPHRASE_ON_FAIL_PREFIX = "Please rephrase the query without unsafe content."
LLM_CRITIC_ERROR_MESSAGE = "The query did not meet the required quality criteria."
LLM_CRITIC_REPHRASE_MESSAGE = (
    f"{LLM_CRITIC_ERROR_MESSAGE} Please rephrase without unsafe content."
)

# Topic relevance validators (shared by the LLMCritic- and litellm-backed variants)
EMPTY_MESSAGE_ERROR = "Empty message."
TOPIC_OUT_OF_SCOPE_ERROR = "Input is outside the allowed topic scope."

# Answer relevance (custom LLM judge) validator. The *_TEMPLATE entries are
# format strings; call .format(...) with the named field before use.
ANSWER_RELEVANCE_EMPTY_FIELDS_ERROR = (
    "Both 'query' and 'answer' fields must be non-empty."
)
ANSWER_RELEVANCE_NOT_RELEVANT_ERROR = "The answer is not relevant to the query."
ANSWER_RELEVANCE_MISSING_PLACEHOLDER_TEMPLATE = (
    "Prompt template missing placeholder: {placeholder}"
)
ANSWER_RELEVANCE_LLM_CALL_FAILED_TEMPLATE = "LLM call failed: {error}"
ANSWER_RELEVANCE_UNEXPECTED_RESPONSE_TEMPLATE = (
    "Unexpected LLM response for relevance check: {response}"
)

# LLM prompt config CRUD
DUPLICATE_LLM_PROMPT_CONFIG_ERROR = (
    "A prompt config with the same configuration already exists"
)

VALIDATOR_CONFIG_SYSTEM_FIELDS = {
    "organization_id",
    "project_id",
    "name",
    "type",
    "stage",
    "on_fail_action",
    "is_enabled",
}
