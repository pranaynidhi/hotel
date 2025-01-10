from datetime import datetime, timedelta
from models import Room, Booking, Hotel, User
from typing import Tuple, List, Dict, Optional

def check_peak_season(date: datetime) -> bool:
    """Check if given date falls in peak season."""
    month = date.month
    return month in [4, 5, 6, 7, 8, 11, 12]

def calculate_room_price(hotel: Hotel, room_type: str, check_in: datetime, 
                        check_out: datetime, num_guests: int) -> Tuple[float, float]:
    """
    Calculate room price including any guest surcharges.
    Returns (base_price, total_price)
    """
    nights = (check_out - check_in).days
    base_price = hotel.get_room_price(room_type, check_in, num_guests)
    total_price = base_price * nights
    
    return base_price, total_price

def calculate_advance_booking_discount(check_in: datetime) -> Tuple[float, str]:
    """
    Calculate advance booking discount percentage and reason.
    Returns (discount_percentage, discount_reason)
    """
    days_in_advance = (check_in - datetime.now()).days
    
    if 80 <= days_in_advance <= 90:
        return 0.30, "30% discount for booking 80-90 days in advance"
    elif 60 <= days_in_advance <= 79:
        return 0.20, "20% discount for booking 60-79 days in advance"
    elif 45 <= days_in_advance <= 59:
        return 0.10, "10% discount for booking 45-59 days in advance"
    
    return 0, "No advance booking discount applicable"

def calculate_cancellation_charge(booking: Booking) -> Tuple[float, str]:
    """
    Calculate cancellation charge and reason.
    Returns (charge_amount, charge_reason)
    """
    days_until_checkin = (booking.check_in - datetime.now()).days
    
    if days_until_checkin > 60:
        return 0, "No cancellation charge for cancellations over 60 days before check-in"
    elif 30 <= days_until_checkin <= 60:
        charge = booking.total_price * 0.5
        return charge, "50% cancellation charge for cancellations 30-60 days before check-in"
    else:
        return booking.total_price, "100% cancellation charge for cancellations within 30 days of check-in"

def find_available_rooms(hotel: Hotel, check_in: datetime, check_out: datetime, 
                        room_type: str, num_guests: int) -> List[Room]:
    """Find available rooms matching the criteria."""
    # Validate room type and guests
    if room_type == 'standard' and num_guests > 1:
        return []
    elif room_type == 'double' and num_guests > 2:
        return []
    elif room_type == 'family' and num_guests > 4:
        return []

    # Get all rooms of the specified type
    rooms = Room.query.filter_by(hotel_id=hotel.id, room_type=room_type).all()
    
    # Filter for availability
    available_rooms = [
        room for room in rooms 
        if room.is_available(check_in, check_out)
    ]
    
    return available_rooms

def validate_booking_request(check_in: datetime, check_out: datetime, 
                           room_type: str, num_guests: int) -> Tuple[bool, str]:
    """
    Validate booking request parameters.
    Returns (is_valid, error_message)
    """
    # Check if dates are in the future
    if check_in < datetime.now():
        return False, "Check-in date must be in the future"

    # Check if check-out is after check-in
    if check_out <= check_in:
        return False, "Check-out date must be after check-in date"

    # Check maximum advance booking (3 months)
    max_advance_date = datetime.now() + timedelta(days=90)
    if check_in > max_advance_date:
        return False, "Bookings can only be made up to 3 months in advance"

    # Check maximum stay duration (30 days)
    if (check_out - check_in).days > 30:
        return False, "Maximum stay duration is 30 days"

    # Validate room type and number of guests
    if room_type == 'standard' and num_guests > 1:
        return False, "Standard rooms can only accommodate 1 guest"
    elif room_type == 'double' and num_guests > 2:
        return False, "Double rooms can only accommodate 2 guests"
    elif room_type == 'family' and num_guests > 4:
        return False, "Family rooms can only accommodate up to 4 guests"

    return True, "Valid booking request"

def generate_booking_receipt(booking: Booking) -> Dict:
    """Generate booking receipt with all details."""
    hotel = booking.hotel
    room = booking.room
    nights = (booking.check_out - booking.check_in).days
    
    receipt = {
        "booking_id": booking.booking_id,
        "hotel_name": hotel.name,
        "hotel_city": hotel.city,
        "room_type": room.room_type,
        "room_number": room.room_number,
        "check_in": booking.check_in.strftime("%Y-%m-%d"),
        "check_out": booking.check_out.strftime("%Y-%m-%d"),
        "num_nights": nights,
        "num_guests": booking.num_guests,
        "room_features": room.features,
        "base_price_per_night": booking.total_price / nights,
        "total_price": booking.total_price,
        "discount_applied": booking.discount_applied,
        "final_price": booking.total_price * (1 - booking.discount_applied),
        "booking_date": booking.booking_date.strftime("%Y-%m-%d %H:%M"),
        "is_peak_season": check_peak_season(booking.check_in),
        "cancellation_policy": {
            "over_60_days": "No charge",
            "30_to_60_days": "50% of booking price",
            "under_30_days": "100% of booking price"
        }
    }
    
    return receipt

def get_room_availability_summary(hotel: Hotel, start_date: datetime, 
                                end_date: datetime) -> Dict:
    """Get room availability summary for a date range."""
    summary = {
        "standard": {"total": hotel.standard_rooms, "available": 0},
        "double": {"total": hotel.double_rooms, "available": 0},
        "family": {"total": hotel.family_rooms, "available": 0}
    }
    
    for room_type in ["standard", "double", "family"]:
        available_rooms = find_available_rooms(
            hotel, start_date, end_date, room_type, 1
        )
        summary[room_type]["available"] = len(available_rooms)
    
    return summary

def get_dashboard_stats() -> Dict:
    """Get statistics for admin dashboard."""
    from models import User, Hotel, Booking
    from sqlalchemy import func
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    stats = {
        "total_users": User.query.count(),
        "total_hotels": Hotel.query.count(),
        "total_bookings": Booking.query.count(),
        "active_bookings": Booking.query.filter(
            Booking.check_out >= datetime.now(),
            Booking.status == 'confirmed'
        ).count(),
        "monthly_revenue": db.session.query(
            func.sum(Booking.total_price)
        ).filter(
            func.extract('month', Booking.booking_date) == current_month,
            func.extract('year', Booking.booking_date) == current_year,
            Booking.status == 'confirmed'
        ).scalar() or 0,
        "recent_bookings": Booking.query.order_by(
            Booking.booking_date.desc()
        ).limit(5).all()
    }
    
    return stats

def get_hotel_performance(hotel_id: int, start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> Dict:
    """Get hotel performance metrics for the specified period."""
    from models import Booking
    from sqlalchemy import func
    
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    
    bookings = Booking.query.filter(
        Booking.hotel_id == hotel_id,
        Booking.booking_date.between(start_date, end_date),
        Booking.status == 'confirmed'
    )
    
    total_revenue = db.session.query(
        func.sum(Booking.total_price)
    ).filter(
        Booking.hotel_id == hotel_id,
        Booking.booking_date.between(start_date, end_date),
        Booking.status == 'confirmed'
    ).scalar() or 0
    
    metrics = {
        "total_bookings": bookings.count(),
        "total_revenue": total_revenue,
        "average_booking_value": total_revenue / bookings.count() if bookings.count() > 0 else 0,
        "occupancy_rate": calculate_occupancy_rate(hotel_id, start_date, end_date),
        "cancellation_rate": calculate_cancellation_rate(hotel_id, start_date, end_date)
    }
    
    return metrics

def calculate_occupancy_rate(hotel_id: int, start_date: datetime, end_date: datetime) -> float:
    """Calculate hotel occupancy rate for the specified period."""
    from models import Hotel, Booking
    
    hotel = Hotel.query.get(hotel_id)
    if not hotel:
        return 0.0
    
    total_room_days = hotel.total_capacity * (end_date - start_date).days
    
    booked_room_days = db.session.query(
        func.sum(
            func.julianday(func.min(end_date, Booking.check_out)) - 
            func.julianday(func.max(start_date, Booking.check_in))
        )
    ).filter(
        Booking.hotel_id == hotel_id,
        Booking.status == 'confirmed',
        Booking.check_in < end_date,
        Booking.check_out > start_date
    ).scalar() or 0
    
    return (booked_room_days / total_room_days) * 100 if total_room_days > 0 else 0

def calculate_cancellation_rate(hotel_id: int, start_date: datetime, end_date: datetime) -> float:
    """Calculate hotel booking cancellation rate for the specified period."""
    from models import Booking
    
    total_bookings = Booking.query.filter(
        Booking.hotel_id == hotel_id,
        Booking.booking_date.between(start_date, end_date)
    ).count()
    
    cancelled_bookings = Booking.query.filter(
        Booking.hotel_id == hotel_id,
        Booking.booking_date.between(start_date, end_date),
        Booking.status == 'cancelled'
    ).count()
    
    return (cancelled_bookings / total_bookings) * 100 if total_bookings > 0 else 0

def generate_monthly_report(month: int, year: int) -> Dict:
    """Generate monthly report with key metrics."""
    from models import Booking, Hotel
    from sqlalchemy import func
    
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    bookings = Booking.query.filter(
        Booking.booking_date.between(start_date, end_date)
    )
    
    report = {
        "period": f"{start_date.strftime('%B %Y')}",
        "total_bookings": bookings.count(),
        "total_revenue": db.session.query(
            func.sum(Booking.total_price)
        ).filter(
            Booking.booking_date.between(start_date, end_date),
            Booking.status == 'confirmed'
        ).scalar() or 0,
        "cancelled_bookings": bookings.filter(Booking.status == 'cancelled').count(),
        "top_performing_hotels": get_top_performing_hotels(start_date, end_date, limit=5),
        "room_type_distribution": get_room_type_distribution(start_date, end_date)
    }
    
    return report

def get_top_performing_hotels(start_date: datetime, end_date: datetime, limit: int = 5) -> List[Dict]:
    """Get top performing hotels based on revenue."""
    from models import Hotel, Booking
    from sqlalchemy import func
    
    top_hotels = db.session.query(
        Hotel,
        func.sum(Booking.total_price).label('revenue'),
        func.count(Booking.id).label('bookings')
    ).join(Booking).filter(
        Booking.booking_date.between(start_date, end_date),
        Booking.status == 'confirmed'
    ).group_by(Hotel.id).order_by(
        func.sum(Booking.total_price).desc()
    ).limit(limit).all()
    
    return [{
        'hotel_name': hotel.name,
        'revenue': revenue,
        'bookings': bookings
    } for hotel, revenue, bookings in top_hotels]

def get_room_type_distribution(start_date: datetime, end_date: datetime) -> Dict:
    """Get distribution of bookings by room type."""
    from models import Booking, Room
    from sqlalchemy import func
    
    distribution = db.session.query(
        Room.room_type,
        func.count(Booking.id).label('count')
    ).join(Booking).filter(
        Booking.booking_date.between(start_date, end_date),
        Booking.status == 'confirmed'
    ).group_by(Room.room_type).all()
    
    return {room_type: count for room_type, count in distribution}
