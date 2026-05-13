# Custom Validators

When the built-in validators don't cover your specific use case, you can build your own.

---

## The Validator Interface

All validators in Kaapi Guardrails are built on the [guardrails-ai](https://github.com/guardrails-ai/guardrails) framework. A custom validator is a class that extends `Validator` and implements `validate()`.

```python
from guardrails.validator_base import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)

@register_validator(name="my-custom-validator", data_type="string")
class MyCustomValidator(Validator):
    def validate(self, value: str, metadata: dict) -> ValidationResult:
        # your validation logic here
        if violates_rule(value):
            return FailResult(
                error_message="Reason this failed",
                fix_value=cleaned_version(value),  # or None if no fix possible
            )
        return PassResult()
```

### Return values

**`PassResult()`** — The text is safe. The pipeline continues with the current text.

**`FailResult(error_message, fix_value)`**

| Field | Type | Description |
|-------|------|-------------|
| `error_message` | `str` | Human-readable explanation of the violation |
| `fix_value` | `str \| None` | The corrected version. Required if `on_fail="fix"`. If `None`, `fix` action returns `""` |

---

## Example 1: Regex-Based Validator

Block inputs that contain social media handles:

```python
import re
from guardrails.validator_base import (
    FailResult, PassResult, ValidationResult, Validator, register_validator
)

@register_validator(name="no-social-handles", data_type="string")
class NoSocialHandlesValidator(Validator):
    HANDLE_PATTERN = re.compile(r"@\w+")

    def validate(self, value: str, metadata: dict) -> ValidationResult:
        matches = self.HANDLE_PATTERN.findall(value)
        if matches:
            fixed = self.HANDLE_PATTERN.sub("[HANDLE]", value)
            return FailResult(
                error_message=f"Social media handles found: {matches}",
                fix_value=fixed,
            )
        return PassResult()
```

Use it in a request:

```json
{
  "validators": [
    { "type": "no-social-handles", "on_fail": "fix" }
  ]
}
```

---

## Example 2: API-Backed Validator

Call an external moderation API and fail based on its response:

```python
import httpx
from guardrails.validator_base import (
    FailResult, PassResult, ValidationResult, Validator, register_validator
)

@register_validator(name="external-moderation", data_type="string")
class ExternalModerationValidator(Validator):
    def __init__(self, api_url: str, api_key: str, threshold: float = 0.8, **kwargs):
        self.api_url = api_url
        self.api_key = api_key
        self.threshold = threshold
        super().__init__(**kwargs)

    def validate(self, value: str, metadata: dict) -> ValidationResult:
        response = httpx.post(
            self.api_url,
            json={"text": value},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=5.0,
        )
        result = response.json()
        score = result["toxicity_score"]

        if score >= self.threshold:
            return FailResult(
                error_message=f"External moderation score {score:.2f} exceeds threshold {self.threshold}",
                fix_value=None,  # no fix; caller should use on_fail=exception
            )
        return PassResult()
```

---

## Example 3: LLM-Based Validator

Use an LLM to evaluate a custom policy:

```python
from openai import OpenAI
from guardrails.validator_base import (
    FailResult, PassResult, ValidationResult, Validator, register_validator
)

@register_validator(name="policy-check", data_type="string")
class PolicyCheckValidator(Validator):
    PROMPT = """
    Does the following text violate our policy of {policy}?
    
    Text: {text}
    
    Answer with YES or NO only.
    """

    def __init__(self, policy: str, llm_callable: str = "gpt-4o-mini", **kwargs):
        self.policy = policy
        self.client = OpenAI()
        self.model = llm_callable
        super().__init__(**kwargs)

    def validate(self, value: str, metadata: dict) -> ValidationResult:
        prompt = self.PROMPT.format(policy=self.policy, text=value)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
        )
        answer = response.choices[0].message.content.strip().upper()

        if answer == "YES":
            return FailResult(
                error_message=f"Policy violation: {self.policy}",
                fix_value=None,
            )
        return PassResult()
```

---

## Wrapping a Custom Validator in a Config

To integrate with the existing API, wrap your validator in a config class:

```python
from app.core.validators.config.base_validator_config import BaseValidatorConfig
from guardrails import Validator

class PolicyCheckConfig(BaseValidatorConfig):
    policy: str
    llm_callable: str = "gpt-4o-mini"

    def build(self) -> Validator:
        return PolicyCheckValidator(
            policy=self.policy,
            llm_callable=self.llm_callable,
            on_fail=self.resolve_on_fail(),
        )
```

Then register it in `validators.json` alongside the existing validators, and add `"policy_check"` to the `ValidatorType` enum.

---

## Common Patterns and Pitfalls

### Always handle exceptions in validate()

Network calls, model loading, and regex can raise. Unhandled exceptions will propagate out of the pipeline.

```python
def validate(self, value: str, metadata: dict) -> ValidationResult:
    try:
        result = call_external_api(value)
    except Exception as e:
        # Fail safe: treat API errors as failures, or pass through conservatively
        return FailResult(error_message=f"Validation service unavailable: {e}")
    ...
```

### Return a `fix_value` whenever possible

When `on_fail="fix"` is used and `fix_value=None`, the output becomes an empty string. That's almost never what you want. Return a cleaned version of the text instead.

```python
# Bad: returns empty string
return FailResult(error_message="...", fix_value=None)

# Good: returns text with the problematic part removed
return FailResult(error_message="...", fix_value=cleaned_text)
```

### Keep validators single-responsibility

One validator, one concern. Don't build a validator that checks both PII and profanity. Combine focused validators in the pipeline instead.

### LLM validators are slow — cache where possible

If the same input is validated frequently, consider caching at the application layer. LLM API calls take 500ms–2s and add cost.
