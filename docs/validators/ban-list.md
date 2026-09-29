# ban_list

Blocks or redacts a custom list of prohibited words, phrases, or patterns. The list can be provided inline in the request or stored in the database and referenced by ID. Sourced from the Guardrails Hub.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `ban_list` |
| Implementation | Guardrails Hub (`hub://guardrails/ban_list`) |
| Speed | Fast (< 10ms) |
| `fix_value` | Yes — redacts matched words |
| Requires API key | Guardrails Hub API key |

---

## Configuration

### Mode 1: Inline word list

Provide banned words directly in the request. Best for small, request-specific lists.

```json
{
  "type": "ban_list",
  "on_fail": "fix",
  "banned_words": ["competitor-name", "internal-codename", "lawsuit"]
}
```

### Mode 2: Stored ban list (recommended for production)

Reference a stored ban list by its UUID. Best for large lists and centrally managed policies.

```json
{
  "type": "ban_list",
  "on_fail": "exception",
  "ban_list_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `banned_words` | `string[]` | — | Inline list of banned words or phrases |
| `ban_list_id` | `UUID` | — | ID of a stored ban list |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

> Provide exactly one of `banned_words` or `ban_list_id`.

---

## Managing Stored Ban Lists

Stored ban lists are scoped per `organization_id` + `project_id`. Use the management API to create and update them without code changes.

**Create a ban list:**

```bash
POST /api/v1/guardrails/ban_lists/
Authorization: Bearer <token>
X-ORGANIZATION-ID: 1
X-PROJECT-ID: 101

{
  "name": "Competitor Terms",
  "description": "Terms that must not appear in AI responses",
  "words": ["CompetitorX", "RivalProduct", "OtherBrand"]
}
```

**Update a ban list:**

```bash
PATCH /api/v1/guardrails/ban_lists/{id}

{
  "words": ["CompetitorX", "RivalProduct", "OtherBrand", "NewCompetitor"]
}
```

Changes take effect immediately for all subsequent requests that reference the list.

**List all ban lists:**

```bash
GET /api/v1/guardrails/ban_lists/?organization_id=1&project_id=101
```

**Delete a ban list:**

```bash
DELETE /api/v1/guardrails/ban_lists/{id}
```

---

## Input / Output Examples

**Example 1 — Inline list, `on_fail: "fix"`:**
```json
{ "banned_words": ["lawsuit", "refund"], "on_fail": "fix" }

Input:  "I want a refund or I'll file a lawsuit"
Output: "I want a  or I'll file a "
```

**Example 2 — Stored list, `on_fail: "exception"`:**
```json
{ "ban_list_id": "uuid-here", "on_fail": "exception" }

Input:  "Tell me about CompetitorX"
Output: safe_text: null (exception raised)
```

**Example 3 — Clean text:**
```
Input:  "How do I reset my password?"
Output: "How do I reset my password?" (PassResult)
```

---

## Common Use Cases

| Use case | Example banned terms |
|----------|---------------------|
| Competitor suppression | Competitor names, product names |
| Legal compliance | "guarantee", "lawsuit", "promise", regulatory trigger words |
| Internal confidentiality | Internal project codenames, unreleased feature names |
| Topic suppression | Off-brand topics for a specialized assistant |
| Profanity (custom) | Domain-specific slurs not in `uli_slur_match` |

---

## Common Pitfalls

### Case sensitivity
The Guardrails Hub ban_list validator performs case-insensitive matching. "Lawsuit", "LAWSUIT", and "lawsuit" are all caught.

### Substring vs. whole-word matching
Depending on the Guardrails Hub implementation version, matching may be substring-based. Test your specific word list to verify behavior — e.g., banning "ass" might affect "assistant" depending on the implementation.

### `fix_value` returns empty spans
When `on_fail: "fix"`, the matched words are redacted (removed), leaving empty space. If the result looks odd, prefer `on_fail: "exception"` for hard blocks.

### Large inline lists add request size
If your banned word list is > 100 terms, prefer a stored ban list. Sending it inline in every request increases payload size and clutters logs.

---

## Recommended Stage

**Input** — Catch prohibited terms in user messages before they influence the LLM.  
**Output** — Also run on LLM responses if the model might reproduce or discuss banned terms.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `uli_slur_match` | Ban list covers custom policy terms; slur matcher covers abusive language |
| `topic_relevance` | Topic relevance catches off-domain requests semantically; ban list catches specific prohibited keywords literally |
