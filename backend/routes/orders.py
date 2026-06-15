"""Orders API. No online payment — owner is notified to contact the customer."""
import json

from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Order
from backend.schemas import OrderCreate
from backend.services import email

router = APIRouter()

FREIGHT_MAP = {
    "Canada/Mexico": 800,
    "Caribbean/Central America": 900,
    "South America": 1000,
    "Europe": 1200,
    "Middle East/North Africa": 1100,
    "Sub-Saharan Africa": 1300,
    "Asia Pacific": 1400,
    "Australia/New Zealand": 1500,
    "Other": 1600,
}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    items_dicts = [item.model_dump() for item in order_in.items]
    subtotal = sum(i["unit_price"] * i["quantity"] for i in items_dicts)

    # Domestic: free over $2,000, else flat $500. International: freight map.
    shipping = 0.0 if subtotal >= 2000 else 500.0
    if order_in.freight_region and order_in.freight_region != "Domestic (USA)":
        shipping = float(FREIGHT_MAP.get(order_in.freight_region, 1600))

    grand_total = subtotal + shipping

    order = Order(
        first_name=order_in.first_name,
        last_name=order_in.last_name,
        phone=order_in.phone,
        email=order_in.email,
        company=order_in.company,
        address=order_in.address,
        city=order_in.city,
        state=order_in.state,
        zip=order_in.zip,
        country=order_in.country,
        freight_region=order_in.freight_region,
        contact_pref=order_in.contact_pref,
        best_time=order_in.best_time,
        notes=order_in.notes,
        payment_method=order_in.payment_method,
        items=json.dumps(items_dicts),
        total=grand_total,
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    customer = {
        "first_name": order_in.first_name,
        "last_name": order_in.last_name,
        "phone": order_in.phone,
        "email": order_in.email,
        "company": order_in.company,
        "address": order_in.address,
        "city": order_in.city,
        "state": order_in.state,
        "zip": order_in.zip,
        "country": order_in.country,
        "freight_region": order_in.freight_region,
        "contact_pref": order_in.contact_pref,
        "best_time": order_in.best_time,
        "notes": order_in.notes,
        "payment_method": order_in.payment_method,
    }
    background_tasks.add_task(
        email.send_order_customer_confirmation, customer, items_dicts, grand_total, shipping
    )
    background_tasks.add_task(
        email.send_order_owner_notification, customer, items_dicts, grand_total, shipping
    )

    return {"message": "Order received", "id": order.id}
