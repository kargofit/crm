import json
import os
from app import app, db
from models import Bike

def import_bikes():
    # Path to the JSON file
    json_path = os.path.join(os.path.dirname(__file__), 'config', 'bikes.json')
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    bikes_data = data.get('bike_market_2026', {})
    
    if not bikes_data:
        print("No bike data found in 'bike_market_2026' key.")
        return

    print(f"Found {len(bikes_data)} brands. Starting import...")

    with app.app_context():
        # Optional: ensure tables exist if not already
        db.create_all()
        
        added_count = 0
        skipped_count = 0
        
        for brand, models in bikes_data.items():
            for item in models:
                base_model = item.get('model')
                if not base_model:
                    continue
                    
                variants = item.get('variants', [])
                
                # We want to import both the base model AND the specific variants
                bikes_to_process = []
                
                # 1. Base Model (e.g. "Splendor Plus")
                bikes_to_process.append((base_model, base_model))
                
                # 2. Variants (e.g. "Splendor Plus XTEC 2.0")
                for v in variants:
                    full_name = f"{base_model} {v}"
                    bikes_to_process.append((full_name, base_model))
                
                for b_name, b_model in bikes_to_process:
                    # Check uniqueness by NAME
                    existing_bike = Bike.query.filter_by(name=b_name).first()
                    
                    if not existing_bike:
                        new_bike = Bike(
                            name=b_name,
                            brand=brand,
                            model=b_model
                        )
                        db.session.add(new_bike)
                        added_count += 1
                    else:
                        skipped_count += 1
                        # Optionally update brand if needed
                        if existing_bike.brand != brand:
                            existing_bike.brand = brand
        
        try:
            db.session.commit()
            print(f"Successfully imported bikes.")
            print(f"Added new entries: {added_count}")
            print(f"Skipped existing: {skipped_count}")
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during commit: {e}")

if __name__ == '__main__':
    import_bikes()
