from myers.memory import HashingEmbedder, InMemoryCodeStore
from myers.memory.embedder import cosine, tokenize


def test_embedder_is_deterministic_and_normalized():
    e = HashingEmbedder(dim=128)
    a, b = e.embed("def charge_customer(amount):"), e.embed("def charge_customer(amount):")
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9  # unit length


def test_tokenize_splits_snake_and_camel():
    toks = set(tokenize("def refreshSession(user_id):"))
    assert "refreshsession" in toks and "refresh" in toks and "session" in toks
    assert "user" in toks and "id" in toks


def test_hybrid_search_finds_semantically_related_chunk():
    store = InMemoryCodeStore()
    store.add_chunk("billing/stripe.py", "def charge_customer(amount):\n    return stripe.charge(amount)")
    store.add_chunk("auth/session.py", "def refresh_session(user):\n    return renew(user.token)")
    top = store.hybrid_search("charge the customer for a payment amount", k=1)
    assert top and top[0].path == "billing/stripe.py"


def test_exact_identifier_match_wins_for_precise_name():
    store = InMemoryCodeStore()
    store.add_chunk("a.py", "def alpha():\n    return 1")
    store.add_chunk("b.py", "def refresh_session(user):\n    return renew(user)")
    top = store.hybrid_search("refresh_session", k=1)
    assert top[0].path == "b.py"


def test_empty_store_returns_nothing():
    assert InMemoryCodeStore().hybrid_search("anything", k=3) == []


def test_ingest_diff_context_indexes_added_lines():
    from myers.diffing import parse_unified_diff
    diff = ("diff --git a/x.py b/x.py\nnew file mode 100644\n--- /dev/null\n+++ b/x.py\n"
            "@@ -0,0 +1,2 @@\n+def charge():\n+    pass\n")
    store = InMemoryCodeStore()
    n = store.ingest_diff_context(parse_unified_diff(diff))
    assert n >= 1 and len(store) >= 1
