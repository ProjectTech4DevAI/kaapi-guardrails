Creates an answer relevance prompt config for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Stores a custom prompt template used by the `answer_relevance_custom_llm` validator to evaluate whether an LLM answer is relevant to a user query.
- Tenant scope is enforced from the API key context.
- `prompt_template` must contain both `{query}` and `{answer}` placeholders; the server rejects templates missing either.

Common failure cases:
- Missing or invalid API key.
- Payload schema validation errors.
- `prompt_template` is missing `{query}` or `{answer}` placeholder.

## Field glossary

**`prompt_template`**
A string with `{query}` and `{answer}` placeholders. At validation time, the guardrail substitutes the user's query and the LLM's answer, then asks the model to respond `YES` (relevant) or `NO` (not relevant).

Default template used when no custom prompt is configured:
```
Query: {query}
Answer: {answer}

Does the answer fully satisfy the query and constraints?
Answer only YES or NO.
```

NGOs can customise this to add domain-specific constraints, language preferences, or stricter relevance criteria for their use case.

Example custom template:
```
You are evaluating a maternal health assistant.
Query: {query}
Answer: {answer}

Does the answer directly address the maternal health query with accurate information?
Answer only YES or NO.
```

**`name`**
Human-readable label for this prompt config (max 100 characters).

**`description`**
What this prompt evaluates (max 500 characters).
