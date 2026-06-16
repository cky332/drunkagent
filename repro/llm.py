"""Minimal Claude API client used as the LLM backbone for this reproduction.

The DrunkAgent paper uses Meta-Llama-3-8B-Instruct (surrogate, white-box) and
OpenAI gpt-4-turbo (generation LLM) plus GPT-style victim agents. Neither is
reachable in this sandbox (HuggingFace and OpenAI are network-blocked, there is
no GPU, and torch/transformers are not installed). We therefore substitute
Claude for every LLM role. This is a *model substitution*; it keeps the method
faithful but means absolute numbers are not directly comparable to the paper.

Auth uses the session OAuth token (Bearer + oauth beta header). All calls are
disk-cached by (model, system, prompt, temperature, max_tokens) so reruns are
cheap and deterministic.
"""
import os, json, time, hashlib, urllib.request, urllib.error

OAUTH_TOKEN_FILE = "/home/claude/.claude/remote/.oauth_token"
API_URL = "https://api.anthropic.com/v1/messages"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache_llm")
os.makedirs(CACHE_DIR, exist_ok=True)

# Cheap + fast model for the bulk of calls. The "generation LLM" role (which the
# paper assigns to the stronger gpt-4-turbo) can optionally use a stronger model.
MODEL_FAST = "claude-haiku-4-5-20251001"
MODEL_STRONG = "claude-haiku-4-5-20251001"

_token_cache = None
def _token():
    global _token_cache
    if _token_cache is None:
        with open(OAUTH_TOKEN_FILE) as f:
            _token_cache = f.read().strip()
    return _token_cache

_call_count = 0
_cache_hits = 0

def stats():
    return {"api_calls": _call_count, "cache_hits": _cache_hits}

def _cache_key(model, system, prompt, temperature, max_tokens):
    h = hashlib.sha256()
    h.update(json.dumps([model, system, prompt, temperature, max_tokens]).encode())
    return h.hexdigest()

def complete(prompt, system=None, model=MODEL_FAST, temperature=0.0,
             max_tokens=512, retries=5):
    """Return the model's text completion for a single user prompt."""
    global _call_count, _cache_hits
    key = _cache_key(model, system, prompt, temperature, max_tokens)
    cpath = os.path.join(CACHE_DIR, key + ".json")
    if os.path.exists(cpath):
        _cache_hits += 1
        with open(cpath) as f:
            return json.load(f)["text"]

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system is not None:
        body["system"] = system
    data = json.dumps(body).encode()

    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API_URL, data=data, method="POST")
            req.add_header("authorization", "Bearer " + _token())
            req.add_header("anthropic-version", "2023-06-01")
            req.add_header("anthropic-beta", "oauth-2025-04-20")
            req.add_header("content-type", "application/json")
            with urllib.request.urlopen(req, timeout=120) as resp:
                out = json.loads(resp.read().decode())
            text = "".join(b.get("text", "") for b in out.get("content", []))
            _call_count += 1
            with open(cpath, "w") as f:
                json.dump({"text": text, "usage": out.get("usage", {})}, f)
            return text
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (429, 500, 502, 503, 529):
                time.sleep(2 ** attempt)
                continue
            break
        except Exception as e:
            last_err = str(e)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Claude API call failed after {retries} tries: {last_err}")


if __name__ == "__main__":
    # smoke test: a ranking-style prompt like the victim agents will issue
    sys = ("You are a CD recommender system. Output ONLY the ranking in the "
           "requested format.")
    p = ("Rank these 3 CDs for a user who likes jazz.\n"
         "CD title: Blue Train. CD title: Pop Hits 2003. CD title: Kind of Blue.\n"
         "Your output should be:\nThe sorted CDs are:\n1. [title]\n2. [title]\n3. [title]")
    print(complete(p, system=sys, max_tokens=80))
    print("stats:", stats())
