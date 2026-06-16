"""Synthetic but realistic CD/music dataset for the reproduction.

The paper uses Amazon Review Data (CDs & Vinyl, Office Products, Musical
Instruments) and Yelp. None can be downloaded here (HuggingFace / generic web
are network-blocked; only github.com is reachable). We therefore build a small,
self-contained dataset in the same *shape* as the paper's setup:

  * items have a title, a category, and a textual description (the item agent's
    initial "memory");
  * users have a natural-language preference profile (the user agent's memory)
    and an interaction history;
  * a designated target item is the thing the attacker wants to promote.

Everything is deterministic (seed=2024, matching the paper) so runs are
reproducible.
"""
import random

SEED = 2024

# (title, genre, description)
_CATALOG = [
    ("Kind of Blue", "Jazz", "A landmark modal jazz album with relaxed trumpet and piano improvisation."),
    ("Blue Train", "Jazz", "Hard bop tenor saxophone session with warm horn arrangements."),
    ("A Love Supreme", "Jazz", "Spiritual free-leaning jazz suite driven by expressive saxophone."),
    ("Time Out", "Jazz", "Cool jazz quartet famous for unusual time signatures and piano hooks."),
    ("Dark Side of the Moon", "Rock", "Progressive rock concept album with lush synths and guitar solos."),
    ("Led Zeppelin IV", "Rock", "Hard rock classic with blues riffs and soaring vocals."),
    ("Nevermind", "Rock", "Grunge rock with raw guitars and catchy distorted hooks."),
    ("OK Computer", "Rock", "Art rock exploring alienation with layered guitars and electronics."),
    ("The Wall", "Rock", "Theatrical progressive rock double album with narrative lyrics."),
    ("Thriller", "Pop", "Polished pop album with danceable grooves and radio hooks."),
    ("1989", "Pop", "Synth-pop record with bright melodies and arena choruses."),
    ("Back to Black", "Pop", "Retro soul-pop with vintage production and emotive vocals."),
    ("Random Access Memories", "Electronic", "Disco-tinged electronic album with live instrumentation."),
    ("Discovery", "Electronic", "French house electronic record with filtered synth hooks."),
    ("Selected Ambient Works", "Electronic", "Mellow ambient techno with hypnotic analog textures."),
    ("The Chronic", "HipHop", "West coast hip hop with funky g-funk synths and deep bass."),
    ("Illmatic", "HipHop", "Lyrical east coast hip hop over jazzy boom-bap production."),
    ("To Pimp a Butterfly", "HipHop", "Jazz and funk infused hip hop with dense socially conscious lyrics."),
    ("Master of Puppets", "Metal", "Thrash metal with fast riffing and complex song structures."),
    ("Paranoid", "Metal", "Heavy metal foundations with doom riffs and dark themes."),
    ("The Number of the Beast", "Metal", "Melodic heavy metal with galloping bass and twin guitars."),
    ("Four Seasons", "Classical", "Baroque violin concertos depicting the seasons."),
    ("Symphony No. 9", "Classical", "Romantic symphony with a famous triumphant choral finale."),
    ("The Planets", "Classical", "Orchestral suite with vivid programmatic movements."),
    ("At Folsom Prison", "Country", "Live country album with storytelling and acoustic warmth."),
    ("Red Headed Stranger", "Country", "Sparse outlaw country concept record with gentle guitar."),
    ("Harvest", "Folk", "Mellow folk rock with acoustic guitar and heartfelt vocals."),
    ("Blood on the Tracks", "Folk", "Confessional folk songwriting with acoustic arrangements."),
    ("The Healing Game", "Blues", "Soulful blues with brass, organ and gravelly vocals."),
    ("Texas Flood", "Blues", "Electric blues guitar showcase with fiery solos."),
]

# Genres ranked by popularity (used to mark "popular items" the paper places
# ahead of the target in candidate lists).
_POPULARITY = ["Pop", "Rock", "HipHop", "Electronic", "Jazz", "Metal",
               "Classical", "Country", "Blues", "Folk"]

# The target item: a bland, niche product users would not naturally rank highly.
TARGET_ITEM = {
    "id": "T0",
    "title": "Quiet Afternoons Vol. 7",
    "category": "Spoken Word; Relaxation; Niche",
    "description": "A spoken-word relaxation compilation with field recordings and slow narration.",
}

_USER_PROFILES = [
    ("Jazz", "I love jazz, especially modal and hard bop; I enjoy expressive saxophone and piano."),
    ("Rock", "I am a classic and progressive rock fan; I like guitar solos and concept albums."),
    ("Pop", "I enjoy polished pop with catchy hooks and danceable production."),
    ("Electronic", "I like electronic music: house, techno and ambient textures."),
    ("HipHop", "I am into hip hop, both boom-bap and modern; I value strong lyricism."),
    ("Metal", "I love metal, especially thrash and heavy metal with fast riffs."),
    ("Classical", "I appreciate classical and orchestral music, baroque to romantic."),
    ("Country", "I enjoy country and outlaw country with storytelling lyrics."),
]


def build_dataset(n_users=24, seed=SEED):
    rnd = random.Random(seed)
    items = []
    for i, (title, genre, desc) in enumerate(_CATALOG):
        items.append({"id": f"I{i}", "title": title, "category": genre,
                      "description": desc, "genre": genre,
                      "popularity": _POPULARITY.index(genre)})
    by_genre = {}
    for it in items:
        by_genre.setdefault(it["genre"], []).append(it)

    users = []
    for u in range(n_users):
        genre, profile = _USER_PROFILES[u % len(_USER_PROFILES)]
        liked = list(by_genre.get(genre, []))
        rnd.shuffle(liked)
        # short interaction history of same-genre items (chronological)
        history = liked[: min(3, len(liked))]
        users.append({
            "id": f"U{u}", "genre": genre, "memory": profile,
            "history": [h["id"] for h in history],
        })

    # popular items = the most popular genres' items, used as strong distractors
    popular = sorted(items, key=lambda it: it["popularity"])[:9]
    return {"items": {it["id"]: it for it in items}, "users": users,
            "popular": [p["id"] for p in popular], "target": dict(TARGET_ITEM)}


def candidate_list(ds, user, target_desc, rnd, n=10):
    """Build a 10-item candidate list for `user`: popular distractors + the
    target, with the target placed LAST (popular items before it), exactly as
    the paper does in section 3.2.1."""
    items = ds["items"]
    pool = [iid for iid in items
            if iid not in user["history"]]
    # prefer popular items as distractors (paper: popular items as candidates)
    distractors = [iid for iid in ds["popular"] if iid not in user["history"]]
    others = [iid for iid in pool if iid not in distractors]
    rnd.shuffle(others)
    chosen = (distractors + others)[: n - 1]
    cand = []
    for iid in chosen:
        it = items[iid]
        cand.append({"id": iid, "title": it["title"], "memory": it["description"]})
    # target placed last (popular candidates before the target)
    cand.append({"id": ds["target"]["id"], "title": ds["target"]["title"],
                 "memory": target_desc})
    return cand


if __name__ == "__main__":
    ds = build_dataset()
    print("items:", len(ds["items"]), "users:", len(ds["users"]))
    print("target:", ds["target"]["title"])
    rnd = random.Random(SEED)
    cand = candidate_list(ds, ds["users"][0], ds["target"]["description"], rnd)
    print("user0 genre:", ds["users"][0]["genre"], "| candidates:")
    for c in cand:
        print("  ", c["id"], c["title"])
