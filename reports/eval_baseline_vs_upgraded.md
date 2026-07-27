# Baseline vs. upgraded — evaluation report

The improvement story, measured on the golden PR set (`myers/evaluation/golden/`). Matching is
on `(category, file, line)` so a regex baseline, a single LLM, and the specialist fan-out are
all scored against the same ground truth. Regenerate any row with:

```bash
python -m myers eval --mode baseline                       # offline, reproducible
python -m myers eval --mode llm         --cap 0.50         # Groq (needs GROQ_API_KEY)
python -m myers eval --mode specialists --cap 0.50         # Groq
```

## Results (golden set: `security_pr`, `clean_pr`)

| Mode | Precision | Recall | F1 | TP | FP | FN | Notes |
|---|---|---|---|---|---|---|---|
| baseline (M1) | **1.00** | 1.00 | 1.00 | 4 | 0 | 0 | Deterministic. Precise but shallow — only what regexes can prove. |
| llm (M2, Groq) | 0.60 | 0.75 | 0.67 | 3 | 2 | 1 | Reasons about intent (caught a missing-arg bug regex can't); chattier. |
| specialists (M3, Groq) | 0.22 | **1.00** | 0.36 | 4 | 14 | 0 | Four domains → catches **everything** in the golden set, plus many extra findings. |

*(Live LLM/specialist numbers measured on Groq `llama-3.3-70b-versatile`, 2026-07-27. Cost per
review ≈ $0.0005 (llm) / $0.0020 (specialists); latency ≈ 1s.)*

## How to read this — the design thesis, confirmed

- **Recall rises toward the fan-out; precision trades off.** The baseline is perfectly precise
  but blind to anything non-mechanical. The specialists catch **every** labeled issue (recall
  1.00) but also raise findings the minimal golden set doesn't label — some are genuine
  (missing docstrings, untested paths), some are noise.
- **Precision on a 2-case golden set understates usefulness** — many "false positives" are real,
  just not in the canonical labels. Growing the golden set with those labels is future work; the
  number is reported raw and un-fudged here.
- **This is exactly why the system is failure-aware, not autonomous.** The right answer is not
  "pick the most precise reviewer" — it is: run the deterministic baseline for a precise floor,
  fan out the specialists for depth and high recall, and route the uncertain / critical / noisy
  findings to a **human** via the confidence gate (M4). High recall + human triage beats either
  reviewer alone.

## Regression gate

`python -m myers eval --mode baseline --min-precision 0.9` exits non-zero if baseline precision
regresses below 0.9 — wired for CI so a change that breaks the deterministic floor blocks.
