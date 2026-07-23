Creates an LLM prompt config for the tenant resolved from the `X-ORGANIZATION-ID` / `X-PROJECT-ID` headers.

Behavior notes:
- Stores a named prompt used by an LLM-backed validator (`topic_relevance` or `answer_relevance_custom_llm`).
- `validator_name` determines which validator this config applies to.
- Tenant scope is enforced from the API key context.
- Duplicate configurations (same `validator_name`, `prompt_schema_version`, and `llm_prompt`) are rejected.
- For `answer_relevance_custom_llm`, `llm_prompt` must contain both `{query}` and `{answer}` placeholders.

Common failure cases:
- Missing or invalid API key.
- Payload schema validation errors.
- `llm_prompt` is missing `{query}` or `{answer}` placeholder (for `answer_relevance_custom_llm`).
- A config with the same configuration already exists.

## Field glossary

**`validator_name`**
Which LLM-backed validator this prompt config applies to.

Accepted values:
- `topic_relevance` — scope guard; `llm_prompt` is a plain-text description of allowed topics injected at `{{TOPIC_CONFIGURATION}}`.
- `answer_relevance_custom_llm` — relevance judge; `llm_prompt` must contain `{query}` and `{answer}` placeholders.

**`llm_prompt`**
The prompt text supplied to the LLM at evaluation time.

For `topic_relevance`, this is a plain-text scope definition:
```
This assistant only answers questions about maternal health and pregnancy care.
It should not respond to questions about politics or general medicine unrelated to pregnancy.
```

For `answer_relevance_custom_llm`, this must include `{query}` and `{answer}` placeholders:
```
You are evaluating a maternal health assistant.
Query: {query}
Answer: {answer}

Does the answer directly address the maternal health query?
Answer only YES or NO.
```

**`prompt_schema_version`**
Integer selecting the versioned prompt template. Defaults to `1`. Only relevant for `topic_relevance`; increment only when a new system prompt version has been added.

**`name`**
Human-readable label for this config (max 100 characters).

**`description`**
What this config evaluates or guards (max 500 characters).
