from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from typing import List, Optional

import crud
import schemas
from database import get_db

    # Create an API router instance
router = APIRouter(
        prefix="/inventory", # All routes start with /inventory
        tags=["Inventory"], # Tag for API docs
        responses={404: {"description": "Inventory or Product not found"}},
    )

    # --- Endpoint to Get All Inventory Status ---
@router.get("/", response_model=List[schemas.Inventory])
def read_all_inventory_endpoint( # Renamed endpoint function
        skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
        limit: int = Query(100, ge=1, le=200, description="Maximum number of records to return"),
        low_stock: bool = Query(False, description="Set to true to only return items at or below low stock threshold"),
        db: Session = Depends(get_db)
    ):
        """
        Retrieves a list of inventory records for all products.
        Supports pagination and filtering for low stock items.
        """
        inventory_list = crud.get_all_inventory(db, skip=skip, limit=limit, low_stock=low_stock)
        return inventory_list


    # --- Endpoint to Get Inventory for a Specific Product ---
@router.get("/{product_id}", response_model=schemas.Inventory)
def read_product_inventory_endpoint( # Renamed endpoint function
        product_id: int = Path(..., gt=0, description="The ID of the product whose inventory to retrieve"),
        db: Session = Depends(get_db)
    ):
        """
        Retrieves the current inventory status for a single product by its ID.
        """
        # First check if product exists to give a clearer error message
        db_product = crud.get_product(db, product_id=product_id)
        if not db_product:
             raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found.")

        db_inventory = crud.get_inventory(db, product_id=product_id)
        if db_inventory is None:
             # This case implies an inconsistency if product exists but inventory doesn't
             # Log this situation as it might indicate a problem
             print(f"WARNING: Product ID {product_id} exists but has no inventory record.")
             raise HTTPException(status_code=404, detail=f"Inventory record for product ID {product_id} not found (data inconsistency?).")
        return db_inventory


    # --- Endpoint to Update Inventory for a Specific Product ---
@router.put("/{product_id}", response_model=schemas.Inventory)
def update_product_inventory_endpoint( # Renamed endpoint function
        product_id: int = Path(..., gt=0, description="The ID of the product whose inventory to update"),
        inventory_update: schemas.InventoryUpdate = Body(..., embed=True, description="Inventory fields to update (quantity and/or low_stock_threshold)"),
        db: Session = Depends(get_db)
    ):
        """
        Updates the inventory details (quantity, low stock threshold) for a specific product.
        Provide only the fields you want to change.
        """
        # Check product exists first
        db_product = crud.get_product(db, product_id=product_id)
        if not db_product:
             raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found.")

        # Ensure at least one field is being updated
        if not inventory_update.model_dump(exclude_unset=True):
             raise HTTPException(status_code=400, detail="No update data provided.")

        updated_inventory = crud.update_inventory(db=db, product_id=product_id, inventory_update=inventory_update)

        if updated_inventory is None:
            # This could happen if the inventory record somehow didn't exist, despite product existing
            print(f"WARNING: update_inventory CRUD returned None for existing product ID {product_id}.")
            raise HTTPException(status_code=404, detail=f"Inventory for product ID {product_id} could not be updated (possibly missing record).")

        return updated_inventory
