# Common Use Cases

Recommended validator pipelines for specific deployment scenarios.

---

## Customer Support Bot

**Risks:** Abusive users, PII leakage in responses, off-topic queries draining LLM budget.

**Input pipeline:**
```json
{
  "validators": [
    {
      "type": "uli_slur_match",
      "on_fail": "rephrase",
      "languages": ["en", "hi"],
      "severity": "all"
    },
    {
      "type": "ban_list",
      "on_fail": "rephrase",
      "ban_list_id": "support-topic-ban-list-uuid"
    },
    {
      "type": "topic_relevance",
      "on_fail": "rephrase",
      "topic_relevance_config_id": "support-scope-uuid",
      "llm_callable": "gpt-4o-mini"
    }
  ]
}
```

**Output pipeline:**
```json
{
  "validators": [
    {
      "type": "pii_remover",
      "on_fail": "fix",
      "entity_types": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]
    },
    {
      "type": "gender_assumption_bias",
      "on_fail": "fix",
      "categories": ["generic"]
    }
  ]
}
```

**Topic config example:**
> "This assistant helps customers with product orders, shipping, returns, and account issues for [Company Name]. It should not answer questions about competitor products, legal matters, or topics unrelated to our product catalog."

---

## NGO Helpline / Community Platform

**Risks:** Crisis language (self-harm), hate speech targeting marginalized communities, slurs in regional languages, PII of vulnerable users.

**Priority:** Err heavily on the side of safety. False positives are acceptable.

```json
{
  "validators": [
    {
      "type": "uli_slur_match",
      "on_fail": "exception",
      "languages": ["en", "hi"],
      "severity": "all"
    },
    {
      "type": "nsfw_text",
      "on_fail": "exception",
      "threshold": 0.7
    },
    {
      "type": "llamaguard_7b",
      "on_fail": "exception",
      "policies": [
        "no_violence_hate",
        "no_encourage_self_harm",
        "no_sexual_content"
      ]
    },
    {
      "type": "pii_remover",
      "on_fail": "fix",
      "threshold": 0.4
    }
  ]
}
```

**Application-level:** Route `safe_text: null` responses to a crisis counselor or escalation workflow.

---

## Educational Chatbot (Students)

**Risks:** Age-inappropriate content, profanity, hate speech, academic dishonesty (if relevant).

**Priority:** Strict content filtering. The audience may include minors.

```json
{
  "validators": [
    {
      "type": "profanity_free",
      "on_fail": "fix"
    },
    {
      "type": "uli_slur_match",
      "on_fail": "exception",
      "languages": ["en", "hi"],
      "severity": "all"
    },
    {
      "type": "nsfw_text",
      "on_fail": "exception",
      "threshold": 0.6,
      "validation_method": "sentence"
    },
    {
      "type": "topic_relevance",
      "on_fail": "rephrase",
      "topic_relevance_config_id": "edu-scope-uuid",
      "llm_callable": "gpt-4o-mini"
    }
  ]
}
```

**Topic config example:**
> "This assistant helps students with homework, study questions, and educational topics for grades 6–12. It covers math, science, history, and literature. It should not discuss adult topics, social media, gaming, or requests to write full assignments."

---

## Healthcare Assistant

**Risks:** Dangerous medical advice, PII of patients, off-topic medical queries exceeding the assistant's scope.

**Priority:** Hard blocks on dangerous advice; PII protection; scope enforcement.

**Input pipeline:**
```json
{
  "validators": [
    {
      "type": "uli_slur_match",
      "on_fail": "exception",
      "severity": "high"
    },
    {
      "type": "topic_relevance",
      "on_fail": "rephrase",
      "topic_relevance_config_id": "health-scope-uuid",
      "llm_callable": "gpt-4o-mini"
    }
  ]
}
```

**Output pipeline:**
```json
{
  "validators": [
    {
      "type": "pii_remover",
      "on_fail": "fix",
      "entity_types": ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "MEDICAL_LICENSE"]
    },
    {
      "type": "gender_assumption_bias",
      "on_fail": "fix",
      "categories": ["healthcare"]
    },
    {
      "type": "llm_critic",
      "on_fail": "exception",
      "metrics": {
        "medical_safety": "The response must not provide specific diagnoses, recommend specific medications, or substitute for professional medical advice. It should always recommend consulting a qualified doctor."
      },
      "max_score": 3,
      "llm_callable": "gpt-4o-mini"
    }
  ]
}
```

---

## Coding Copilot / Developer Tool

**Risks:** Generating malicious code, leaking secrets found in pasted code, off-topic requests.

**Priority:** Low toxicity risk (developer audience). Focus on secret detection and scope.

```json
{
  "validators": [
    {
      "type": "ban_list",
      "on_fail": "fix",
      "banned_words": ["password", "api_key", "secret", "private_key", "AWS_SECRET"]
    },
    {
      "type": "pii_remover",
      "on_fail": "fix",
      "entity_types": ["EMAIL_ADDRESS", "IP_ADDRESS", "PHONE_NUMBER"]
    }
  ]
}
```

For code generation output, consider `llm_critic` with a security-focused metric:

```json
{
  "type": "llm_critic",
  "metrics": {
    "security": "The generated code must not include hardcoded credentials, SQL injection vulnerabilities, command injection, or insecure deserialization patterns."
  },
  "max_score": 3,
  "llm_callable": "gpt-4o-mini"
}
```
