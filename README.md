# Hunting & Fishing Supply Co — Online Store

A full-stack outdoor-gear storefront for **Hunting & Fishing Supply Co**
(2667 Jackson Ave, Memphis, TN 38108 · +1 (406) 206-9144 ·
saleshuntingandfishingsupplyco@gmail.com).

Dark-tactical storefront with a 134-product catalog, cart, **quote requests**,
and a **no-online-payment checkout** (orders notify the owner, who contacts the
customer to confirm and arrange payment), plus a **password-protected admin
dashboard** for orders and inquiries. Data lives in a local SQLite database
(`outdoor.db`).

## Stack

- **FastAPI** + **Uvicorn** on **port 8002**
- **SQLAlchemy** over **SQLite** (`outdoor.db`)
- **Jinja2** server-rendered templates (multi-page, vanilla JS — no framework)
- **aiosmtplib** for Gmail SMTP email
- **python-dotenv** for configuration

## Quick start

```bash
# 1. Install dependencies
python3 -m pip install --user -r requirements.txt
#    (or with a venv:  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt)

# 2. Run — the DB is created and the 134-product catalog is seeded automatically.
uvicorn backend.main:app --host 0.0.0.0 --port 8002
#    Add --reload during development.
```

Open **http://localhost:8002**. Admin is at **http://localhost:8002/admin**.

## Project structure

```
backend/
  main.py            # FastAPI app, lifespan (auto-seed), storefront routes
  database.py        # SQLAlchemy engine / session / Base
  models.py          # Product, Order, Booking
  schemas.py         # Pydantic request models
  seed_data.py       # PRODUCTS_SEED (134 items) + sync_products() upsert
  routes/
    bookings.py      # POST /api/bookings/   (quote / inquiry)
    orders.py        # POST /api/orders/     (checkout, shipping logic)
    admin.py         # /api/admin/*  (HTTP Basic auth: stats + CRUD)
  services/
    email.py         # aiosmtplib sender + 4 branded email templates
templates/           # base, index, products, product_detail, checkout, _card
frontend/
  about.html         # standalone About page (FileResponse)
  admin.html         # standalone admin dashboard SPA (FileResponse)
static/css/main.css  # dark-tactical design system
static/js/main.js    # cart, quote modal, toast, filtering, checkout
static/images/placeholder.jpg
.env / .env.example  # configuration
outdoor.db           # SQLite database (created on first run)
```

## Configuration — `.env`

| Variable | Purpose |
| --- | --- |
| `BUSINESS_NAME`, `BUSINESS_EMAIL`, `BUSINESS_ADDRESS`, `OWNER_PHONE` | Shown throughout the site & emails |
| `OWNER_EMAIL` | Inbox that receives order & inquiry notifications |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Admin dashboard credentials (default `admin` / `changeme123`) |
| `SMTP_HOST/PORT/USER/PASSWORD` | Gmail SMTP. **Leave `SMTP_PASSWORD` blank to disable sending** (emails are logged, never sent). Use a Gmail **App Password**. |
| `DATABASE_URL` | SQLite URL (`sqlite:///./outdoor.db`) |

## How ordering works (no online payment)

1. Customer adds items to the cart and submits the checkout form.
2. `POST /api/orders/` saves the order and computes shipping:
   - Domestic: **free over $5,000**, otherwise **$500 flat**.
   - International: per-region freight ($800–$1,600).
3. Two emails are sent (when SMTP is configured): a confirmation to the
   customer and an **"ACTION REQUIRED"** notice to the owner.
4. The owner contacts the customer to confirm availability and arrange payment
   (ACH/Wire, Zelle, or other arranged method). No card is processed online.

"Request a Quote" buttons post to `POST /api/bookings/` and notify the owner the
same way.

## Admin dashboard

Visit **/admin**, log in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`. You get:

- Stat cards: orders, pending orders, inquiries, pending inquiries, pipeline revenue
- Orders & Inquiries tables with inline **status updates**, **detail view**, and **delete**

All admin API endpoints are protected with HTTP Basic auth (timing-safe check).

## Catalog

`backend/seed_data.py` is the single source of truth. On startup `sync_products()`
upserts the catalog (insert new, update changed, remove deleted) so editing the
seed and restarting reconciles the DB. Products use `static/images/placeholder.jpg`
— drop real images into `static/images/` and set each product's `image` path to
use them.

> Note: the 12 category counts total **134** products (the "120" figure in the
> original brief was a label; every per-category count is built exactly as specified).

## Resetting the database

```bash
rm -f outdoor.db && uvicorn backend.main:app --port 8002   # re-seeds on startup
```
