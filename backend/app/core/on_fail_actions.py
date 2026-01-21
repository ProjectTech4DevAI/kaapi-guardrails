from guardrails.validators import FailResult

def rephrase_query_on_fail(value: str, fail_result: FailResult):
    return f"Please rephrase the query without unsafe content. {fail_result.error_message}"