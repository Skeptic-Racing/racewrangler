import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from models import Car
from database import SessionLocal, init_db


def load_cars_from_json():
    """Load cars from the hardcoded cars list JSON file."""
    json_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "docs",
        "poc",
        "hardcoded cars list.json"
    )
    
    with open(json_path, "r") as f:
        cars_data = json.load(f)
    
    return cars_data


def seed_database():
    """Seed the database with cars from the hardcoded list."""
    # Initialize tables
    init_db()
    
    # Get or create session
    db = SessionLocal()
    
    try:
        # Check if cars already exist
        existing_count = db.query(Car).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} cars. Skipping seed.")
            return
        
        # Load cars from JSON
        cars_data = load_cars_from_json()
        
        # Insert cars
        for car_data in cars_data:
            car = Car(
                id=car_data.get("id"),
                number=car_data.get("number"),
                class_name=car_data.get("class"),
                model=car_data.get("model")
            )
            db.add(car)
        
        db.commit()
        print(f"Successfully seeded {len(cars_data)} cars into the database.")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
