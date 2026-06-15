"""Bookings (quote / inquiry) API."""
from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking
from backend.schemas import BookingCreate
from backend.services import email

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    booking = Booking(
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=payload.email,
        service=payload.service or "General Inquiry",
        product_interest=payload.product_interest,
        details=payload.details,
        status="pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    data = {
        "first_name": booking.first_name,
        "last_name": booking.last_name,
        "phone": booking.phone,
        "email": booking.email,
        "service": booking.service,
        "product_interest": booking.product_interest,
        "details": booking.details,
    }
    background_tasks.add_task(email.send_customer_confirmation, data)
    background_tasks.add_task(email.send_owner_notification, data)

    return {"message": "Inquiry received", "id": booking.id}
