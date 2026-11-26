from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Booking, ChatMessage, Property, Transaction, User


PROPERTIES = [
    ("Pinetree Boutique Hotel", "Kilimani, Nairobi", "Boutique stay near Nairobi Garage", "Hotel", 14500.0, "ChIJdemo-pinetree", 4.7),
    ("Maasai Oasis Camp", "Kitengela, Kajiado", "Tented camp with cultural experiences", "Camp", 9800.0, "ChIJdemo-maasai", 4.8),
    ("Lakefront Homestay", "Kisumu", "Community-run homestay by Lake Victoria", "Homestay", 6200.0, "ChIJdemo-lakefront", 4.5),
    ("Swahili Coast Guest House", "Mombasa", "Swahili-style guest house near the old town", "Guest House", 11200.0, "ChIJdemo-swahili", 4.6),
    ("Rift Valley View Lodge", "Nakuru", "Lodge overlooking Lake Nakuru", "Lodge", 8700.0, "ChIJdemo-rift", 4.4),
]

USERS = [
    ("+254712345678", "WA", "Amina Yusuf", "sw"),
    ("+254733456789", "IG", "Brian Kamau", "en"),
    ("+254720111222", "SMS", "Grace Wanjiku", "en"),
    ("+254798765432", "WA", "David Ochieng", "en"),
]


def seed_demo_data() -> None:
    db: Session = SessionLocal()
    try:
        if db.query(User).count() > 0 or db.query(Property).count() > 0:
            return

        properties = []
        for name, location, description, category, price, place_id, rating in PROPERTIES:
            new_property = Property(
                name=name,
                location=location,
                description=description,
                category=category,
                price_per_night=price,
                google_place_id=place_id,
                rating=rating,
            )
            db.add(new_property)
            properties.append(new_property)
        db.flush()

        users = [User(phone_number=p, platform=pl, display_name=n, preferred_language=lang) for p, pl, n, lang in USERS]
        db.add_all(users)
        db.flush()

        today = date.today()
        bookings = [
            Booking(user_id=users[0].id, property_id=properties[0].id, check_in=today.isoformat(), check_out=str(today + timedelta(days=2)), guests=2, status="Paid", total_amount=29000.0),
            Booking(user_id=users[0].id, property_id=properties[0].id, check_in=str(today + timedelta(days=3)), check_out=str(today + timedelta(days=5)), guests=2, status="Paid", total_amount=29000.0),
            Booking(user_id=users[1].id, property_id=properties[1].id, check_in=str(today + timedelta(days=7)), check_out=str(today + timedelta(days=9)), guests=4, status="Paid", total_amount=19600.0),
            Booking(user_id=users[2].id, property_id=properties[2].id, check_in=str(today + timedelta(days=1)), check_out=str(today + timedelta(days=2)), guests=2, status="Pending", total_amount=6200.0),
            Booking(user_id=users[3].id, property_id=properties[3].id, check_in=str(today + timedelta(days=12)), check_out=str(today + timedelta(days=15)), guests=3, status="Paid", total_amount=33600.0),
            Booking(user_id=users[0].id, property_id=properties[4].id, check_in=str(today + timedelta(days=20)), check_out=str(today + timedelta(days=22)), guests=2, status="Cancelled", total_amount=17400.0),
            Booking(user_id=users[1].id, property_id=properties[0].id, check_in=str(today + timedelta(days=2)), check_out=str(today + timedelta(days=4)), guests=2, status="Paid", total_amount=29000.0),
        ]
        db.add_all(bookings)
        db.flush()

        for index, booking in enumerate([b for b in bookings if b.status == "Paid"]):
            db.add(
                Transaction(
                    booking_id=booking.id,
                    mpesa_receipt_number=f"DEMO{index + 1}7RT61SV",
                    merchant_request_id=f"DEMO-MERCHANT-{index + 1}",
                    checkout_request_id=f"DEMO_CHECKOUT_{index + 1}",
                    amount=booking.total_amount,
                    status="Success",
                    result_description="The service request is processed successfully.",
                    phone_number=users[index % len(users)].phone_number,
                    created_at=datetime.now() - timedelta(days=6 - index),
                )
            )

        conversations = [
            (users[0], "in", "Habari! Ninataka ku-book hoteli hii", "booking"),
            (users[0], "out", "Karibu! Ninaweza kukusaidia ku-book. Unataka kukaa tarehe gani?", "booking"),
            (users[1], "in", "Any places near Lake Nakuru?", "recommendation"),
            (users[1], "out", "Rift Valley View Lodge is a great choice near Lake Nakuru.", "recommendation"),
            (users[2], "in", "I need a homestay in Kisumu for 2 nights", "booking"),
            (users[2], "out", "I found Lakefront Homestay at KES 6,200/night. Shall I send an M-Pesa prompt?", "booking"),
            (users[3], "in", "How much is deposit?", "faq"),
            (users[3], "out", "A 50% deposit is required to confirm your booking.", "faq"),
        ]
        for user, direction, content, intent in conversations:
            db.add(
                ChatMessage(
                    user_id=user.id,
                    platform=user.platform,
                    direction=direction,
                    content=content,
                    intent=intent,
                    created_at=datetime.now() - timedelta(minutes=len(conversations) * 5),
                )
            )

        db.commit()
    finally:
        db.close()
