from app.store import BinStore


def test_create_and_capture():
    s = BinStore()
    b = s.create_bin()
    assert s.exists(b)
    r = s.capture(b, method="POST", path="/x", query={"a": "1"},
                  headers={"h": "v"}, body="hi", ts="t")
    assert r.id == 1
    assert s.requests(b)[0].method == "POST"


def test_since_filter():
    s = BinStore()
    b = s.create_bin()
    for i in range(3):
        s.capture(b, method="GET", path="/", query={}, headers={}, body="", ts="t")
    assert [r.id for r in s.requests(b, since=1)] == [2, 3]


def test_ring_buffer_bounded():
    s = BinStore(max_per_bin=2)
    b = s.create_bin()
    for i in range(5):
        s.capture(b, method="GET", path="/", query={}, headers={}, body=str(i), ts="t")
    reqs = s.requests(b)
    assert len(reqs) == 2
    assert [r.body for r in reqs] == ["3", "4"]


def test_unknown_bin_raises():
    s = BinStore()
    try:
        s.requests("nope")
        assert False
    except KeyError:
        pass


def test_lru_eviction_of_oldest_bin():
    s = BinStore(max_bins=2)
    a = s.create_bin()
    b = s.create_bin()
    s.capture(a, method="GET", path="/", query={}, headers={}, body="", ts="t")  # touch a
    c = s.create_bin()      # over cap -> evict LRU, which is now b (a was just touched)
    assert s.exists(a) and s.exists(c) and not s.exists(b)


def test_body_is_truncated():
    s = BinStore(max_body=10)
    b = s.create_bin()
    r = s.capture(b, method="POST", path="/", query={}, headers={}, body="x" * 50, ts="t")
    assert r.truncated is True and len(r.body) == 10


def test_response_config_lifecycle():
    s = BinStore()
    b = s.create_bin()
    assert s.has_custom_response(b) is False
    assert s.response(b)["status"] == 200
    s.set_response(b, status=503, body="busy", content_type="text/plain")
    assert s.has_custom_response(b) and s.response(b)["body"] == "busy"
    s.reset_response(b)
    assert not s.has_custom_response(b)
