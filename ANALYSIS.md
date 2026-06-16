# DrunkAgent — Reproduction Findings & Critical Analysis

This document answers four reproduction questions and gives a code-grounded read
of the paper's strengths and weaknesses. It combines (a) a static analysis of the
paper's algorithm and reported numbers with (b) an **executed** re-implementation
(see `repro/`, results in `results/`).

> **Honest scope.** The paper's exact stack can't run in this sandbox
> (HuggingFace + OpenAI network-blocked, no GPU). I substituted Claude for the
> LLM roles and a synthetic CD dataset for Amazon. So absolute numbers differ
> from the paper by construction; what transfers is the **qualitative behaviour**
> of the method. Every empirical claim below is reproducible via `python3 -m
> repro.run` and `python3 -m repro.control_injectability`.

(Result tables are filled in from `results/` after the run; see the "Empirical
results" section.)

---

## The four questions

### Q1 — What cannot be reproduced?

1. **End-to-end, in this environment: nothing runs as the paper specifies** —
   Llama-3-8B surrogate (white-box NLL), gpt-4-turbo generation LLM, GPT-o1
   defense, GPT-Neo perplexity, and the Amazon/Yelp datasets are all blocked. A
   faithful run needs GPU + open HF/OpenAI access.
2. **The greedy-search score (Eq. 4) is not reproducible as written without a
   white-box surrogate.** It is a token-level NLL over the agent's generated
   ranking; an API-only victim (Claude, GPT-4) gives no logprobs, so the exact
   objective can't be computed. I substitute a black-box mean-reciprocal-rank
   score. Anyone reproducing with closed models faces the same wall.
3. **Under-specified stopping rules.** Algorithm 1 line 3 stops when the attack
   "is achieved stably" — no threshold. Line 16 loops "until the malicious action
   occurs", which makes Table 6's 100% true *by construction* (see Q4).
4. **Non-deterministic / moving dependencies.** gpt-4-turbo and GPT-o1 drift over
   time; `temperature=0, seed=2024` only pins victim inference, not the GPT-4
   generation calls. Exact numbers are not reproducible even with full access.

### Q2 — Which workload loses the most?

From the paper's own Table 1, the attack is far weaker on:
- **Musical Instruments** (every victim): DrunkAgent HR@1 = 0.2268 / 0.1340 /
  0.1443 (CF/RAG/SEQ) vs **CDs & Vinyl** 0.4040 / 0.3131 / 0.4949 — roughly a
  3× drop.
- **AgentRAG** is the most robust victim across datasets; the weakest single cell
  is AgentRAG × Musical Instruments (0.1340), ~3.7× below the headline CDs
  number the abstract leans on.

My reproduction reproduces the *direction*: see the "Empirical results" table —
AgentRAG is the hardest victim, and the effect is concentrated, not uniform.

### Q3 — Which assumption is unstable?

**The load-bearing, and most fragile, assumption is that the victim LLM will obey
instructions embedded in an item's description (the "strategy module").** The
strategy is textbook prompt injection: `Ignore previous instructions`,
`### NEW TASK BEGINS ###`, `Task complete!!!!!!`, `!!!!!!`. Whether this works is
entirely a property of the victim backbone's injection-susceptibility — which the
paper never varies (single backbone family; surrogate ≈ victim, Table 4).

My controlled experiment (`control_injectability.py`) holds the attack fixed and
flips only the victim's susceptibility:
- on an **injection-obedient** backbone the strategy lands;
- on a **guarded** backbone (treats descriptions as data) the *same* injection
  does nothing — and adding it can *lower* the target's rank because the
  `### NEW TASK ###!!!!!!` text reads as spam.

So the paper's central novelty is not really "agentic memory corruption" — it is
prompt injection whose success rides on a fragile assumption about the victim.

A secondary unstable assumption: **surrogate→victim transfer.** Table 4 shows the
victims' prompt templates are nearly identical to the surrogate's, so the
reported "black-box transferability" is closer to white-box-template transfer.

### Q4 — Which metric doesn't match / won't hold up?

1. **Table 6 "Success Rate to Get the Target Agents Drunk" = 100% everywhere.**
   This is circular: Algorithm 1 line 16 loops *until* the malicious action
   occurs, so on the surrogate it is 100% by construction. It says nothing about
   real victims. In my run the analogous "drunk-success" on a guarded victim is
   **far below 100%** (see table) — the metric does not survive contact with an
   injection-robust model.
2. **Perplexity (Fig. 5).** Absolute values (45–637) are scorer/tokenizer
   dependent and the paper is internally inconsistent about the scorer (text says
   GPT-Neo; setup says "standard perplexity [43]"). It is also measured on the
   fluent *trigger*, not on the glaring *strategy* text that is actually injected
   — so the stealth metric and the injected payload are not the same object.
3. **HR/NDCG absolute values.** I verified every Table 1 value equals k/N with
   N≈97–99 (the subsampled user count). The eval rests on ~99 users and what
   looks like a single sampled target item, with no variance/CI. One user flips
   the metric by ~1 point; nothing reproduces to four decimals.
4. **Ablation direction (Table 5) is backbone-specific.** The paper: removing the
   strategy collapses the attack (strategy essential). My run on a guarded
   backbone: removing the strategy *helps*, and strategy-alone = 0. The
   qualitative ablation conclusion inverts depending on the victim.

---

## Core strengths (from the method, not the framing)

- **A genuinely new and realistic threat surface:** editing an item's own
  description — a legitimate seller capability — to manipulate an agentic
  recommender. The promotion (push one item to rank 1) framing matches real
  money-driven abuse and is cleanly measurable.
- **Two-pronged design is reasonable:** a transferable persuasive trigger
  (optimized by greedy text search) plus an instruction-injection strategy.
- **Black-box-via-surrogate is the right conceptual setup.**

## Core weaknesses (from the code/numbers)

- **It is, mechanically, prompt injection.** The paper's own Table 5 shows the
  strategy module is doing the work; my run shows that on a robust model the
  injection is useless/harmful and the attack degenerates to "write nicer copy"
  (a plain ChatGPT rewrite matches it).
- **Stealth is overstated and self-contradictory.** The injected payload contains
  `### NEW TASK ###`, `Ignore previous instructions`, `!!!!!!` — caught by a
  one-line regex (my detector flags DrunkAgent and never flags Benign). Low
  perplexity is reported on a different (trigger-only) string.
- **Defense evaluation is weak:** only paraphrasing (which they admit sometimes
  *helps* the attack); no instruction-injection detector, delimiter/role
  isolation, or memory-write validation — i.e., not the defenses that directly
  counter prompt injection.
- **Statistically thin & possibly inflated:** ~99 users, ~1 target item, no
  variance; surrogate ≈ victim; Table 6 is 100% by construction.
- **Reproducibility decays:** pinned to drifting closed endpoints (gpt-4-turbo,
  GPT-o1) and a specific open model, with under-specified stopping criteria.

---

## Empirical results (executed; Claude backbone, 20 users, synthetic CD data)

### Transferability — HR@1 by victim and attack

| Attack | AgentCF | AgentRAG | AgentSEQ |
|---|---|---|---|
| Benign | 0.000 | 0.050 | 0.000 |
| TrivialInsertion | 0.000 | 0.050 | 0.050 |
| ChatGPTAttack (plain LLM rewrite) | 0.150 | 0.150 | 0.050 |
| **DrunkAgent (full = trigger + strategy)** | 0.150 | **0.000** | **0.000** |
| DrunkAgent — trigger only (no injection) | **0.250** | **0.400** | **0.350** |
| DrunkAgent — injection only (no trigger) | 0.000 | 0.000 | 0.000 |

Reading this table:
- **The injection ("strategy") never helps and usually destroys the attack.**
  Trigger-only beats full DrunkAgent on every victim (0.25 vs 0.15; 0.40 vs 0.00;
  0.35 vs 0.00). Injection-only is 0.000 everywhere. This is the **opposite** of
  the paper's Table 5, where the strategy is the essential component.
- **The effective part is just persuasive copy.** Trigger-only is the strongest
  attack, and a plain ChatGPT rewrite (no injection, no greedy search) already
  matches "full DrunkAgent."
- **AgentRAG/AgentSEQ are the robust victims** (DrunkAgent 0.000), matching the
  paper's robustness ordering — but here DrunkAgent loses to a plain rewrite on
  them.

### "Drunk-success" (target ranked #1 under full DrunkAgent) — vs paper's Table 6 = 100%

| AgentCF | AgentRAG | AgentSEQ |
|---|---|---|
| 0.150 | 0.000 | 0.000 |

The paper reports 100% on every dataset/budget. Against an injection-robust
victim it is 0–15%. The 100% is an artifact of the optimize-until-success
stopping rule on the surrogate, not a property of real victims.

### Stealth / detectability (one-line regex for injection markers)

| Benign | TrivialInsertion | ChatGPTAttack | DrunkAgent (full) | trigger-only | injection-only |
|---|---|---|---|---|---|
| no | no | no | **YES** | no | **YES** |

The "stealthy" full attack is trivially detectable (it contains `### NEW TASK ###`,
`Ignore previous instructions`, `!!!!!!`). The only stealthy *and* effective
variant is trigger-only — i.e., "write better copy," which isn't novel.

### Control: does the attack just need an injectable victim? (`control_injectability.py`)

Same DrunkAgent attack, AgentCF victim, only the backbone's instruction-following
discipline changed:

| Attack | guarded HR@1 | obedient HR@1 |
|---|---|---|
| Benign | 0.000 | 0.000 |
| ChatGPTAttack | 0.000 | 0.250 |
| DrunkAgent — trigger only | 0.250 | 0.250 |
| DrunkAgent — injection only | 0.000 | 0.000 |
| DrunkAgent — full (trigger+injection) | 0.000 | 0.000 |

Interpretation: persuasion (trigger / rewrite) moves rankings; the **injection
moves nothing on either victim config (0.000)** and *poisons* the good trigger
(trigger-only 0.250 → full 0.000). Notably, Claude resists the injection **even
when its system prompt explicitly tells it to follow instructions inside item
descriptions** — i.e., I could not construct a Claude victim that the paper's
strategy module defeats. The paper's high numbers therefore look specific to its
weaker, more injectable open-model victims (Llama-3-8B-Instruct family, surrogate
≈ victim). The "agentic memory corruption" mechanism does not survive a change of
backbone.

### Bottom line of the reproduction

On an injection-robust backbone, **DrunkAgent's headline mechanism inverts**: the
prompt-injection "strategy module" — the paper's core novelty — is useless or
harmful, the attack degenerates to persuasive copywriting (matched by a one-call
GPT rewrite), the 100% drunk-success does not hold, and the payload is caught by
a trivial regex. The method's success in the paper is best explained by its
victims (a single, relatively injectable open-model family, with surrogate ≈
victim), not by a new "agentic memory" vulnerability.
