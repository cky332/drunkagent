"""Controlled experiment: does DrunkAgent's effect depend on the victim being
injection-susceptible?

The paper's central novelty is the *strategy module* (prompt injection that
"gets the agent drunk"). It is evaluated on a single backbone family (Llama-3-8B
victims, with a near-identical surrogate). We hold the attack fixed and vary
ONLY the victim's susceptibility to instructions hidden in item descriptions:

  guarded  : treats item descriptions as data (a safety-tuned model's default)
  obedient : follows instructions found inside item descriptions (emulates a
             weak, highly injectable backbone)

If the attack works on `obedient` but not on `guarded`, then the paper's headline
mechanism is not a property of "agentic memory" at all -- it is just classic
prompt injection, and its success is a function of how injectable the victim LLM
happens to be.
"""
import os, json, random
from . import data, victims, attacks
from .metrics import aggregate

def eval_under(system_override, ds, users, base_cands, target_desc):
    tid = ds["target"]["id"]
    ranks = []
    for u, base in zip(users, base_cands):
        cand = [dict(c) for c in base]
        for c in cand:
            if c["id"] == tid:
                c["memory"] = target_desc
        rank, _ = victims.run_victim("AgentCF", ds, u, cand, tid,
                                     system_override=system_override)
        ranks.append(rank)
    return aggregate(ranks)["HR@1"]

def main():
    n_users = int(os.environ.get("N_USERS", "20"))
    ds = data.build_dataset(n_users=n_users)
    users = ds["users"]
    descs = attacks.make_attack_descriptions(ds)
    rnd = random.Random(2024)
    base_cands = [data.candidate_list(ds, u, ds["target"]["description"], rnd) for u in users]

    rows = ["Benign", "ChatGPTAttack", "DrunkAgent_noStrategy", "DrunkAgent_noGen", "DrunkAgent"]
    print(f"{'attack':24s} | guarded HR@1 | obedient HR@1")
    print("-" * 56)
    out = {}
    for atk in rows:
        g = eval_under(victims.SYS_GUARDED, ds, users, base_cands, descs[atk])
        o = eval_under(victims.SYS_OBEDIENT, ds, users, base_cands, descs[atk])
        out[atk] = {"guarded": g, "obedient": o}
        print(f"{atk:24s} |    {g:.3f}     |    {o:.3f}")
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "results", "control_injectability.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nsaved -> results/control_injectability.json")

if __name__ == "__main__":
    main()
