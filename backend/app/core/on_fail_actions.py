from guardrails.validators import FailResult

from app.core.constants import REPHRASE_ON_FAIL_PREFIX

def rephrase_query_on_fail(value: str, fail_result: FailResult):
    return f"{REPHRASE_ON_FAIL_PREFIX} {fail_result.error_message}"