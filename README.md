# 📚 QTSBook — Books Scraper, Scheduler & API

A production-ready solution that crawls [**books.toscrape.com**](https://books.toscrape.com), stores data in **MongoDB**, detects daily changes, and exposes a secure **FastAPI** for querying books and change logs. Includes a **dashboard** to trigger/resume crawls, run scheduled jobs on-demand, and view live logs.

---

## 🚀 Setup

### Prerequisites
- Install **Docker** & **Docker Compose**

### Configure Environment
Copy and edit:

```bash
cp .env.example .env
```

### Launch the stack

```bash
docker compose up -d --build
```

### Where to go
- **API/Dashboard** → [http://localhost:8000](http://localhost:8000)
- **Swagger UI** → [http://localhost:8000/docs](http://localhost:8000/docs)
- **Dashboard** → [http://localhost:8000/dashboard](http://localhost:8000/dashboard) (Basic Auth)
- **Mongo-Express (optional)** → [http://localhost:8081](http://localhost:8081)

> Run a crawl first (Dashboard → **Start Crawl**) to populate data.

---

## 🕷️ Crawling

### Dashboard controls
- **Start Crawl (Fresh)** — full crawl (for daily runs).
- **Start Crawl (Resume if possible)** — resume interrupted crawl (Scrapy JOBDIR).
- **Stop Crawl** — terminate current crawl.
- **View Logs** — live crawler output.

### CLI (inside container)

```bash
# Fresh crawl
docker compose exec app bash -lc "python scheduler/run_crawl.py"

# Resume crawl
docker compose exec app bash -lc "QTS_SCRAPY_RESUME=true python scheduler/run_crawl.py"
```

**Fresh vs Resume (important):**
- Fresh = revisits all pages → required for accurate change detection.
- Resume = only for interrupted runs. Never use for scheduled daily jobs.

---

## 📅 Scheduler (Daily Job)

- Implemented in `scheduler/schedule_daily.py` with APScheduler.
- Runs daily at **09:00** (based on `QTS_TIMEZONE`).
- Workflow: fresh crawl → compute change summary → save reports → send email.
- Dashboard → **Run Scheduled Job Now** = same flow, on demand.

Manual run:

```bash
docker compose exec app bash -lc "python scheduler/schedule_daily.py"
```

---

## ✨ Features

### 🔎 Scraper (Scrapy)
- Crawls all categories & paginated listings with robust selectors, retries, HTTP cache, and polite throttling.
- Normalizes and stores each book in MongoDB (`books`), including:
  - Numeric price fields
  - Gzipped HTML snapshot (`raw_html_gz`)
- Idempotent upserts by URL.

### 🔄 Change Detection
- Per-page **`content_hash`** (stable fingerprint).
- Detailed entry in `changes` for **new** and **update** events.
- Field-level diffs (`fields_changed`), `price_delta`, and a `significant` flag.
- Daily JSON/CSV reports + email alerts.

### ⏰ Scheduler
- APScheduler daily run (timezone from `.env`).
- Dashboard button: **“Run Scheduled Job Now”**.

### ⚡ API (FastAPI)
- `GET /books` — filter, sort, paginate books.
- `GET /books/{id}` — full book details.
- `GET /changes` — filter by type, significance, URL, time windows.
- API-key auth and per-key, per-path rate limiting.
- Interactive **Swagger UI** with API key security scheme.

### 🖥️ Dashboard
- Start **fresh** crawl.
- Start **resume-if-possible** crawl (Scrapy JOBDIR).
- Stop crawl, view live logs.
- Quick links: Swagger, Docs, Mongo-Express.

### 🐳 Dockerized
- App + MongoDB (+ optional Mongo-Express).
- Persistent volumes for data and reports.

### ✅ Tests
- Pytest suite for endpoints, rate limiting, and reports.
- Coverage reporting.

---

## 🔑 API

### Authentication & Rate Limiting
- Every request requires:

```http
X-API-Key: <QTS_API_KEY>
```

- Rate limit: **100 req/hour** per (API key, path).
- Exceeding → `429 Too Many Requests`.

### Endpoints
- `GET /books` — query by category, rating, price range, search term.
- `GET /books/{id}` — book details.
- `GET /changes` — filter by kind, significance, time window.
- `GET /reports/list` — list available daily reports.
- `GET /reports/today` — fetch today’s report (`json|csv`).

---

# 📂 MongoDB Document Structure

The application uses two primary collections: **`books`** and **`changes`**.

---

## 📝 `books` Collection

Stores the latest snapshot of each crawled book.

**Sample document:**

```json
{
  "_id": { "$oid": "6512bd43d9caa6e02c990b0a" },
  "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "name": "A Light in the Attic",
  "description": "A collection of humorous poems and drawings.",
  "category": "Poetry",
  "image_url": "https://books.toscrape.com/media/cache/fe/9a/fe9a...jpg",
  "rating": 4,
  "availability": "In stock (22 available)",
  "price_incl_tax": "£51.77",
  "price_excl_tax": "£48.77",
  "price_incl_tax_num": 51.77,
  "price_excl_tax_num": 48.77,
  "tax": "£3.00",
  "num_reviews": 0,
  "crawled_at": { "$date": "2025-09-27T14:23:16.725Z" },
  "source": "books.toscrape.com",
  "content_hash": "sha256:6d6b8b5f9c8f...b7",
  "raw_html_gz": { "$binary": "H4sIAAAAAAAA/4xYXW...", "$type": "00" }
}
```

**Field reference:**

- `url` *(string, unique)* — canonical product URL  
- `name` *(string)*  
- `description` *(string)*  
- `category` *(string)*  
- `image_url` *(string)*  
- `rating` *(int, 0–5)*  
- `availability` *(string)*  
- `price_incl_tax`, `price_excl_tax`, `tax` *(string as scraped, e.g. "£51.77")*  
- `price_incl_tax_num`, `price_excl_tax_num` *(number, for sorting/filtering)*  
- `num_reviews` *(int)*  
- `crawled_at` *(datetime, UTC)*  
- `source` *(string, e.g. "books.toscrape.com")*  
- `content_hash` *(string, sha256 fingerprint of salient content)*  
- `raw_html_gz` *(binary, gzipped HTML snapshot; optional)*  

---

## 🔄 `changes` Collection

Stores change history between crawls. Each entry records either a **new** book or an **update**.

**Sample documents:**

```json
{
  "_id": { "$oid": "6512bd43d9caa6e02c990b0b" },
  "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "changed_at": { "$date": "2025-09-28T09:05:11.112Z" },
  "change_kind": "new",
  "significant": true,
  "fields_changed": {
    "price_incl_tax": { "prev": null, "new": "£51.77" },
    "availability":   { "prev": null, "new": "In stock (22 available)" }
  },
  "price_delta": 51.77,
  "prev_hash": null,
  "new_hash": "sha256:6d6b8b5f9c8f...b7"
}
```

```json
{
  "_id": { "$oid": "6512bd43d9caa6e02c990b0c" },
  "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "changed_at": { "$date": "2025-10-01T10:14:03.004Z" },
  "change_kind": "update",
  "significant": true,
  "fields_changed": {
    "price_incl_tax": { "prev": "£51.77", "new": "£49.99" },
    "availability":   { "prev": "In stock (22 available)", "new": "In stock (5 available)" }
  },
  "price_delta": -1.78,
  "prev_hash": "sha256:6d6b8b5f9c8f...b7",
  "new_hash":  "sha256:9f3e2a1c0d4e...21"
}
```

**Field reference:**

- `url` *(string)* — FK to `books.url`  
- `changed_at` *(datetime, UTC)*  
- `change_kind` *(enum: `"new"` | `"update"`)*  
- `significant` *(bool)*  
- `fields_changed` *(object: `{ field: { prev, new } }`)*  
- `price_delta` *(number; 0 for non-price updates)*  
- `prev_hash`, `new_hash` *(strings; content fingerprints)*  

---

## 📊 Reports & Alerts

- Daily reports in `./reports/`:
  - `changes_YYYY-MM-DD.json`
  - `changes_YYYY-MM-DD.csv`
- Email alerts (optional) → when new items or significant changes are detected.

---

## 🧪 Tests & Coverage

Run tests + coverage:

```bash
docker compose exec app bash -lc "coverage run -m pytest -q && coverage report -m"
```

Generate HTML report:

```bash
docker compose exec app bash -lc "coverage html && ls -l htmlcov/index.html"
```

---

## ⚙️ Operational Notes

- API key: always send `X-API-Key`.
- Dashboard auth: `QTS_ADMIN_USER` / `QTS_ADMIN_PASS`.
- Scheduler: timezone controlled by `QTS_TIMEZONE`.
- Resume: only for interrupted runs (not for daily jobs).
- Mongo-Express: optional UI.

---

## 🛠️ Troubleshooting

- **401/403 despite Authorized in Swagger**  
  → Ensure `X-API-Key` matches `.env` and container is restarted.

- **Resume not working**  
  → Check `QTS_SCRAPY_RESUME=true` and `./jobdata/books/` exists.

