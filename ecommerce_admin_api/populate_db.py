import random
import logging
from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError # To handle potential unique constraint violations

    # Import necessary components from your project
from database import SessionLocal, engine # Use the same session/engine setup
import models
import schemas
import crud # We can use CRUD functions to add data

    # --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

    # --- Sample Data ---
    # More realistic product names and categories
PRODUCT_DATA = [
        {"name": "Wireless Noise Cancelling Headphones", "category": "Electronics", "price": 149.99, "desc": "Over-ear headphones with active noise cancellation and 30-hour battery life."},
        {"name": "Smart LED TV 55-Inch 4K UHD", "category": "Electronics", "price": 479.00, "desc": "Ultra high definition smart TV with built-in streaming apps (Netflix, Hulu, etc.)."},
        {"name": "Organic Cotton T-Shirt (White)", "category": "Apparel", "price": 19.95, "desc": "Soft and breathable 100% GOTS certified organic cotton t-shirt."},
        {"name": "Men's Running Shoes Size 10", "category": "Footwear", "price": 85.50, "desc": "Lightweight and supportive running shoes with breathable mesh upper."},
        {"name": "Stainless Steel Water Bottle 1L", "category": "Home & Kitchen", "price": 22.00, "desc": "Double-wall insulated vacuum flask, keeps drinks cold for 24 hours or hot for 12 hours. BPA-free."},
        {"name": "Non-Stick Frying Pan Set (3-Piece)", "category": "Home & Kitchen", "price": 45.99, "desc": "Durable non-stick ceramic coated pans (8-inch, 10-inch, 12-inch) for everyday cooking."},
        {"name": "Yoga Mat Extra Thick (6mm)", "category": "Sports & Outdoors", "price": 29.99, "desc": "Comfortable and non-slip TPE yoga mat with carrying strap."},
        {"name": "Laptop Backpack with USB Charging Port", "category": "Accessories", "price": 39.99, "desc": "Water-resistant durable backpack with padded laptop compartment (up to 15.6 inch) and external USB port."},
        {"name": "Instant Read Meat Thermometer", "category": "Home & Kitchen", "price": 15.75, "desc": "Digital food thermometer with backlight and magnet. Reads temperature in 3-5 seconds."},
        {"name": "Scented Soy Candle (Lavender)", "category": "Home Decor", "price": 12.50, "desc": "Relaxing lavender essential oil scented candle made from natural soy wax. 45-hour burn time."},
        {"name": "Bluetooth Speaker Portable Waterproof", "category": "Electronics", "price": 35.00, "desc": "Compact portable speaker with IPX7 waterproof rating and 12-hour playtime."},
        {"name": "Electric Kettle 1.7L Fast Boil", "category": "Home & Kitchen", "price": 28.99, "desc": "Stainless steel electric kettle with auto shut-off and boil-dry protection."},
    ]

    # --- Helper Functions ---
def get_random_datetime(start_date, end_date):
        """Generates a random datetime between start_date and end_date."""
        time_between_dates = end_date - start_date
        # Ensure time difference is positive
        if time_between_dates.total_seconds() <= 0:
            return start_date # Or handle error appropriately
        seconds_between_dates = time_between_dates.total_seconds()
        random_number_of_seconds = random.randrange(int(seconds_between_dates))
        random_date = start_date + timedelta(seconds=random_number_of_seconds)
        return random_date

    # --- Main Population Logic ---
def populate():
        logger.info("--- Starting database population ---")
        db: Session = SessionLocal() # Get a new session

        created_products_map = {} # Store created products by name for quick lookup

        try:
            # 1. Create Products and Initial Inventory
            logger.info("Step 1: Creating products and initial inventory...")
            for item in PRODUCT_DATA:
                product_name = item['name']
                logger.info(f"  Processing product: {product_name}")

                # Check if product already exists in this run or in DB
                if product_name in created_products_map:
                    logger.info(f"    Product '{product_name}' already processed in this run. Skipping.")
                    continue

                existing_product = crud.get_product_by_name(db, name=product_name)
                if existing_product:
                    logger.info(f"    Product '{product_name}' already exists in DB (ID: {existing_product.id}). Skipping creation.")
                    created_products_map[product_name] = existing_product # Store existing product
                    continue

                # Create product using schema
                product_in = schemas.ProductCreate(
                    name=product_name,
                    description=item.get('desc'), # Use get with default None
                    category=item.get('category', 'Uncategorized'), # Provide default category
                    price=item['price'],
                    initial_quantity=random.randint(20, 150), # Random initial stock (adjusted range)
                    low_stock_threshold=random.randint(5, 15)  # Random low stock threshold (adjusted range)
                )
                try:
                    # Use the CRUD function to create product and inventory
                    created_product = crud.create_product(db=db, product=product_in)
                    if created_product:
                        created_products_map[product_name] = created_product
                        logger.info(f"    Successfully created product '{created_product.name}' with ID {created_product.id}")
                    else:
                        # This case might happen if there's a race condition not caught above
                        logger.warning(f"    Failed to create product '{product_name}' (CRUD function returned None). Might be duplicate.")
                        db.rollback() # Rollback potential partial changes

                except IntegrityError:
                    db.rollback() # Rollback the specific failed transaction
                    logger.warning(f"    IntegrityError: Product '{product_name}' likely already exists (concurrent creation?). Skipping.")
                except ValueError as ve:
                     db.rollback()
                     logger.error(f"    ValueError creating product '{product_name}': {ve}")
                except Exception as e:
                     db.rollback()
                     logger.error(f"    Unexpected error creating product '{product_name}': {e}", exc_info=True)


            # Get list of product objects that were successfully created or found
            available_products = list(created_products_map.values())
            if not available_products:
                logger.warning("No products available in the database to generate sales for. Exiting population script.")
                return # Exit if no products were created or found

            logger.info(f"Total available products for sales generation: {len(available_products)}")

            # 2. Create Sales Data
            logger.info("\nStep 2: Creating sales data...")
            num_sales_to_create = 500 # Create more sales records
            sales_created_count = 0
            sales_skipped_stock = 0
            # Sales over the last 6 months for more data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)

            for i in range(num_sales_to_create):
                # Select a random product
                if not available_products:
                    logger.warning("Ran out of available products for sales.")
                    break
                product_to_sell = random.choice(available_products)

                # Determine quantity to sell
                sell_qty = random.randint(1, 3) # Sell smaller quantities more often

                sale_in = schemas.SaleCreate(
                    product_id=product_to_sell.id,
                    quantity_sold=sell_qty
                )

                try:
                    # Use the CRUD function to create the sale and update inventory
                    # This function now includes the stock check
                    sale = crud.create_sale(db=db, sale=sale_in)

                    # Manually set a random sale date *after* creating the sale record
                    # because crud.create_sale uses the DB default (current time) initially.
                    random_sale_date = get_random_datetime(start_date, end_date)
                    sale.sale_date = random_sale_date
                    db.add(sale) # Add the modified sale object back to the session
                    db.commit() # Commit the date change
                    # db.refresh(sale) # Refresh not strictly needed after commit unless reading back immediately

                    sales_created_count += 1
                    if sales_created_count % 100 == 0: # Print progress periodically
                         logger.info(f"  Created {sales_created_count}/{num_sales_to_create} sales records...")

                except ValueError as e:
                     # Catch insufficient stock errors specifically
                     if "Insufficient stock" in str(e):
                         sales_skipped_stock += 1
                         # Optionally remove product from available list if consistently out of stock
                         # available_products.remove(product_to_sell)
                     else:
                         logger.warning(f"  Skipping sale for '{product_to_sell.name}': {e}")
                     db.rollback() # Rollback the failed sale attempt
                except Exception as e:
                     db.rollback()
                     logger.error(f"  Error creating sale for product ID {product_to_sell.id}: {e}", exc_info=True)


            logger.info(f"\nFinished creating sales records.")
            logger.info(f"  Successfully created: {sales_created_count}")
            logger.info(f"  Skipped due to insufficient stock: {sales_skipped_stock}")

            # 3. Optional: Simulate some inventory updates (e.g., restocking)
            logger.info("\nStep 3: Simulating inventory updates (restocking)...")
            restock_count = 0
            # Get products again to ensure we have latest state if needed
            products_to_consider_restock = crud.get_products(db, limit=len(available_products) + 5) # Fetch slightly more
            for product in products_to_consider_restock:
                # Restock about 25% of the products randomly
                if random.random() < 0.25:
                    restock_qty = random.randint(10, 50)
                    # Need current quantity to add to it
                    current_inventory = crud.get_inventory(db, product.id)
                    if not current_inventory:
                        logger.warning(f"  Cannot restock '{product.name}', inventory record missing.")
                        continue

                    new_quantity = current_inventory.quantity + restock_qty
                    inventory_update = schemas.InventoryUpdate(quantity=new_quantity)
                    try:
                        updated = crud.update_inventory(db, product_id=product.id, inventory_update=inventory_update)
                        if updated:
                            logger.info(f"  Restocked '{product.name}' by {restock_qty} units. New quantity: {updated.quantity}")
                            restock_count += 1
                        else:
                            logger.warning(f"  Restock failed for '{product.name}' (update returned None).")
                            db.rollback()
                    except Exception as e:
                        logger.error(f"  Error restocking '{product.name}': {e}", exc_info=True)
                        db.rollback()

            logger.info(f"Simulated {restock_count} restocking events.")


            logger.info("\n--- Database population script finished successfully. ---")

        except Exception as e:
            db.rollback() # Rollback any changes if a major error occurs during the process
            logger.error(f"\n--- An error occurred during database population: {e} ---", exc_info=True)
        finally:
            db.close() # Always close the session
            logger.info("Database session closed.")


    # --- Run the population script ---
if __name__ == "__main__":
        logger.info("Running database population script...")
        # Optional: Add confirmation step?
        # confirm = input("This will add demo data to the database defined in .env. Proceed? (y/n): ")
        # if confirm.lower() == 'y':
        #     populate()
        # else:
        #     logger.info("Population cancelled by user.")
        populate() # Run directly
        logger.info("Script execution complete.")
    