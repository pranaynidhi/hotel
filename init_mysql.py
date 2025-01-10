import mysql.connector
from mysql.connector import Error
import os

def create_database():
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="your_password"  # Replace with your MySQL root password
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS hotel_booking")
            print("Database 'hotel_booking' created successfully")
            
            # Switch to the hotel_booking database
            cursor.execute("USE hotel_booking")
            
            # Create tables
            tables = {}
            
            tables['users'] = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE
            ) ENGINE=InnoDB
            """
            
            tables['hotels'] = """
            CREATE TABLE IF NOT EXISTS hotels (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                city VARCHAR(50) NOT NULL,
                address VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                rating FLOAT DEFAULT 0.0,
                amenities JSON,
                images JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """
            
            tables['rooms'] = """
            CREATE TABLE IF NOT EXISTS rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_id INT NOT NULL,
                type VARCHAR(50) NOT NULL,
                description TEXT,
                base_price FLOAT NOT NULL,
                price FLOAT NOT NULL,
                peak_price FLOAT,
                capacity INT DEFAULT 2,
                amenities JSON,
                images JSON,
                available BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hotel_id) REFERENCES hotels(id)
            ) ENGINE=InnoDB
            """
            
            tables['bookings'] = """
            CREATE TABLE IF NOT EXISTS bookings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                booking_id VARCHAR(50) UNIQUE NOT NULL,
                user_id INT NOT NULL,
                hotel_id INT NOT NULL,
                room_id INT NOT NULL,
                check_in DATETIME NOT NULL,
                check_out DATETIME NOT NULL,
                guests INT NOT NULL,
                total_price FLOAT NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                payment_status VARCHAR(20) DEFAULT 'pending',
                payment_method VARCHAR(20),
                booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                advance_booking_discount FLOAT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (hotel_id) REFERENCES hotels(id),
                FOREIGN KEY (room_id) REFERENCES rooms(id)
            ) ENGINE=InnoDB
            """
            
            tables['currencies'] = """
            CREATE TABLE IF NOT EXISTS currencies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(3) UNIQUE NOT NULL,
                name VARCHAR(50) NOT NULL,
                exchange_rate FLOAT NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """
            
            # Create each table
            for table_name in tables:
                table_query = tables[table_name]
                try:
                    cursor.execute(table_query)
                    print(f"Created table {table_name}")
                except Error as e:
                    print(f"Error creating table {table_name}: {str(e)}")
            
            print("All tables created successfully")
            
    except Error as e:
        print(f"Error connecting to MySQL: {str(e)}")
        
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed")

if __name__ == "__main__":
    create_database()
