# $12 Hug Test 🥊

Can a $12/month VPS survive the Reddit Hug of Death?

This repo documents load-testing experiments on a $12 Linode box (1 CPU, 2 GB RAM, 50 GB storage) running FastAPI + SQLite.

We wanted to know: what happens if my indie side-project actually hits the Reddit front page?

## 🔧 Setup

- **Server**: Linode, 1 vCPU / 2 GB RAM / 50 GB storage
- **Stack**: FastAPI, SQLite (FTS5), Gunicorn + Uvicorn workers, Nginx (TLS via Certbot)
- **Rules**: no upgrades, no Postgres, no Kubernetes. Just the $12 box.

## 🐹 The App

Minimal journal app (MicroJournal):

- `/` → homepage (read entries)
- `/search?q=term` → full-text search
- `/add` → add entry (redirect)
- `/add_raw` → raw write endpoint (used for load tests)

## 🚦 Load Testing

We used [bombardier](https://github.com/codesenberg/bombardier) to simulate traffic spikes:

- **Page 4 Reddit** (~5k/day): ~1 RPS
- **Page 2 Reddit** (~50k/day): ~10 RPS
- **Page 1 Reddit** (~500k/day): ~100 RPS (≈1k–2k simultaneous users)

**Test cases:**

- Read (`/`)
- Search (`/search`)
- Write (`/add_raw`)
- Mixed (90% reads, 10% writes)

Logs: see `/logs` (sanitized).

## 🐛 Bottlenecks Found

- `/search` with naive LIKE pegged CPU at 100%
- Concurrent writes caused database locked

## ✅ Fixes

- **FTS5 full-text search** → efficient indexing
- **WAL mode** → concurrent reads + writes
- **Nginx micro-caching** (1–5s TTL) → absorbed bursts

## 📊 Results

- **Reads**: stable at 100 RPS (~140ms latency, ~60% CPU)
- **Search**: from 5xx → clean 200s with FTS5
- **Writes**: from "DB locked" → stable 204s with WAL
