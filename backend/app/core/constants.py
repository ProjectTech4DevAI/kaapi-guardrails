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

VALIDATOR_CONFIG_SYSTEM_FIELDS = {
    "organization_id",
    "project_id",
    "name",
    "type",
    "stage",
    "on_fail_action",
    "is_enabled",
}
