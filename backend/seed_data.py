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
    """Seed the database with cars from the hardcoded list (POC only)."""
    init_db()
    db = SessionLocal()
    try:
        existing_count = db.query(Car).count()
        if existing_count > 0:
            return
        try:
            cars_data = load_cars_from_json()
        except FileNotFoundError:
            return
        for car_data in cars_data:
            car = Car(
                id=car_data.get("id"),
                number=car_data.get("number"),
                class_name=car_data.get("class"),
                model=car_data.get("model")
            )
            db.add(car)
        db.commit()
        print(f"Seeded {len(cars_data)} cars.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
