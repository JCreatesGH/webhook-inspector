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
