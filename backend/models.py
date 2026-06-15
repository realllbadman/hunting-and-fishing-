from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, Text, DateTime

from backend.database import Base


class Product(Base):
    __tablename__ = "products"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    slug           = Column(Text, unique=True, nullable=False)
    name           = Column(Text, nullable=False)
    brand          = Column(Text, nullable=False)
    category       = Column(Text, nullable=False)
    subcategory    = Column(Text, nullable=True)
    model_number   = Column(Text, nullable=True)
    price          = Column(Float, nullable=False)   # low end of the range / list price
    price_max      = Column(Float, nullable=True)     # high end of the range (optional)
    original_price = Column(Float, nullable=True)
    description    = Column(Text, nullable=True)
    features       = Column(Text, nullable=True)   # JSON list of strings
    in_stock       = Column(Integer, default=1)    # 1=in stock, 0=out of stock
    badge          = Column(Text, nullable=True)   # "Best Seller","New","Sale","Hot Deal"
    image          = Column(Text, nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    first_name     = Column(Text, nullable=False)
    last_name      = Column(Text, nullable=False)
    phone          = Column(Text, nullable=False)
    email          = Column(Text, nullable=False)
    company        = Column(Text, nullable=True)
    address        = Column(Text, nullable=True)
    city           = Column(Text, nullable=True)
    state          = Column(Text, nullable=True)
    zip            = Column(Text, nullable=True)
    country        = Column(Text, nullable=True)
    freight_region = Column(Text, nullable=True)
    contact_pref   = Column(Text, nullable=True)
    best_time      = Column(Text, nullable=True)
    notes          = Column(Text, nullable=True)
    payment_method = Column(Text, nullable=True)    # Bank Transfer / Zelle / PayPal / Other: ...
    items          = Column(Text, nullable=False)   # JSON list of OrderItem dicts
    total          = Column(Float, nullable=False)
    status         = Column(Text, default="pending")
    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Booking(Base):
    __tablename__ = "bookings"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    first_name       = Column(Text, nullable=False)
    last_name        = Column(Text, nullable=False)
    phone            = Column(Text, nullable=False)
    email            = Column(Text, nullable=False)
    service          = Column(Text, default="General Inquiry")
    product_interest = Column(Text, nullable=True)
    details          = Column(Text, nullable=True)
    status           = Column(Text, default="pending")
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes            = Column(Text, nullable=True)
