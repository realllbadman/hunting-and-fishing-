from typing import Optional, List

from pydantic import BaseModel


class OrderItem(BaseModel):
    product_id: str
    name: str
    model_number: Optional[str] = None
    unit_price: float
    quantity: int


class OrderCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: str
    company: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    freight_region: Optional[str] = None
    contact_pref: Optional[str] = None
    best_time: Optional[str] = None
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    items: List[OrderItem]
    total: float


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class BookingCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: str
    service: Optional[str] = "General Inquiry"
    product_interest: Optional[str] = None
    details: Optional[str] = None


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
