from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_ 
from datetime import datetime, timedelta
from typing import Optional 

import models
import schemas


def get_product(db: Session, product_id: int):
        """Fetches a single product by its ID."""
       
        return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_product_by_name(db: Session, name: str):
        """Fetches a single product by its name."""
        return db.query(models.Product).filter(func.lower(models.Product.name) == func.lower(name)).first()

def get_products(db: Session, skip: int = 0, limit: int = 100, category: Optional[str] = None):
        """Fetches a list of products, with pagination and optional category filtering."""
        query = db.query(models.Product)
        if category:
            
            query = query.filter(func.lower(models.Product.category) == func.lower(category))
        return query.offset(skip).limit(limit).all()

def create_product(db: Session, product: schemas.ProductCreate):
        """Creates a new product and its initial inventory record."""
        
        existing_product = get_product_by_name(db, product.name)
        if existing_product:
            return None 

        db_product = models.Product(
            name=product.name,
            description=product.description,
            category=product.category,
            price=product.price
        )
        db.add(db_product)
        db.flush() 

        db_inventory = models.Inventory(
            product_id=db_product.id,
            quantity=product.initial_quantity,
            low_stock_threshold=product.low_stock_threshold if product.low_stock_threshold is not None else 10 # Ensure default
        )
        db.add(db_inventory)

        db.commit() 
        db.refresh(db_product) 
        db.refresh(db_inventory) 
        db_product.inventory = db_inventory
        return db_product


def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate):
        """Updates an existing product's details."""
        db_product = get_product(db, product_id)
        if not db_product:
            return None

        update_data = product_update.model_dump(exclude_unset=True) 

       
        if "name" in update_data and update_data["name"].lower() != db_product.name.lower():
            existing_product = get_product_by_name(db, update_data["name"])
            if existing_product and existing_product.id != product_id:
                raise ValueError(f"Product name '{update_data['name']}' already exists.")

        for key, value in update_data.items():
            setattr(db_product, key, value)

        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product

def delete_product(db: Session, product_id: int):
        """Deletes a product and its associated inventory and sales records (due to cascade)."""
        db_product = get_product(db, product_id)
        if not db_product:
            return None # Not found
        db.delete(db_product)
        db.commit()
        return db_product


def get_inventory(db: Session, product_id: int):
        """Fetches inventory for a specific product."""
        return db.query(models.Inventory).filter(models.Inventory.product_id == product_id).first()

def get_all_inventory(db: Session, skip: int = 0, limit: int = 100, low_stock: bool = False):
        """Fetches all inventory records, with pagination and optional low stock filtering."""
        query = db.query(models.Inventory)
        if low_stock:
            query = query.filter(models.Inventory.quantity <= models.Inventory.low_stock_threshold)
        return query.offset(skip).limit(limit).all()

def update_inventory(db: Session, product_id: int, inventory_update: schemas.InventoryUpdate):
        """Updates inventory quantity or threshold for a product."""
        db_inventory = get_inventory(db, product_id)
        if not db_inventory:
            return None 

        update_data = inventory_update.model_dump(exclude_unset=True) 

        updated = False
        if "quantity" in update_data and update_data["quantity"] is not None:
            db_inventory.quantity = update_data["quantity"]
            updated = True
        if "low_stock_threshold" in update_data and update_data["low_stock_threshold"] is not None:
            db_inventory.low_stock_threshold = update_data["low_stock_threshold"]
            updated = True

        if updated:
            db.add(db_inventory)
            db.commit()
            db.refresh(db_inventory)

        return db_inventory

def create_sale(db: Session, sale: schemas.SaleCreate):
        """Creates a new sale record and updates inventory."""
        db_product = get_product(db, sale.product_id)
        if not db_product:
            raise ValueError(f"Product with id {sale.product_id} not found.")

        db_inventory = db_product.inventory
        if not db_inventory:
             db_inventory = get_inventory(db, sale.product_id)
             if not db_inventory:
                 raise ValueError(f"CRITICAL: Inventory record for product id {sale.product_id} not found.")

        if db_inventory.quantity < sale.quantity_sold:
            raise ValueError(f"Insufficient stock for product id {sale.product_id}. Available: {db_inventory.quantity}, Requested: {sale.quantity_sold}")

        current_price = db_product.price
        total_revenue = sale.quantity_sold * current_price

        db_sale = models.Sale(
            product_id=sale.product_id,
            quantity_sold=sale.quantity_sold,
            sale_price_per_unit=current_price, 
            total_revenue=total_revenue,
        )

        db_inventory.quantity -= sale.quantity_sold

        db.add(db_sale)
        db.add(db_inventory) 

        db.refresh(db_sale)
        db.refresh(db_inventory)

        return db_sale


def get_sales(db: Session, skip: int = 0, limit: int = 100,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  product_id: Optional[int] = None,
                  category: Optional[str] = None):
        """Fetches sales records with filtering and pagination."""
        query = db.query(models.Sale)

      
        if category:
            query = query.join(models.Product).filter(func.lower(models.Product.category) == func.lower(category))

        if product_id:
            query = query.filter(models.Sale.product_id == product_id)
        if start_date:
            query = query.filter(models.Sale.sale_date >= start_date)
        if end_date:
            
             query = query.filter(models.Sale.sale_date <= end_date)


        return query.order_by(models.Sale.sale_date.desc()).offset(skip).limit(limit).all()


def get_revenue_summary(db: Session, start_date: datetime, end_date: datetime,
                            product_id: Optional[int] = None,
                            category: Optional[str] = None):
        """Calculates total revenue within a date range, optionally filtered."""
        query = db.query(func.sum(models.Sale.total_revenue).label("total_revenue"))

        query = query.filter(models.Sale.sale_date >= start_date)

        query = query.filter(models.Sale.sale_date <= end_date)

        if product_id:
            query = query.filter(models.Sale.product_id == product_id)

        if category:
            query = query.join(models.Product).filter(func.lower(models.Product.category) == func.lower(category))

        result = query.scalar() 
        return result if result is not None else 0.0 


def get_revenue_by_period(db: Session, period: str, start_date: datetime, end_date: datetime):
        """
        Calculates revenue grouped by a specific period (day, week, month, year).
        Returns a list of tuples: (period_start_date, revenue)
        Note: Date truncation functions can be database-specific. These examples lean towards MySQL.
        """
        if period not in ['day', 'week', 'month', 'year']:
            raise ValueError("Invalid period specified. Use 'day', 'week', 'month', or 'year'.")

       
        if period == 'day':
            date_trunc_func = func.date(models.Sale.sale_date)
        elif period == 'week':
            date_trunc_func = func.date(func.subdate(models.Sale.sale_date, func.dayofweek(models.Sale.sale_date) - 1))
        elif period == 'month':
            date_trunc_func = func.date(func.subdate(models.Sale.sale_date, func.dayofmonth(models.Sale.sale_date) - 1))
        elif period == 'year':
            date_trunc_func = func.date(func.subdate(models.Sale.sale_date, func.dayofyear(models.Sale.sale_date) - 1))
        else: 
             raise ValueError("Invalid period")


        query = db.query(
            date_trunc_func.label("period_start"),
            func.sum(models.Sale.total_revenue).label("revenue")
        ).filter(
            models.Sale.sale_date >= start_date,
            models.Sale.sale_date <= end_date
        ).group_by(
            "period_start" 
        ).order_by(
            "period_start" 
        )

        results = query.all()
        return [(datetime.combine(r.period_start, datetime.min.time()), r.revenue) for r in results]

    