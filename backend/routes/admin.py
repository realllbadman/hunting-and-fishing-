"""Admin API — HTTP Basic auth over orders and bookings."""
import os
import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Order, Booking
from backend.schemas import OrderUpdate, BookingUpdate

router = APIRouter()
security = HTTPBasic()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme123")


def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    ok_u = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    ok_p = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (ok_u and ok_p):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _order_dict(o: Order) -> dict:
    try:
        items = json.loads(o.items) if o.items else []
    except (ValueError, TypeError):
        items = []
    return {
        "id": o.id, "first_name": o.first_name, "last_name": o.last_name,
        "phone": o.phone, "email": o.email, "company": o.company,
        "address": o.address, "city": o.city, "state": o.state, "zip": o.zip,
        "country": o.country, "freight_region": o.freight_region,
        "contact_pref": o.contact_pref, "best_time": o.best_time,
        "notes": o.notes, "payment_method": o.payment_method,
        "items": items, "total": o.total,
        "status": o.status,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


def _booking_dict(b: Booking) -> dict:
    return {
        "id": b.id, "first_name": b.first_name, "last_name": b.last_name,
        "phone": b.phone, "email": b.email, "service": b.service,
        "product_interest": b.product_interest, "details": b.details,
        "status": b.status, "notes": b.notes,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


# ─────────────────────────────── Stats ────────────────────────────────

@router.get("/stats")
def stats(_: str = Depends(require_auth), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    orders = db.query(Order).all()
    orders_this_month = sum(
        1 for o in orders
        if o.created_at and o.created_at.year == now.year and o.created_at.month == now.month
    )
    return {
        "orders": len(orders),
        "pending_orders": sum(1 for o in orders if o.status == "pending"),
        "bookings": db.query(Booking).count(),
        "pending_bookings": db.query(Booking).filter(Booking.status == "pending").count(),
        "orders_this_month": orders_this_month,
        "revenue": sum(o.total or 0 for o in orders),
    }


# ─────────────────────────────── Orders ───────────────────────────────

@router.get("/orders")
def list_orders(_: str = Depends(require_auth), db: Session = Depends(get_db)):
    rows = db.query(Order).order_by(Order.created_at.desc()).all()
    return [_order_dict(o) for o in rows]


@router.get("/orders/{order_id}")
def get_order(order_id: int, _: str = Depends(require_auth), db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_dict(o)


@router.patch("/orders/{order_id}")
def update_order(order_id: int, payload: OrderUpdate,
                 _: str = Depends(require_auth), db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if payload.status is not None:
        o.status = payload.status
    if payload.notes is not None:
        o.notes = payload.notes
    db.commit()
    db.refresh(o)
    return _order_dict(o)


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, _: str = Depends(require_auth), db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(o)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ────────────────────────────── Bookings ──────────────────────────────

@router.get("/bookings")
def list_bookings(_: str = Depends(require_auth), db: Session = Depends(get_db)):
    rows = db.query(Booking).order_by(Booking.created_at.desc()).all()
    return [_booking_dict(b) for b in rows]


@router.get("/bookings/{booking_id}")
def get_booking(booking_id: int, _: str = Depends(require_auth), db: Session = Depends(get_db)):
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _booking_dict(b)


@router.patch("/bookings/{booking_id}")
def update_booking(booking_id: int, payload: BookingUpdate,
                   _: str = Depends(require_auth), db: Session = Depends(get_db)):
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if payload.status is not None:
        b.status = payload.status
    if payload.notes is not None:
        b.notes = payload.notes
    db.commit()
    db.refresh(b)
    return _booking_dict(b)


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(booking_id: int, _: str = Depends(require_auth), db: Session = Depends(get_db)):
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(b)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
