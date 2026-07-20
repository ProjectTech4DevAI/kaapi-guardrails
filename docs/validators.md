# All Validators

10 validators across safety, privacy, quality, and compliance categories.

---

## By Category

### Safety & Content Moderation
| Validator | What it catches | Speed |
|-----------|----------------|-------|
| [uli_slur_match](validators/uli-slur-match.md) | Slurs and abusive language (English + Hindi) | Fast |
| [profanity_free](validators/profanity-free.md) | General profanity | Fast |
| [nsfw_text](validators/nsfw-text.md) | Sexually explicit / NSFW content | Medium |
| [llamaguard_7b](validators/llamaguard-7b.md) | Violence, hate, weapons, drugs, self-harm | Medium |

### Privacy
| Validator | What it catches | Speed |
|-----------|----------------|-------|
| [pii_remover](validators/pii-remover.md) | Names, phones, email, Aadhaar, PAN, and 11 more | Fast |

### Bias & Fairness
| Validator | What it catches | Speed |
|-----------|----------------|-------|
| [gender_assumption_bias](validators/gender-assumption-bias.md) | Gendered language — replaces with neutral terms | Fast |

### Quality & Relevance
| Validator | What it catches | Speed |
|-----------|----------------|-------|
| [ban_list](validators/ban-list.md) | Your custom prohibited words and phrases | Fast |
| [topic_relevance](validators/topic-relevance.md) | Off-topic queries outside configured domain scope | Slow (LLM) |
| [answer_relevance_custom_llm](validators/answer-relevance.md) | LLM answers that don't address the user's query | Slow (LLM) |
| [llm_critic](validators/llm-critic.md) | Custom quality and safety metrics via LLM judge | Slow (LLM) |

---

## Quick Comparison

| Validator | Type | Requires API key | `fix_value` available | Recommended `on_fail` |
|-----------|------|-----------------|----------------------|----------------------|
| `uli_slur_match` | Lexical | No | Yes (redacts slur) | `fix` or `exception` |
| `pii_remover` | NLP model | No | Yes (redacted text) | `fix` |
| `gender_assumption_bias` | Lexical | No | Yes (neutral text) | `fix` |
| `ban_list` | Lexical | Hub key | Yes (redacts word) | `exception` or `fix` |
| `profanity_free` | ML (SVM) | Hub key | No | `exception` or `rephrase` |
| `nsfw_text` | ML (Transformer) | Hub key | No | `exception` |
| `llamaguard_7b` | LLM (7B model) | Hub key | No | `exception` |
| `topic_relevance` | LLM critic | OpenAI key | No | `rephrase` |
| `answer_relevance_custom_llm` | LLM critic | OpenAI key | No | `exception` or `rephrase` |
| `llm_critic` | LLM critic | OpenAI key | No | `exception` |

> **`fix_value` available = No** means `on_fail: "fix"` will return an empty string when this validator triggers. Use `exception` or `rephrase` instead.
