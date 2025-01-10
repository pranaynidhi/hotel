from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps, lru_cache
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, DateField, SelectField, IntegerField, TextAreaField, FloatField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional
import json
import os
import requests
from itertools import groupby
import uuid
import enum
from sqlalchemy import extract, create_engine, text
from flask_migrate import Migrate
from dotenv import load_dotenv
import pymysql
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure MySQL connection
from urllib.parse import quote_plus
password = quote_plus(os.getenv('MYSQL_PASSWORD'))

# Create database URL without database name
base_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{password}@{os.getenv('MYSQL_HOST')}"
database_name = os.getenv('MYSQL_DATABASE')

# Create engine without database selected
engine = create_engine(base_url)

# Create database if it doesn't exist
with engine.connect() as conn:
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {database_name}"))
    conn.execute(text(f"USE {database_name}"))

# Now configure Flask-SQLAlchemy with the full database URL
app.config['SQLALCHEMY_DATABASE_URI'] = f"{base_url}/{database_name}?charset=utf8mb4"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Enums
class RoomType(enum.Enum):
    STANDARD = "standard"
    DOUBLE = "double"
    FAMILY = "family"

class BookingStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class SearchForm(FlaskForm):
    city = SelectField('City', choices=[
        ('', 'Select a City'),
        ('Aberdeen', 'Aberdeen'),
        ('Belfast', 'Belfast'),
        ('Birmingham', 'Birmingham'),
        ('Bristol', 'Bristol'),
        ('Cardiff', 'Cardiff'),
        ('Edinburgh', 'Edinburgh'),
        ('Glasgow', 'Glasgow'),
        ('London', 'London'),
        ('Manchester', 'Manchester'),
        ('New Castle', 'New Castle'),
        ('Norwich', 'Norwich'),
        ('Nottingham', 'Nottingham'),
        ('Oxford', 'Oxford'),
        ('Plymouth', 'Plymouth'),
        ('Swansea', 'Swansea'),
        ('Bournemouth', 'Bournemouth'),
        ('Kent', 'Kent')
    ], validators=[DataRequired()])
    check_in = DateField('Check-in Date', validators=[DataRequired()])
    check_out = DateField('Check-out Date', validators=[DataRequired()])
    room_type = SelectField('Room Type', choices=[
        ('any', 'Any Type'),
        ('standard', 'Standard Room'),
        ('double', 'Double Room'),
        ('family', 'Family Room')
    ])
    rooms = IntegerField('Number of Rooms', default=1, validators=[
        NumberRange(min=1, max=5, message="Please select between 1 and 5 rooms")
    ])
    currency = SelectField('Currency', choices=[
        ('GBP', 'British Pound (£)'),
        ('EUR', 'Euro (€)'),
        ('USD', 'US Dollar ($)')
    ], default='GBP')

class AdminLoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class HotelForm(FlaskForm):
    name = StringField('Hotel Name', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    rating = FloatField('Rating', validators=[NumberRange(min=0, max=5)])
    submit = SubmitField('Submit')

class RoomForm(FlaskForm):
    type = SelectField('Room Type', choices=[('standard', 'Standard'), ('double', 'Double'), ('family', 'Family')])
    description = TextAreaField('Description')
    base_price = FloatField('Base Price', validators=[DataRequired(), NumberRange(min=0)])
    max_guests = IntegerField('Max Guests', validators=[DataRequired(), NumberRange(min=1)])
    available = BooleanField('Available')
    submit = SubmitField('Submit')

class CurrencyForm(FlaskForm):
    code = StringField('Currency Code', validators=[DataRequired(), Length(min=3, max=3)])
    name = StringField('Currency Name', validators=[DataRequired()])
    exchange_rate = FloatField('Exchange Rate (to GBP)', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Submit')

class BookingForm(FlaskForm):
    check_in = DateField('Check-in Date', validators=[DataRequired()])
    check_out = DateField('Check-out Date', validators=[DataRequired()])
    room_type = SelectField('Room Type', choices=[
        ('standard', 'Standard Room'),
        ('double', 'Double Room'),
        ('family', 'Family Room')
    ], validators=[DataRequired()])
    num_guests = IntegerField('Number of Guests', validators=[
        DataRequired(),
        NumberRange(min=1, max=4, message="Please enter between 1 and 4 guests")
    ])
    submit = SubmitField('Book Now')

class PaymentForm(FlaskForm):
    payment_method = SelectField('Payment Method', 
        choices=[
            ('card', 'Credit/Debit Card'),
            ('paypal', 'PayPal'),
            ('googlepay', 'Google Pay')
        ],
        validators=[DataRequired()]
    )
    
    # Card Details
    card_holder = StringField('Card Holder Name', 
        validators=[Optional(), Length(min=2, max=100)])
    card_number = StringField('Card Number', 
        validators=[Optional(), Length(min=16, max=16)])
    expiry_month = SelectField('Expiry Month',
        choices=[(str(i), str(i).zfill(2)) for i in range(1, 13)],
        validators=[Optional()])
    expiry_year = SelectField('Expiry Year',
        choices=[(str(i), str(i)) for i in range(2024, 2035)],
        validators=[Optional()])
    cvv = StringField('CVV', validators=[Optional(), Length(min=3, max=4)])
    
    # PayPal
    paypal_email = StringField('PayPal Email',
        validators=[Optional(), Email()])
    
    # Google Pay
    google_account = StringField('Google Account Email',
        validators=[Optional(), Email()])
    
    confirm_payment = BooleanField('I confirm that I want to proceed with the payment',
        validators=[DataRequired()])
    
    submit = SubmitField('Confirm Payment')

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    bookings = db.relationship('Booking', backref='user', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Hotel(db.Model):
    __tablename__ = 'hotels'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Float, default=0.0)
    amenities = db.Column(db.JSON)
    images = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    rooms = db.relationship('Room', backref='hotel', lazy=True)
    bookings = db.relationship('Booking', backref='hotel', lazy=True)

class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    peak_price = db.Column(db.Float)
    capacity = db.Column(db.Integer, default=2)
    amenities = db.Column(db.JSON)
    images = db.Column(db.JSON)
    available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='room', lazy=True)

    def calculate_price(self, check_in, check_out):
        if isinstance(check_in, str):
            check_in = datetime.strptime(check_in, '%Y-%m-%d').date()
        if isinstance(check_out, str):
            check_out = datetime.strptime(check_out, '%Y-%m-%d').date()
        
        nights = (check_out - check_in).days
        if nights <= 0:
            return None
        
        total_price = 0
        current_date = check_in
        
        while current_date < check_out:
            is_weekend = current_date.weekday() >= 5
            is_peak = current_date.month in [4, 5, 6, 7, 8, 11, 12]
            
            if is_peak:
                day_price = self.peak_price or (self.base_price * 1.3)
            else:
                day_price = self.base_price
            
            if is_weekend:
                day_price *= 1.2
            
            total_price += day_price
            current_date += timedelta(days=1)
        
        return total_price

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    check_in = db.Column(db.DateTime, nullable=False)
    check_out = db.Column(db.DateTime, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(20))
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    advance_booking_discount = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Booking, self).__init__(**kwargs)
        if not self.booking_id:
            self.booking_id = str(uuid.uuid4())

class SalesReport(db.Model):
    __tablename__ = 'sales_reports'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    month = db.Column(db.Date, nullable=False)
    total_sales = db.Column(db.Float, default=0.0)
    total_bookings = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    profit = db.Column(db.Float, default=0.0)

    @classmethod
    def generate_monthly_report(cls, hotel_id, month):
        bookings = Booking.query.filter(
            Booking.hotel_id == hotel_id,
            extract('year', Booking.created_at) == month.year,
            extract('month', Booking.created_at) == month.month,
            Booking.status == 'confirmed'
        ).all()

        total_sales = sum(b.total_price for b in bookings)
        total_bookings = len(bookings)
        profit = total_sales * 0.2  # Assuming 20% profit margin

        report = cls(
            hotel_id=hotel_id,
            month=month,
            total_sales=total_sales,
            total_bookings=total_bookings,
            profit=profit
        )
        return report

class Currency(db.Model):
    __tablename__ = 'currencies'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    exchange_rate = db.Column(db.Float, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def update_rate(self, new_rate):
        self.exchange_rate = new_rate
        self.last_updated = datetime.utcnow()

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user:
        return user
    return None

def is_peak_season(date):
    """
    Check if a given date falls in peak season.
    Peak season is April-August and November-December
    """
    month = date.month
    return month in [4, 5, 6, 7, 8, 11, 12]

def calculate_price(room, check_in, check_out):
    """
    Calculate the total price for a room booking based on season
    """
    try:
        if not room or not check_in or not check_out:
            return None

        # Convert dates to datetime if they're date objects
        if isinstance(check_in, datetime.date):
            check_in = datetime.combine(check_in, datetime.min.time())
        if isinstance(check_out, datetime.date):
            check_out = datetime.combine(check_out, datetime.min.time())

        return room.calculate_price(check_in, check_out)

    except Exception as e:
        app.logger.error(f"Error calculating price: {str(e)}")
        return None

@lru_cache(maxsize=1)
def get_exchange_rates():
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/GBP')
        return response.json()['rates']
    except:
        # Fallback rates if API fails
        return {
            'GBP': 1.0,
            'EUR': 1.16,
            'USD': 1.27
        }

def convert_currency(amount, from_currency='GBP', to_currency='GBP'):
    if amount is None:
        return None
    
    rates = get_exchange_rates()
    if from_currency == to_currency:
        return amount
    
    # Convert to GBP first if not already in GBP
    if from_currency != 'GBP':
        amount = amount / rates[from_currency]
    
    # Convert from GBP to target currency
    return amount * rates[to_currency]

@app.template_filter('unique')
def unique_filter(items, attribute=None):
    if attribute:
        key = lambda x: getattr(x, attribute)
        return [next(g) for k, g in groupby(sorted(items, key=key), key=key)]
    return list(set(items))

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be logged in as an admin to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    form = SearchForm()
    hotels = []
    
    if request.method == 'POST':
        try:
            # Get search parameters
            city = request.form.get('city')
            check_in_str = request.form.get('check_in')
            check_out_str = request.form.get('check_out')
            room_type = request.form.get('room_type', 'any')
            rooms_needed = int(request.form.get('rooms', 1))
            selected_currency = request.form.get('currency', 'GBP')
            
            # Convert dates
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date() if check_in_str else None
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date() if check_out_str else None
            
            app.logger.info(f"Search parameters - City: {city}, Check-in: {check_in}, Check-out: {check_out}, "
                          f"Room type: {room_type}, Rooms needed: {rooms_needed}")
            
            # Store search parameters in session
            session['check_in'] = check_in_str
            session['check_out'] = check_out_str
            
            # Filter hotels by city if provided
            if city:
                hotels = Hotel.query.filter(Hotel.city == city).all()
                app.logger.info(f"Found {len(hotels)} hotels in {city}")
            else:
                hotels = Hotel.query.all()
                app.logger.info(f"No city specified. Found {len(hotels)} total hotels")
            
            if not hotels:
                flash('No hotels found in the selected city', 'info')
                return render_template('index.html', form=form, hotels=[])
            
            # Filter hotels based on room availability
            if check_in and check_out and rooms_needed:
                available_hotels = []
                for hotel in hotels:
                    rooms_query = Room.query.filter_by(hotel_id=hotel.id, available=True)
                    
                    if room_type != 'any':
                        rooms_query = rooms_query.filter_by(type=room_type)
                    
                    available_rooms = rooms_query.all()
                    app.logger.info(f"Hotel {hotel.name} has {len(available_rooms)} available rooms")
                    
                    # Check if hotel has enough rooms
                    if len(available_rooms) >= rooms_needed:
                        # Calculate minimum price for available rooms
                        room_prices = []
                        for room in available_rooms:
                            base_price = room.base_price
                            if is_peak_season(check_in):
                                price = room.peak_price
                            else:
                                price = base_price
                            room_prices.append(price)
                        
                        if room_prices:
                            min_price = min(room_prices)
                            if selected_currency != 'GBP':
                                min_price = convert_currency(min_price, 'GBP', selected_currency)
                            hotel.min_price = min_price
                            available_hotels.append(hotel)
                            app.logger.info(f"Added hotel {hotel.name} to available hotels. Min price: {min_price}")
                
                hotels = available_hotels
                app.logger.info(f"Final number of available hotels: {len(hotels)}")
                
                if not hotels:
                    flash('No hotels found with available rooms matching your criteria', 'info')
            
        except Exception as e:
            app.logger.error(f"Error in search: {str(e)}")
            flash('An error occurred while searching for hotels. Please try again.', 'error')
            hotels = []
    else:
        # For GET request, show featured hotels
        try:
            hotels = Hotel.query.limit(6).all()
            app.logger.info(f"Loaded {len(hotels)} featured hotels")
        except Exception as e:
            app.logger.error(f"Error loading featured hotels: {str(e)}")
            flash('Error loading featured hotels', 'error')
            hotels = []
    
    # Add debug information
    app.logger.info(f"Rendering template with {len(hotels)} hotels")
    for hotel in hotels:
        app.logger.info(f"Hotel: {hotel.name}, City: {hotel.city}")
    
    return render_template('index.html', form=form, hotels=hotels)

@app.route('/hotel/<int:hotel_id>')
def hotel_details(hotel_id):
    try:
        hotel = Hotel.query.get_or_404(hotel_id)
        app.logger.info(f"Loading details for hotel {hotel_id}: {hotel.name}")
        
        # Get available rooms
        available_rooms = Room.query.filter_by(
            hotel_id=hotel_id,
            available=True
        ).all()
        
        app.logger.info(f"Found {len(available_rooms)} available rooms for hotel {hotel_id}")
        
        # Get room prices
        for room in available_rooms:
            try:
                # Use today and tomorrow as default dates if not in session
                check_in = session.get('check_in', datetime.now().date())
                check_out = session.get('check_out', (datetime.now() + timedelta(days=1)).date())
                
                if isinstance(check_in, str):
                    check_in = datetime.strptime(check_in, '%Y-%m-%d').date()
                if isinstance(check_out, str):
                    check_out = datetime.strptime(check_out, '%Y-%m-%d').date()
                
                calculated_price = room.calculate_price(check_in, check_out)
                room.price = calculated_price if calculated_price is not None else room.base_price
                app.logger.info(f"Calculated price for room {room.id}: {room.price}")
            except Exception as e:
                app.logger.error(f"Error calculating price for room {room.id}: {str(e)}")
                room.price = room.base_price  # Fallback to base price
        
        return render_template('hotel_details.html', 
                             hotel=hotel, 
                             available_rooms=available_rooms)
    
    except Exception as e:
        app.logger.error(f"Error loading hotel details for hotel {hotel_id}: {str(e)}")
        flash('Error loading hotel details', 'error')
        return redirect(url_for('index'))

@app.route('/booking/<int:hotel_id>/<int:room_id>', methods=['GET', 'POST'])
@login_required
def booking(hotel_id, room_id):
    try:
        hotel = Hotel.query.get_or_404(hotel_id)
        room = Room.query.get_or_404(room_id)
        
        # Check if room is available
        if not room.available:
            flash('This room is not available for booking', 'error')
            return redirect(url_for('hotel_details', hotel_id=hotel_id))
        
        form = BookingForm()
        
        # Pre-fill room type
        form.room_type.data = room.type
        
        # Get check-in/check-out dates from session
        if 'check_in' in session and 'check_out' in session:
            try:
                form.check_in.data = datetime.strptime(session['check_in'], '%Y-%m-%d').date()
                form.check_out.data = datetime.strptime(session['check_out'], '%Y-%m-%d').date()
            except ValueError:
                form.check_in.data = datetime.now().date()
                form.check_out.data = (datetime.now() + timedelta(days=1)).date()
        
        if form.validate_on_submit():
            try:
                check_in = form.check_in.data
                check_out = form.check_out.data
                num_guests = form.num_guests.data
                
                # Validate dates
                if check_in >= check_out:
                    flash('Check-out date must be after check-in date', 'error')
                    return render_template('booking.html', form=form, hotel=hotel, room=room)
                
                if check_in < datetime.now().date():
                    flash('Check-in date cannot be in the past', 'error')
                    return render_template('booking.html', form=form, hotel=hotel, room=room)
                
                # Maximum booking duration is 30 days
                if (check_out - check_in).days > 30:
                    flash('Maximum booking duration is 30 days', 'error')
                    return render_template('booking.html', form=form, hotel=hotel, room=room)
                
                # Check if room is available for these dates
                existing_bookings = Booking.query.filter(
                    Booking.room_id == room_id,
                    Booking.status.in_(['confirmed', 'pending']),
                    Booking.payment_status != 'cancelled',
                    Booking.check_out > datetime.combine(check_in, datetime.min.time()),
                    Booking.check_in < datetime.combine(check_out, datetime.min.time())
                ).first()
                
                if existing_bookings:
                    flash('Room is not available for the selected dates', 'error')
                    return render_template('booking.html', form=form, hotel=hotel, room=room)
                
                # Validate guest count
                if num_guests > room.capacity:
                    flash(f'Maximum {room.capacity} guests allowed for this room type', 'error')
                    return render_template('booking.html', form=form, hotel=hotel, room=room)
                
                if num_guests < 1:
                    flash('Number of guests must be at least 1', 'error')
                    return render_template('booking.html', form=form, hotel=hotel, room=room)
                
                # Calculate total price
                total_price = room.calculate_price(check_in, check_out)
                if total_price is None:
                    flash('Error calculating room price', 'error')
                    return render_template('booking.html', form=form, hotel=hotel, room=room)
                
                # Apply advance booking discount
                days_until_checkin = (check_in - datetime.now().date()).days
                if days_until_checkin > 60:
                    discount = 0.15  # 15% discount
                elif days_until_checkin > 30:
                    discount = 0.10  # 10% discount
                else:
                    discount = 0
                
                discounted_price = total_price * (1 - discount)
                
                # Create booking
                booking = Booking(
                    user_id=current_user.id,
                    hotel_id=hotel_id,
                    room_id=room_id,
                    check_in=datetime.combine(check_in, datetime.min.time()),
                    check_out=datetime.combine(check_out, datetime.min.time()),
                    guests=num_guests,
                    total_price=discounted_price,
                    status='pending',
                    payment_status='pending',
                    advance_booking_discount=discount
                )
                
                db.session.add(booking)
                db.session.commit()
                
                # Store booking dates in session
                session['check_in'] = check_in.strftime('%Y-%m-%d')
                session['check_out'] = check_out.strftime('%Y-%m-%d')
                
                flash('Booking created successfully. Please complete the payment.', 'success')
                return redirect(url_for('payment', booking_id=booking.id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error processing booking: {str(e)}")
                flash('An error occurred while processing your booking. Please try again.', 'error')
                return render_template('booking.html', form=form, hotel=hotel, room=room)
        
        # For GET request or form validation failure
        min_date = datetime.now().date()
        max_date = min_date + timedelta(days=365)  # Allow booking up to 1 year in advance
        
        return render_template('booking.html',
                             form=form,
                             hotel=hotel,
                             room=room,
                             min_date=min_date.strftime('%Y-%m-%d'),
                             max_date=max_date.strftime('%Y-%m-%d'))
                             
    except Exception as e:
        app.logger.error(f"Error in booking route: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Verify booking belongs to current user
        if booking.user_id != current_user.id:
            flash('Unauthorized access', 'error')
            return redirect(url_for('index'))
            
        # Check if payment is already done
        if booking.payment_status == 'paid':
            flash('This booking is already paid', 'info')
            return redirect(url_for('booking_confirmation', booking_id=booking.id))
            
        # Check if booking is expired (created more than 30 minutes ago)
        if (datetime.utcnow() - booking.created_at).total_seconds() > 1800:  # 30 minutes
            booking.status = 'cancelled'
            booking.payment_status = 'cancelled'
            db.session.commit()
            flash('Booking expired. Please try again.', 'error')
            return redirect(url_for('hotel_details', hotel_id=booking.hotel_id))
        
        form = PaymentForm()
        
        if form.validate_on_submit():
            try:
                if not form.confirm_payment.data:
                    flash('Please confirm that you want to proceed with the payment', 'error')
                    return render_template('payment.html', form=form, booking=booking)
                
                payment_method = form.payment_method.data
                
                # Validate payment details based on method
                if payment_method == 'card':
                    # Validate card details
                    card_number = form.card_number.data.strip()
                    if not card_number.isdigit() or len(card_number) != 16:
                        flash('Invalid card number', 'error')
                        return render_template('payment.html', form=form, booking=booking)
                    
                    cvv = form.cvv.data.strip()
                    if not cvv.isdigit() or len(cvv) not in [3, 4]:
                        flash('Invalid CVV', 'error')
                        return render_template('payment.html', form=form, booking=booking)
                        
                    if not form.card_holder.data or len(form.card_holder.data.strip()) < 2:
                        flash('Please enter a valid card holder name', 'error')
                        return render_template('payment.html', form=form, booking=booking)
                        
                    if not form.expiry_month.data or not form.expiry_year.data:
                        flash('Please select card expiry date', 'error')
                        return render_template('payment.html', form=form, booking=booking)
                        
                    # Check if card is expired
                    expiry_date = datetime(int(form.expiry_year.data), int(form.expiry_month.data), 1)
                    if expiry_date.date() < datetime.now().date():
                        flash('Card has expired', 'error')
                        return render_template('payment.html', form=form, booking=booking)
                        
                elif payment_method == 'paypal':
                    # Validate PayPal email
                    if not form.paypal_email.data or '@' not in form.paypal_email.data:
                        flash('Please enter a valid PayPal email address', 'error')
                        return render_template('payment.html', form=form, booking=booking)
                        
                elif payment_method == 'googlepay':
                    # Validate Google Pay account
                    if not form.google_account.data or '@' not in form.google_account.data:
                        flash('Please enter a valid Google account email', 'error')
                        return render_template('payment.html', form=form, booking=booking)
                
                # In a real application, you would process the payment here based on the payment method
                # For this demo, we'll just mark the booking as paid
                booking.payment_status = 'paid'
                booking.status = 'confirmed'
                booking.booking_date = datetime.utcnow()
                booking.payment_method = payment_method
                
                # Mark the room as unavailable for these dates
                room = Room.query.get(booking.room_id)
                if room:
                    room.available = False
                
                db.session.commit()
                
                # Clear session data
                session.pop('check_in', None)
                session.pop('check_out', None)
                
                flash('Payment successful! Your booking has been confirmed.', 'success')
                return redirect(url_for('booking_confirmation', booking_id=booking.id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error processing payment: {str(e)}")
                flash('An error occurred while processing your payment. Please try again.', 'error')
                return render_template('payment.html', form=form, booking=booking)
        
        return render_template('payment.html', 
                             form=form, 
                             booking=booking)
                             
    except Exception as e:
        app.logger.error(f"Error in payment route: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid email or password')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    now = datetime.utcnow()
    upcoming_bookings = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.check_in >= now
    ).order_by(Booking.check_in).all()
    
    past_bookings = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.check_in < now
    ).order_by(Booking.check_in.desc()).all()
    
    return render_template('profile.html',
                         upcoming_bookings=upcoming_bookings,
                         past_bookings=past_bookings)

@app.route('/booking/confirmation/<int:booking_id>')
@login_required
def booking_confirmation(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Verify booking belongs to current user
        if booking.user_id != current_user.id:
            flash('Unauthorized access', 'error')
            return redirect(url_for('index'))
            
        # Check if booking is confirmed
        if booking.status != 'confirmed' or booking.payment_status != 'paid':
            flash('This booking is not yet confirmed', 'error')
            return redirect(url_for('index'))
            
        # Calculate advance booking discount
        days_until_checkin = (booking.check_in - datetime.utcnow()).days
        if days_until_checkin > 60:
            booking.advance_booking_discount = 0.15  # 15% discount
        elif days_until_checkin > 30:
            booking.advance_booking_discount = 0.10  # 10% discount
        else:
            booking.advance_booking_discount = 0
            
        db.session.commit()
            
        return render_template('booking_confirmation.html', 
                             booking=booking)
                             
    except Exception as e:
        app.logger.error(f"Error in booking confirmation route: {str(e)}")
        flash('An error occurred', 'error')
        return redirect(url_for('index'))

@app.route('/booking/cancel/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized access')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        booking.status = 'cancelled'
        db.session.commit()
        flash('Booking cancelled successfully')
        return redirect(url_for('profile'))
    
    # Calculate cancellation charges
    days_until_checkin = (booking.check_in - datetime.utcnow()).days
    if days_until_checkin > 7:
        cancellation_charge = 0
    elif days_until_checkin > 3:
        cancellation_charge = booking.total_price * 0.5
    else:
        cancellation_charge = booking.total_price
    
    return render_template('cancellation.html',
                         booking=booking,
                         cancellation_charge=cancellation_charge)

@app.route('/api/check-availability', methods=['POST'])
def check_availability():
    data = request.get_json()
    hotel_id = data.get('hotel_id')
    room_type = data.get('room_type')
    check_in = datetime.strptime(data.get('check_in'), '%Y-%m-%d')
    check_out = datetime.strptime(data.get('check_out'), '%Y-%m-%d')
    
    # Check if there are any overlapping bookings
    overlapping_bookings = Booking.query.filter(
        Booking.hotel_id == hotel_id,
        Booking.status != 'cancelled',
        Booking.check_in < check_out,
        Booking.check_out > check_in
    ).join(Room).filter(Room.type == room_type).count()
    
    # Get total rooms of this type
    total_rooms = Room.query.filter_by(
        hotel_id=hotel_id,
        type=room_type
    ).count()
    
    return jsonify({'available': overlapping_bookings < total_rooms})

@app.route('/download/receipt/<int:booking_id>')
@login_required
def download_receipt(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized access')
        return redirect(url_for('index'))
    
    # Generate receipt logic here
    # For now, we'll just return a simple text file
    content = f"""
    Booking Receipt
    --------------
    Booking ID: {booking.id}
    Hotel: {booking.hotel.name}
    Room Type: {booking.room.type}
    Check-in: {booking.check_in.strftime('%Y-%m-%d')}
    Check-out: {booking.check_out.strftime('%Y-%m-%d')}
    Guests: {booking.guests}
    Total Price: ${booking.total_price:.2f}
    """
    
    return content, 200, {
        'Content-Type': 'text/plain',
        'Content-Disposition': f'attachment; filename=receipt_{booking.id}.txt'
    }

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data) and user.is_admin:
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid email or password', 'error')
    return render_template('admin/login.html', form=form)

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    hotels = Hotel.query.all()
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', hotels=hotels, recent_bookings=recent_bookings)

@app.route('/admin/hotels', methods=['GET', 'POST'])
@admin_required
def admin_hotels():
    form = HotelForm()
    if form.validate_on_submit():
        hotel = Hotel(
            name=form.name.data,
            city=form.city.data,
            address=form.address.data,
            description=form.description.data,
            rating=form.rating.data
        )
        db.session.add(hotel)
        db.session.commit()
        flash('Hotel added successfully', 'success')
        return redirect(url_for('admin_hotels'))
    
    hotels = Hotel.query.all()
    return render_template('admin/hotels.html', hotels=hotels, form=form)

@app.route('/admin/hotel/<int:hotel_id>/rooms', methods=['GET', 'POST'])
@admin_required
def admin_rooms(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    form = RoomForm()
    
    if form.validate_on_submit():
        room = Room(
            hotel=hotel,
            type=form.type.data,
            description=form.description.data,
            base_price=form.base_price.data,
            max_guests=form.max_guests.data,
            available=form.available.data
        )
        db.session.add(room)
        db.session.commit()
        flash('Room added successfully', 'success')
        return redirect(url_for('admin_rooms', hotel_id=hotel_id))
    
    rooms = hotel.rooms
    return render_template('admin/rooms.html', hotel=hotel, rooms=rooms, form=form)

@app.route('/admin/reports')
@admin_required
def admin_reports():
    hotels = Hotel.query.all()
    current_month = datetime.utcnow().replace(day=1)
    
    # Generate reports for each hotel
    reports = []
    for hotel in hotels:
        report = {
            'hotel': hotel,
            'total_bookings': Booking.query.filter_by(hotel_id=hotel.id).count(),
            'total_revenue': sum([booking.total_price for booking in Booking.query.filter_by(hotel_id=hotel.id).all()])
        }
        reports.append(report)
    
    # Get top customers
    top_customers = db.session.query(
        User,
        db.func.count(Booking.id).label('booking_count'),
        db.func.sum(Booking.total_price).label('total_spent')
    ).join(Booking).group_by(User.id).order_by(db.text('total_spent DESC')).limit(5).all()
    
    return render_template('admin/reports.html', reports=reports, top_customers=top_customers)

@app.route('/admin/currencies', methods=['GET', 'POST'])
@admin_required
def admin_currencies():
    form = CurrencyForm()
    if form.validate_on_submit():
        currency = Currency(
            code=form.code.data.upper(),
            name=form.name.data,
            exchange_rate=form.exchange_rate.data
        )
        db.session.add(currency)
        db.session.commit()
        flash('Currency added successfully', 'success')
        return redirect(url_for('admin_currencies'))
    
    currencies = Currency.query.all()
    return render_template('admin/currencies.html', currencies=currencies, form=form)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

def init_db():
    """Initialize the database with sample data"""
    try:
        with app.app_context():
            # Create tables
            db.create_all()
            
            # Check if admin user exists
            admin = User.query.filter_by(email='admin@example.com').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    is_admin=True
                )
                admin.set_password('admin123')
                db.session.add(admin)

            # Add sample user if not exists
            user = User.query.filter_by(email='user@example.com').first()
            if not user:
                user = User(
                    username='user',
                    email='user@example.com',
                    name='John Doe',
                    phone='+1234567890'
                )
                user.set_password('user123')
                db.session.add(user)
            
            # Add currencies
            currencies = [
                {'code': 'GBP', 'name': 'British Pound', 'exchange_rate': 1.0},
                {'code': 'EUR', 'name': 'Euro', 'exchange_rate': 1.16},
                {'code': 'USD', 'name': 'US Dollar', 'exchange_rate': 1.27}
            ]
            
            for currency_data in currencies:
                if not Currency.query.filter_by(code=currency_data['code']).first():
                    currency = Currency(**currency_data)
                    db.session.add(currency)

            # Add sample hotels if not exist
            hotels_data = [
                {
                    'name': 'Grand Hotel London',
                    'city': 'London',
                    'address': '123 Oxford Street, London',
                    'description': 'Luxury hotel in the heart of London',
                    'rating': 4.5,
                    'amenities': json.dumps(['WiFi', 'Pool', 'Spa', 'Restaurant']),
                    'images': json.dumps(['hotel1.jpg', 'hotel2.jpg'])
                },
                {
                    'name': 'Manchester City Hotel',
                    'city': 'Manchester',
                    'address': '456 Main Street, Manchester',
                    'description': 'Modern hotel near Manchester City Centre',
                    'rating': 4.2,
                    'amenities': json.dumps(['WiFi', 'Gym', 'Restaurant']),
                    'images': json.dumps(['hotel3.jpg', 'hotel4.jpg'])
                }
            ]

            for hotel_data in hotels_data:
                if not Hotel.query.filter_by(name=hotel_data['name']).first():
                    hotel = Hotel(**hotel_data)
                    db.session.add(hotel)
                    db.session.flush()  # Get hotel ID

                    # Add rooms for each hotel
                    rooms_data = [
                        {
                            'hotel_id': hotel.id,
                            'type': 'standard',
                            'description': 'Comfortable standard room',
                            'base_price': 100.0,
                            'price': 100.0,
                            'peak_price': 130.0,
                            'capacity': 2,
                            'amenities': json.dumps(['WiFi', 'TV', 'Air Conditioning']),
                            'images': json.dumps(['room1.jpg', 'room2.jpg'])
                        },
                        {
                            'hotel_id': hotel.id,
                            'type': 'double',
                            'description': 'Spacious double room',
                            'base_price': 150.0,
                            'price': 150.0,
                            'peak_price': 195.0,
                            'capacity': 3,
                            'amenities': json.dumps(['WiFi', 'TV', 'Mini Bar', 'Air Conditioning']),
                            'images': json.dumps(['room3.jpg', 'room4.jpg'])
                        },
                        {
                            'hotel_id': hotel.id,
                            'type': 'family',
                            'description': 'Large family room',
                            'base_price': 200.0,
                            'price': 200.0,
                            'peak_price': 260.0,
                            'capacity': 4,
                            'amenities': json.dumps(['WiFi', 'TV', 'Mini Bar', 'Air Conditioning', 'Kitchen']),
                            'images': json.dumps(['room5.jpg', 'room6.jpg'])
                        }
                    ]

                    for room_data in rooms_data:
                        room = Room(**room_data)
                        db.session.add(room)

            db.session.commit()
            print("Database initialized successfully!")
            
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, host='127.0.0.1', port=8000)
