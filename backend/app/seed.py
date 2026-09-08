"""Seed a demo customer/order into the simulator's system of record.

Run with: python -m app.seed
"""

from app.database import Base, SessionLocal, engine
from app.models import Customer, Order


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.get(Customer, "C-891") is None:
            db.add(Customer(id="C-891", name="Jordan Rivera", email="jordan.rivera@example.com"))
        if db.get(Order, "ORD-1047") is None:
            db.add(Order(id="ORD-1047", customer_id="C-891", amount_minor_units=18500, currency="EUR"))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seeded demo customer C-891 and order ORD-1047.")
