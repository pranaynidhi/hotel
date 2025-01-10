# Hotel Booking System

A comprehensive hotel booking system built with Flask and MySQL.

## Features

- User registration and authentication
- Hotel and room management
- Booking system with payment processing
- Admin dashboard
- Currency conversion
- Peak season pricing
- Responsive design

## Prerequisites

- Python 3.8 or higher
- MySQL 8.0 or higher
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd hotel-booking-system
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Configure MySQL:
- Install MySQL if you haven't already
- Create a MySQL user or use root
- Update the .env file with your MySQL credentials

5. Initialize the database:
```bash
python init_mysql.py
python hotel_app.py
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:
```
FLASK_APP=hotel_app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=hotel_booking
```

## Running the Application

1. Start the Flask application:
```bash
python hotel_app.py
```

2. Access the application at `http://localhost:8000`

## Default Admin Account

- Email: admin@example.com
- Password: admin123

## Project Structure

```
hotel-booking-system/
├── hotel_app.py          # Main application file
├── init_mysql.py         # Database initialization script
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── static/              # Static files (CSS, JS, images)
└── templates/           # HTML templates
```

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.
