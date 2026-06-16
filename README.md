# DrunkAgent — Reproduction & Critical Analysis

*[中文版 / Chinese version → `README.zh.md`](README.zh.md)*

A from-scratch reproduction of **"DrunkAgent: Stealthy Memory Corruption in
LLM-Powered Recommender Agents"** (arXiv:2503.23804v3), built to stress-test the
paper's claims rather than restate them.

> The original repo for this task was **empty** — no code was present. This is an
> independent re-implementation of the method from the paper text (Algorithm 1,
> Fig. 2, Table 4), written so the core claims can actually be executed.

## What is faithful vs. substituted

The paper's exact stack is **not runnable in this sandbox**: HuggingFace and
OpenAI are network-blocked, there is no GPU, and `torch`/`transformers` are not
installed. So:

| Component | Paper | Here | Why |
|---|---|---|---|
| Surrogate / victim LLM | Llama-3-8B-Instruct, gpt-4-turbo | **Claude (haiku-4.5)** for every LLM role | HF + OpenAI blocked, no GPU |
| Greedy-search score (Eq. 4) | token-level **NLL** from white-box surrogate | **black-box surrogate MRR** (target's reciprocal rank on probe users) | Claude exposes no logprobs; MRR optimizes the attack objective directly |
| Datasets | Amazon Review Data, Yelp | **synthetic CD dataset** (same shape) | data not downloadable here |
| Perplexity metric (GPT-Neo) | GPT-Neo PPL | replaced by a trivial **injection detector** | GPT-Neo not downloadable |
| Scale | ~99 users, E=20, \|M_c\|=10 | ~20 users, E=3, \|M_c\|=6 | API budget |

**Faithful:** the three victim designs (AgentCF/RAG/SEQ) with Table-4 prompt
templates; the generation module (init → quality estimation → feature
integration/crossover → linguistic enrichment); the strategy module (the five
prompt-injection components of Fig. 2); HR@K / NDCG@K; the ablation structure of
Table 5; the drunk-success metric of Table 6.

Because the backbone and data differ, **absolute numbers are not comparable to
the paper.** What *is* comparable — and what this repo is for — are the
**qualitative claims**: does the attack beat baselines, which victim is most
robust, does removing the strategy collapse the attack, and is the "stealthy"
text actually stealthy.

## Layout

```
repro/
  llm.py        Claude client (OAuth bearer, disk cache, retries)
  data.py       synthetic CD dataset (deterministic, seed=2024)
  victims.py    AgentCF / AgentRAG / AgentSEQ + ranking parser
  metrics.py    HR@K, NDCG@K
  attacks.py    baselines + DrunkAgent generation (greedy search) + strategy
  run.py        orchestrates everything -> results/
results/        results.json + report.md (generated)
```

## Run

```bash
N_USERS=20 python3 -m repro.run          # full reproduction
N_USERS=2 VICTIMS=AgentCF python3 -m repro.run   # quick smoke test
```

See `results/report.md` for the generated tables and `ANALYSIS.md` for the
critical read of the paper (the four reproduction questions + strengths/
weaknesses).
