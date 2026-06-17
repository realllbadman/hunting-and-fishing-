import os
import json
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load .env BEFORE importing backend modules — several read os.getenv at import.
load_dotenv()

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from backend.database import Base, engine, SessionLocal, get_db
from backend import models  # noqa: F401 — register models on Base
from backend.models import Product
from backend.seed_data import sync_products
from backend.routes import bookings, orders, admin

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR  = os.path.join(BASE_DIR, "frontend")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR    = os.path.join(BASE_DIR, "static")

BUSINESS = {
    "name":     os.getenv("BUSINESS_NAME", "Hunting & Fishing Supply Co"),
    "email":    os.getenv("BUSINESS_EMAIL", "saleshuntingandfishingsupplyco@gmail.com"),
    "phone":    os.getenv("OWNER_PHONE", "+14062069144"),
    "phone_display": "+1 (406) 206-9144",
    "address":  os.getenv("BUSINESS_ADDRESS", "2667 Jackson Ave, Memphis, TN 38108"),
}


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    # Lightweight migration: add columns introduced after the table was created.
    from sqlalchemy import text as _text
    with engine.connect() as _conn:
        try:
            _conn.execute(_text("ALTER TABLE orders ADD COLUMN payment_method TEXT"))
            _conn.commit()
        except Exception:
            pass  # column already exists
        try:
            _conn.execute(_text("ALTER TABLE products ADD COLUMN price_max FLOAT"))
            _conn.commit()
        except Exception:
            pass  # column already exists
    db = SessionLocal()
    try:
        sync_products(db)
    finally:
        db.close()
    yield


# CRITICAL Python 3.12 / Jinja2 fix: disable template caching.
_jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), cache_size=0)
templates = Jinja2Templates(env=_jinja_env)
# Expose business details to every template.
_jinja_env.globals["business"] = BUSINESS

app = FastAPI(title="Hunting & Fishing Supply Co", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_cache_html(request: Request, call_next):
    """Stop browsers caching rendered HTML so content edits show immediately.
    Static assets (/static) keep their own ?v= cache-busting and are untouched."""
    response = await call_next(request)
    ctype = response.headers.get("content-type", "")
    if ctype.startswith("text/html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ─────────────────────────── Storefront routes ───────────────────────────

CATEGORY_LABELS = {
    "trolling-motors": "Trolling Motors",
    "fish-finders": "Fish Finders",
    "small-outboards": "Small Outboards",
    "thermal-night-vision": "Thermal & Night Vision",
    "rifle-scopes": "Rifle Scopes",
    "hunting-blinds": "Hunting Blinds",
    "ammo": "Ammo",
    "kayaks": "Kayaks",
    "dog-kennels": "Dog Kennels",
    "crossbows-bows": "Crossbows & Bows",
    "chicken-coops": "Chicken Coops",
    "reloading-powder": "Reloading Powder",
}


def _interleave(products: list, chunk: int = 4) -> list:
    """Mix categories so the grid does not show one category in a long block."""
    buckets: dict[str, list] = {}
    for p in products:
        buckets.setdefault(p.category, []).append(p)
    order = list(buckets.keys())
    out = []
    while any(buckets[c] for c in order):
        for c in order:
            for _ in range(chunk):
                if buckets[c]:
                    out.append(buckets[c].pop(0))
    return out


@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    def top(category, brands, limit):
        q = db.query(Product).filter(Product.category == category, Product.in_stock == 1)
        if brands:
            q = q.filter(Product.brand.in_(brands))
        return q.order_by(Product.price.desc()).limit(limit).all()

    motors = top("trolling-motors", ["Minn Kota", "Lowrance"], 4)
    finders = top("fish-finders", ["Humminbird", "Garmin"], 3)
    hunting = (
        top("hunting-blinds", None, 1)
        + top("thermal-night-vision", None, 1)
        + top("rifle-scopes", None, 1)
    )

    # Zip the three groups together so categories alternate in the grid.
    featured = []
    pools = [motors, finders, hunting]
    idxs = [0, 0, 0]
    while len(featured) < 10 and any(idxs[i] < len(pools[i]) for i in range(3)):
        for i in range(3):
            if idxs[i] < len(pools[i]):
                featured.append(pools[i][idxs[i]])
                idxs[i] += 1
            if len(featured) >= 10:
                break

    all_products = db.query(Product).all()
    brand_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for p in all_products:
        brand_counts[p.brand] = brand_counts.get(p.brand, 0) + 1
        category_counts[p.category] = category_counts.get(p.category, 0) + 1
    brand_counts = dict(sorted(brand_counts.items(), key=lambda kv: -kv[1]))

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "featured": featured,
            "brand_counts": brand_counts,
            "category_counts": category_counts,
            "category_labels": CATEGORY_LABELS,
            "total_count": len(all_products),
        },
    )


@app.get("/products")
def products_page(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Product.name.ilike(like)) | (Product.brand.ilike(like))
        )
    products = query.all()
    # Mix categories only when showing the full, unfiltered catalog.
    if not category and not q:
        products = _interleave(products)
    total_count = db.query(Product).count()
    return templates.TemplateResponse(
        request,
        "products.html",
        {
            "products": products,
            "q": q,
            "current_category": category,
            "category_label": CATEGORY_LABELS.get(category) if category else None,
            "category_labels": CATEGORY_LABELS,
            "total_count": total_count,
        },
    )


@app.get("/products/{slug}")
def product_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    features = json.loads(product.features) if product.features else []
    related = (
        db.query(Product)
        .filter(Product.category == product.category, Product.slug != slug)
        .limit(4)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "product_detail.html",
        {
            "product": product,
            "features": features,
            "related": related,
            "category_labels": CATEGORY_LABELS,
        },
    )


@app.get("/checkout")
def checkout_page(request: Request):
    return templates.TemplateResponse(request, "checkout.html", {})


@app.get("/about")
def about_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "about.html"))


@app.get("/contact")
def contact_page(request: Request):
    return templates.TemplateResponse(request, "contact.html", {})


@app.get("/financing")
def financing_page(request: Request):
    return templates.TemplateResponse(request, "financing.html", {})


@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))


# ───────────────────────────── API routers ──────────────────────────────
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(orders.router,   prefix="/api/orders",   tags=["orders"])
app.include_router(admin.router,    prefix="/api/admin",    tags=["admin"])
