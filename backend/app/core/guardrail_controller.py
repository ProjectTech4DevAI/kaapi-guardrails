from typing import get_args

from guardrails import Guard

from app.models.guardrail_config import ValidatorConfigItem

def build_guard(validator_items):
    validators = [v_item.build() for v_item in validator_items]
    return Guard().use_many(*validators)

def get_validator_config_models():
    annotated_args = get_args(ValidatorConfigItem)
    union_type = annotated_args[0]
    return get_args(union_type)