# Webhook Inspector

[![CI](https://github.com/JCreatesGH/webhook-inspector/actions/workflows/ci.yml/badge.svg)](https://github.com/JCreatesGH/webhook-inspector/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A self-hostable "requestbin": generate a throwaway URL, point any webhook or HTTP client at it, and watch requests stream into a live UI — method, path, query, headers, and body. Genuinely useful for debugging Stripe/GitHub/Slack webhooks locally.

![screenshot](assets/screenshot.png)

## Run it

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000
# or
docker build -t inspector . && docker run -p 8000:8000 inspector
```

Open the page, copy your bin URL (`/b/<id>`), then fire a request:

```bash
curl -X POST localhost:8000/b/<id>/webhook?source=stripe \
     -H 'X-Signature: abc' -d '{"event":"charge.succeeded"}'
```

It appears in the UI within ~1.5s.

## API

| Method | Route | Purpose |
|--------|-------|---------|
| `POST` | `/api/bins` | create a bin → `{ bin_id }` |
| `ANY`  | `/b/{bin_id}/...` | capture a request (any method/path), returns 200 |
| `GET`  | `/api/bins/{id}/requests?since=N` | poll for new captured requests |
| `DELETE` | `/api/bins/{id}/requests` | clear the bin |

## Design

- **`BinStore`** is an in-memory, **bounded ring buffer** per bin (oldest requests drop off) with monotonic request IDs — so the front end can poll with `?since=` and only fetch new ones. It's pure and unit-tested.
- The capture route accepts every common method via a single `api_route`, recording method, path, query, headers, and decoded body with a UTC timestamp.

## Development

```bash
python -m pytest -q   # 9 tests (store + API: capture, methods, query, headers, body, polling)
```

## License

MIT
