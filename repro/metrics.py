"""Ranking metrics: HR@K and NDCG@K, matching the paper's evaluation (K=1,2,3).

For a single promoted target item, HR@K = fraction of users for whom the target
appears in the top-K of the agent's output ranking; NDCG@K uses the standard
1/log2(rank+1) gain for the (single relevant) target. This mirrors the paper's
target-promotion setup.
"""
import math

def hit_at_k(rank, k):
    return 1.0 if (rank is not None and rank <= k) else 0.0

def ndcg_at_k(rank, k):
    if rank is None or rank > k:
        return 0.0
    return 1.0 / math.log2(rank + 1)

def aggregate(ranks, ks=(1, 2, 3)):
    """ranks: list of target ranks (1-based) or None (not found / out of list).
    Returns dict with HR@k and NDCG@k averaged over users."""
    n = len(ranks)
    out = {}
    for k in ks:
        out[f"HR@{k}"] = sum(hit_at_k(r, k) for r in ranks) / n
        out[f"NDCG@{k}"] = sum(ndcg_at_k(r, k) for r in ranks) / n
    return out
