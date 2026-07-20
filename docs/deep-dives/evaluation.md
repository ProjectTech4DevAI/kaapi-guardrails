# Evaluation & Benchmarking

How to measure whether your validators are actually working.

---

## Why Accuracy Alone Is Misleading

An NSFW filter that blocks everything has 100% recall but 0% precision. A filter that blocks nothing has 100% precision but 0% recall. Neither is useful.

Safety systems live or die by the balance between:
- **Precision** — of things blocked, how many were actually unsafe
- **Recall** — of all unsafe things, how many did we catch

A single accuracy number hides this tradeoff. Always report both.

---

## Core Metrics

### Definitions

| Metric | Formula | What it measures |
|--------|---------|-----------------|
| **Precision** | TP / (TP + FP) | When we block, are we right? |
| **Recall** | TP / (TP + FN) | Of all unsafe content, what fraction do we catch? |
| **F1** | 2 × (P × R) / (P + R) | Harmonic mean of precision and recall |
| **False Positive Rate** | FP / (FP + TN) | How often do we block safe content? |

Where:
- **TP** = Unsafe content correctly blocked
- **FP** = Safe content incorrectly blocked (false alarm)
- **FN** = Unsafe content incorrectly passed (miss)
- **TN** = Safe content correctly passed

### Which metric to optimize

| Use case | Optimize for |
|----------|-------------|
| Public platform (social, gaming) | High recall — minimize misses |
| Enterprise internal tool | High precision — minimize false alarms |
| Healthcare / regulated | Near-perfect recall (misses are unacceptable) |
| General purpose | F1 — balanced |

---

## Running the Built-in Evaluations

The project includes evaluation scripts for each validator under `backend/app/evaluation/`.

**Run a single validator evaluation:**

```bash
# From the backend directory
python -m app.evaluation.pii.run
python -m app.evaluation.lexical_slur.run
python -m app.evaluation.gender_assumption_bias.run
python -m app.evaluation.ban_list.run
python -m app.evaluation.topic_relevance.run
python -m app.evaluation.toxicity.run
```

**Outputs:**

Each script writes to `backend/app/evaluation/outputs/<validator>/`:
- `predictions.csv` — per-sample predictions (input, expected, predicted, correct)
- `metrics.json` — precision, recall, F1 scores

**Example `metrics.json`:**

```json
{
  "precision": 0.87,
  "recall": 0.91,
  "f1": 0.89,
  "total_samples": 200,
  "true_positives": 89,
  "false_positives": 13,
  "false_negatives": 9,
  "true_negatives": 89
}
```

---

## Evaluating on Your Own Data

The built-in datasets are useful benchmarks but may not reflect your user base. Build your own evaluation set.

### Step 1: Collect examples

Gather 100–500 real inputs from your application:
- Examples that should pass (safe)
- Examples that should fail (unsafe)
- Borderline cases (ambiguous)

If you're launching a new product, generate synthetic examples representative of expected user behavior.

### Step 2: Label the examples

For each example, record:
- `input`: the text
- `expected_outcome`: `pass` or `fail`
- `notes`: why (optional but useful for reviewing errors)

```csv
input,expected_outcome,notes
"What's the weather today?",pass,generic safe query
"<slur> you",fail,clear violation
"Send me Priya's phone number",pass,"intent to get PII but no PII in input itself"
```

### Step 3: Run through your pipeline

```python
import csv
import httpx

results = []
with open("test_set.csv") as f:
    for row in csv.DictReader(f):
        response = httpx.post(
            "http://localhost:8001/api/v1/guardrails/",
            headers={"Authorization": "Bearer your-token"},
            json={
                "request_id": str(uuid.uuid4()),
                "organization_id": 1,
                "project_id": 1,
                "input": row["input"],
                "validators": YOUR_VALIDATOR_CONFIG,
            },
        ).json()

        predicted = "fail" if response["data"]["safe_text"] is None else "pass"
        results.append({
            "input": row["input"],
            "expected": row["expected_outcome"],
            "predicted": predicted,
            "correct": predicted == row["expected_outcome"],
        })
```

### Step 4: Compute metrics

```python
from sklearn.metrics import precision_score, recall_score, f1_score

y_true = [1 if r["expected"] == "fail" else 0 for r in results]
y_pred = [1 if r["predicted"] == "fail" else 0 for r in results]

print(f"Precision: {precision_score(y_true, y_pred):.3f}")
print(f"Recall:    {recall_score(y_true, y_pred):.3f}")
print(f"F1:        {f1_score(y_true, y_pred):.3f}")
```

---

## Latency Benchmarking

Correctness isn't enough — validators need to be fast enough for your use case.

```python
import time

latencies = []
for example in test_set:
    start = time.perf_counter()
    call_pipeline(example)
    latencies.append(time.perf_counter() - start)

print(f"p50:  {sorted(latencies)[len(latencies)//2]*1000:.0f}ms")
print(f"p95:  {sorted(latencies)[int(len(latencies)*0.95)]*1000:.0f}ms")
print(f"p99:  {sorted(latencies)[int(len(latencies)*0.99)]*1000:.0f}ms")
```

### Typical latency ranges

| Validator type | Expected latency |
|----------------|-----------------|
| Lexical (ban_list, uli_slur_match) | < 20ms |
| ML model (nsfw_text, llamaguard_7b) | 100–400ms |
| LLM critic (topic_relevance, llm_critic) | 500ms–3s |
| Combined pipeline (all types) | 1–5s |

---

## Datasets Used in Built-in Evaluations

| Validator | Dataset | Source |
|-----------|---------|--------|
| `uli_slur_match` | `lexical_slur_testing_dataset.csv` | ULI NGO database + synthetic |
| `pii_remover` | `pii_detection_testing_dataset.csv` | Project-created, India-context |
| `gender_assumption_bias` | `gender_bias_assumption_dataset.csv` | Project-created |
| `ban_list` | `ban_list_testing_dataset.csv` | Project-created |
| `topic_relevance` | `datasets/topic_relevance/` | Project-created, NGO scenarios |
| Toxicity | `datasets/toxicity/` | HASOC + project-created |

---

## Multilingual Evaluation

If your product serves Hindi (or other Indian language) users, evaluate specifically on code-mixed (Hinglish) examples. Model performance can degrade significantly on:
- Romanized Hindi text ("yaar yeh kaisa banda hai")
- Mixed Hindi-English sentences
- Regional slang and colloquialisms

Build a separate multilingual test set and track metrics independently.

---

## When to Re-evaluate

- After changing any threshold
- After updating a ban list or topic config
- After upgrading the guardrails-ai version
- Monthly, even without changes — user behavior evolves
- After any notable safety incident
