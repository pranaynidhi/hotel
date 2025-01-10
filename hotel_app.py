from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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
from flask_migrate import Migrate

app = Flask(__name__)

# MySQL Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:your_password@localhost/hotel_booking'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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
        ('London', 'London'),
        ('Manchester', 'Manchester'),
        ('Birmingham', 'Birmingham'),
        ('Edinburgh', 'Edinburgh'),
        ('Glasgow', 'Glasgow')
    ], validators=[DataRequired()])
    check_in = DateField('Check-in Date', validators=[DataRequired()])
    check_out = DateField('Check-out Date', validators=[DataRequired()])
    room_type = SelectField('Room Type', choices=[
        ('any', 'Any Type'),
        ('standard', 'Standard Room'),
        ('double', 'Double Room'),
        ('family', 'Family Room')
    ])
    guests = IntegerField('Number of Guests', default=1, validators=[
        NumberRange(min=1, max=5, message="Please select between 1 and 5 guests")
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

class PaymentForm(FlaskForm):
    payment_method = SelectField('Payment Method', 
        choices=[
            ('card', 'Credit/Debit Card'),
            ('paypal', 'PayPal'),
            ('googlepay', 'Google Pay')
        ],
        validators=[DataRequired()]
    )
    card_holder = StringField('Card Holder Name', validators=[Optional(), Length(min=2, max=100)])
    card_number = StringField('Card Number', validators=[Optional(), Length(min=16, max=16)])
    expiry_month = SelectField('Expiry Month',
        choices=[(str(i), str(i).zfill(2)) for i in range(1, 13)],
        validators=[Optional()])
    expiry_year = SelectField('Expiry Year',
        choices=[(str(i), str(i)) for i in range(2024, 2035)],
        validators=[Optional()])
    cvv = StringField('CVV', validators=[Optional(), Length(min=3, max=4)])
    submit = SubmitField('Confirm Payment')

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)

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
        """Calculate total price for the room booking."""
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
            # Check if it's weekend (Friday or Saturday)
            is_weekend = current_date.weekday() >= 5
            # Check if it's peak season
            is_peak = current_date.month in [4, 5, 6, 7, 8, 11, 12]
            
            if is_peak:
                day_price = self.peak_price
            else:
                day_price = self.base_price
            
            # Apply weekend surcharge
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
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be an admin to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def is_peak_season(date):
    """Check if a given date falls in peak season (April-August and November-December)"""
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d').date()
    return date.month in [4, 5, 6, 7, 8, 11, 12]

@app.route('/')
def index():
    form = SearchForm()
    hotels = Hotel.query.all()
    return render_template('index.html', form=form, hotels=hotels)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('Error occurred. Please try again.', 'danger')
    
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
            return redirect(next_page) if next_page else redirect(url_for('index'))
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    upcoming_bookings = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.check_in >= datetime.utcnow()
    ).order_by(Booking.check_in).all()
    
    past_bookings = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.check_in < datetime.utcnow()
    ).order_by(Booking.check_in.desc()).all()
    
    return render_template('profile.html', 
                         upcoming_bookings=upcoming_bookings, 
                         past_bookings=past_bookings)

@app.route('/hotel/<int:hotel_id>')
def hotel_details(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    rooms = Room.query.filter_by(hotel_id=hotel_id, available=True).all()
    return render_template('hotel_details.html', hotel=hotel, rooms=rooms)

@app.route('/book/<int:hotel_id>/<int:room_id>', methods=['GET', 'POST'])
@login_required
def booking(hotel_id, room_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    room = Room.query.get_or_404(room_id)
    
    if request.method == 'POST':
        check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d')
        check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d')
        guests = int(request.form['guests'])
        
        # Calculate price
        total_price = room.calculate_price(check_in, check_out)
        
        if total_price:
            booking = Booking(
                user_id=current_user.id,
                hotel_id=hotel_id,
                room_id=room_id,
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                total_price=total_price
            )
            db.session.add(booking)
            db.session.commit()
            
            return redirect(url_for('payment', booking_id=booking.booking_id))
        
        flash('Error calculating price. Please try again.', 'danger')
    
    return render_template('booking.html', hotel=hotel, room=room)

@app.route('/payment/<booking_id>', methods=['GET', 'POST'])
@login_required
def payment(booking_id):
    booking = Booking.query.filter_by(booking_id=booking_id).first_or_404()
    
    if booking.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))
    
    form = PaymentForm()
    if form.validate_on_submit():
        booking.payment_method = form.payment_method.data
        booking.payment_status = 'paid'
        booking.status = 'confirmed'
        
        try:
            db.session.commit()
            flash('Payment successful!', 'success')
            return redirect(url_for('booking_confirmation', booking_id=booking_id))
        except:
            db.session.rollback()
            flash('Error processing payment. Please try again.', 'danger')
    
    return render_template('payment.html', booking=booking, form=form)

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    hotels_count = Hotel.query.count()
    bookings_count = Booking.query.count()
    users_count = User.query.count()
    revenue = db.session.query(db.func.sum(Booking.total_price)).filter_by(status='confirmed').scalar() or 0
    
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         hotels_count=hotels_count,
                         bookings_count=bookings_count,
                         users_count=users_count,
                         revenue=revenue,
                         recent_bookings=recent_bookings)

def init_db():
    """Initialize the database with some sample data"""
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
        
        try:
            db.session.commit()
            print("Database initialized successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {str(e)}")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=8000)
