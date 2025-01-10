from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import random
import os

# Create the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import models first
from models import db, User, AdminUser, Hotel, Room, Booking, Currency

# Initialize the app with SQLAlchemy
db.init_app(app)

def init_db():
    # Drop all tables
    db.drop_all()
    
    # Create all tables
    db.create_all()
    
    # Create admin user
    admin = AdminUser(
        email='admin@example.com',
        is_admin=True
    )
    admin.set_password('admin123')
    db.session.add(admin)
    
    # Create test user
    user = User(
        email='test@example.com',
        name='Test User',
        phone='1234567890'
    )
    user.set_password('test123')
    db.session.add(user)
    
    # Create hotels
    hotels_data = [
        {
            'name': 'Grand Hotel London',
            'city': 'London',
            'address': '123 Oxford Street, London',
            'description': 'Luxury hotel in the heart of London',
            'rating': 4.5
        },
        {
            'name': 'Manchester Plaza',
            'city': 'Manchester',
            'address': '456 Main St, Manchester',
            'description': 'Modern hotel with excellent amenities',
            'rating': 4.2
        }
    ]
    
    hotels = []
    for hotel_data in hotels_data:
        hotel = Hotel(**hotel_data)
        db.session.add(hotel)
        hotels.append(hotel)
    
    # Commit to get hotel IDs
    db.session.commit()
    
    # Create rooms
    room_types = ['standard', 'double', 'family']
    room_prices = {'standard': 100, 'double': 150, 'family': 200}
    room_capacities = {'standard': 2, 'double': 3, 'family': 4}
    
    for hotel in hotels:
        for room_type in room_types:
            for _ in range(3):  # 3 rooms of each type per hotel
                base_price = room_prices[room_type]
                peak_price = base_price * 1.5
                room = Room(
                    hotel_id=hotel.id,
                    type=room_type,
                    description=f'Comfortable {room_type} room',
                    base_price=base_price,
                    price=base_price,
                    peak_price=peak_price,
                    capacity=room_capacities[room_type],
                    amenities=['WiFi', 'TV', 'Air Conditioning'],
                    available=True
                )
                db.session.add(room)
    
    # Commit to get room IDs
    db.session.commit()
    
    # Create some sample bookings
    now = datetime.utcnow()
    rooms = Room.query.all()
    
    # Past bookings
    for i in range(3):
        check_in = now - timedelta(days=30+i)
        check_out = check_in + timedelta(days=3)
        room = random.choice(rooms)
        total_price = room.base_price * 3
        
        booking = Booking(
            user_id=user.id,
            hotel_id=room.hotel_id,
            room_id=room.id,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            total_price=total_price,
            status='confirmed',
            payment_status='paid',
            payment_method='card',
            booking_date=check_in - timedelta(days=5),
            advance_booking_discount=0.1
        )
        db.session.add(booking)
    
    # Future bookings
    for i in range(3):
        check_in = now + timedelta(days=15+i)
        check_out = check_in + timedelta(days=2)
        room = random.choice(rooms)
        total_price = room.base_price * 2
        
        booking = Booking(
            user_id=user.id,
            hotel_id=room.hotel_id,
            room_id=room.id,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            total_price=total_price,
            status='confirmed',
            payment_status='paid',
            payment_method='paypal',
            booking_date=now - timedelta(days=2),
            advance_booking_discount=0.15
        )
        db.session.add(booking)
    
    # Add currencies
    currencies = [
        {'code': 'GBP', 'name': 'British Pound', 'exchange_rate': 1.0},
        {'code': 'EUR', 'name': 'Euro', 'exchange_rate': 1.16},
        {'code': 'USD', 'name': 'US Dollar', 'exchange_rate': 1.27}
    ]
    
    for currency_data in currencies:
        currency = Currency(**currency_data)
        db.session.add(currency)
    
    # Commit all changes
    db.session.commit()
    print("Database initialized successfully!")

if __name__ == '__main__':
    with app.app_context():
        init_db()
