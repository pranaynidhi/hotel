from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import enum
import uuid
from sqlalchemy import extract

db = SQLAlchemy()

class RoomType(enum.Enum):
    STANDARD = "standard"
    DOUBLE = "double"
    FAMILY = "family"

class BookingStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    bookings = db.relationship('Booking', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Float, default=0.0)
    rooms = db.relationship('Room', backref='hotel', lazy=True)
    bookings = db.relationship('Booking', backref='hotel', lazy=True)

    def get_image_url(self):
        # Convert hotel name to a search-friendly format
        search_term = self.name.lower().replace(' ', '-')
        # Use the hotel name and city for more relevant images
        return f"https://source.unsplash.com/800x600/?hotel,{search_term},{self.city}"

    @property
    def available_rooms_count(self):
        return len([room for room in self.rooms if room.available])
    
    @property
    def available_room_types(self):
        return list(set(room.type for room in self.rooms if room.available))

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Current calculated price
    peak_price = db.Column(db.Float)
    capacity = db.Column(db.Integer, default=2)
    amenities = db.Column(db.JSON)
    images = db.Column(db.JSON)
    available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='room', lazy=True)

    def calculate_price(self, check_in, check_out):
        """Calculate total price for the room booking."""
        try:
            if isinstance(check_in, str):
                check_in = datetime.strptime(check_in, '%Y-%m-%d').date()
            if isinstance(check_out, str):
                check_out = datetime.strptime(check_out, '%Y-%m-%d').date()
            
            # Calculate number of nights
            nights = (check_out - check_in).days
            if nights <= 0:
                return None
            
            # Check if dates are in peak season
            is_peak = check_in.month in [4, 5, 6, 7, 8, 11, 12]
            
            # Use peak price during peak season if available
            daily_rate = self.peak_price if (is_peak and self.peak_price) else self.base_price
            
            return daily_rate * nights
        except Exception as e:
            print(f"Error calculating price: {str(e)}")
            return None

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    check_in = db.Column(db.DateTime, nullable=False)
    check_out = db.Column(db.DateTime, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(20))
    booking_date = db.Column(db.DateTime)
    advance_booking_discount = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Booking, self).__init__(**kwargs)
        if not self.booking_id:
            self.booking_id = str(uuid.uuid4())

class SalesReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    month = db.Column(db.Date, nullable=False)
    total_sales = db.Column(db.Float, default=0.0)
    total_bookings = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    profit = db.Column(db.Float, default=0.0)

    @classmethod
    def generate_monthly_report(cls, hotel_id, month):
        # Get all bookings for the hotel in the given month
        bookings = Booking.query.join(Room).filter(
            Room.hotel_id == hotel_id,
            extract('month', Booking.check_in) == month.month,
            extract('year', Booking.check_in) == month.year
        ).all()
        
        total_sales = sum(booking.total_price for booking in bookings)
        total_bookings = len(bookings)
        
        # Calculate average rating from reviews
        hotel = Hotel.query.get(hotel_id)
        average_rating = hotel.rating
        
        # Assume 30% of sales is profit (simplified)
        profit = total_sales * 0.3
        
        report = cls(
            hotel_id=hotel_id,
            month=month,
            total_sales=total_sales,
            total_bookings=total_bookings,
            average_rating=average_rating,
            profit=profit
        )
        db.session.add(report)
        db.session.commit()
        return report

class Currency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    exchange_rate = db.Column(db.Float, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def update_rate(self, new_rate):
        self.exchange_rate = new_rate
        self.last_updated = datetime.utcnow()
        db.session.commit()

def is_peak_season(date):
    """Check if a given date falls in peak season (April-August and November-December)"""
    month = date.month
    return month in [4, 5, 6, 7, 8, 11, 12]
