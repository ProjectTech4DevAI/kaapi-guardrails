BAN_LIST = "ban_list"

LANG_HINDI = "hi"
LANG_ENGLISH = "en"
LABEL = "label"
SCORE = "score"

REPHRASE_ON_FAIL_PREFIX = "Please rephrase the query without unsafe content."
LLM_CRITIC_ERROR_MESSAGE = "The query did not meet the required quality criteria."

VALIDATOR_CONFIG_SYSTEM_FIELDS = {
    "organization_id",
    "project_id",
    "name",
    "type",
    "stage",
    "on_fail_action",
    "is_enabled",
}
