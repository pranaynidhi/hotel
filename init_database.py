from app import app, db, init_db

with app.app_context():
    db.drop_all()
    init_db()
