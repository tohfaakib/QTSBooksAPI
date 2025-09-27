# 📚 QTSBook — Books Scraper, Scheduler & API

A production-ready solution that crawls [**books.toscrape.com**](https://books.toscrape.com), stores data in **MongoDB**, detects daily changes, and exposes a secure **FastAPI** for querying books and change logs. Includes a **dashboard** to trigger/resume crawls, run scheduled jobs on-demand, and view live logs.

---

## ✨ Features

### 🔎 Scraper (Scrapy)
- Crawls all categories & paginated listings with robust selectors, retries, HTTP cache, and polite throttling.
- Normalizes and stores each book in MongoDB (`books`), including:
  - Numeric price fields
  - Gzipped HTML snapshot (`raw_html_gz`)
- Idempotent upserts by URL; recommended indexes for fast API queries.

### 🔄 Change Detection
- Per-page **`content_hash`** (stable fingerprint).
- Detailed entry in `changes` for **new** and **update** events.
- Field-level diffs (`fields_changed`), `price_delta`, and a `significant` flag.
- Daily JSON/CSV reports + optional email alerts.

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
- **Start Crawl (Fresh)** — full crawl (recommended for daily runs).
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

## 🗄️ Data Model

### `books`
- Full book info (title, category, prices, rating, reviews).
- HTML snapshot (`raw_html_gz`).
- Stable `content_hash`.

### `changes`
- Captures diffs between crawls.
- `fields_changed`, `price_delta`, `significant` flag.

Indexes:

```js
db.books.createIndex({ url: 1 }, { unique: true });
db.books.createIndex({ name: "text" });
db.changes.createIndex({ changed_at: -1 });
```

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

---

## 📄 License

MIT (or your preferred license)
