from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import os

def upgrade_database():
    # Get the path to the database file
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hotel.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add new columns to the booking table
        cursor.execute('''
            ALTER TABLE booking 
            ADD COLUMN payment_method VARCHAR(20)
        ''')
        
        cursor.execute('''
            ALTER TABLE booking 
            ADD COLUMN booking_date DATETIME
        ''')
        
        cursor.execute('''
            ALTER TABLE booking 
            ADD COLUMN advance_booking_discount FLOAT DEFAULT 0
        ''')
        
        # Commit the changes
        conn.commit()
        print("Successfully added new columns to booking table")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Columns already exist")
        else:
            print(f"Error: {str(e)}")
            conn.rollback()
    
    finally:
        conn.close()

if __name__ == '__main__':
    upgrade_database()
