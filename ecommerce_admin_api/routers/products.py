from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, Response
from sqlalchemy.orm import Session
from typing import List, Optional

import crud
import schemas
from database import get_db

    # Create an API router instance
router = APIRouter(
        prefix="/products", # All routes in this file will start with /products
        tags=["Products"], # Tag for grouping in API docs
        responses={404: {"description": "Product not found"}}, # Default response for not found
    )

    # --- Endpoint to Create a New Product ---
@router.post("/", response_model=schemas.Product, status_code=201) # Use 201 Created status
def create_product_endpoint( # Renamed to avoid conflict with crud function name
        product: schemas.ProductCreate = Body(..., embed=True, description="Product details including initial inventory"),
        db: Session = Depends(get_db)
    ):
        """
        Registers a new product along with its initial inventory level.

        - **name**: The name of the product (must be unique).
        - **description**: Optional description.
        - **category**: Optional category.
        - **price**: The selling price (must be > 0).
        - **initial_quantity**: The starting stock quantity (must be >= 0).
        - **low_stock_threshold**: Optional threshold for low stock alerts (default 10).
        """
        # Check for existing product by name first
        db_product_check = crud.get_product_by_name(db, name=product.name)
        if db_product_check:
            raise HTTPException(status_code=400, detail=f"Product name '{product.name}' already registered.")

        try:
            created_product = crud.create_product(db=db, product=product)
            # The crud function should return the created product with inventory attached
            if created_product is None:
                 # This might happen if the name check fails due to race condition
                 raise HTTPException(status_code=400, detail="Product could not be created (possibly duplicate name).")
            # Ensure inventory is loaded for the response model (Pydantic's from_attributes should handle this)
            return created_product
        except ValueError as e: # Catch potential errors from CRUD
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Log the exception e here in a real application
            print(f"Error in create_product_endpoint: {e}") # Basic logging
            raise HTTPException(status_code=500, detail="An internal error occurred during product creation.")


    # --- Endpoint to Get a List of Products ---
@router.get("/", response_model=List[schemas.Product])
def read_products_endpoint( # Renamed endpoint function
        skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
        limit: int = Query(100, ge=1, le=200, description="Maximum number of records to return"), # Added limits
        category: Optional[str] = Query(None, description="Filter products by category (case-insensitive)"),
        db: Session = Depends(get_db)
    ):
        """
        Retrieves a list of products, supporting pagination and category filtering.
        Includes inventory details for each product.
        """
        products = crud.get_products(db, skip=skip, limit=limit, category=category)
        # Pydantic's from_attributes=True in schemas.Product should automatically handle
        # loading the 'inventory' relationship if it's available on the product objects.
        # If eager loading wasn't used in CRUD, this might trigger N+1 queries.
        # Consider adding eager loading in crud.get_products for performance.
        return products


    # --- Endpoint to Get a Specific Product by ID ---
@router.get("/{product_id}", response_model=schemas.Product)
def read_product_endpoint( # Renamed endpoint function
        product_id: int = Path(..., gt=0, description="The ID of the product to retrieve"), # Use Path for path parameters
        db: Session = Depends(get_db)
    ):
        """
        Retrieves details for a specific product by its unique ID.
        Includes inventory details.
        """
        db_product = crud.get_product(db, product_id=product_id)
        if db_product is None:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
        # Again, assume Pydantic handles loading inventory relationship
        return db_product


    # --- Endpoint to Update a Product ---
@router.put("/{product_id}", response_model=schemas.Product)
def update_product_endpoint( # Renamed endpoint function
        product_id: int = Path(..., gt=0, description="The ID of the product to update"),
        product_update: schemas.ProductUpdate = Body(..., embed=True, description="Fields to update for the product"),
        db: Session = Depends(get_db)
    ):
        """
        Updates the details of an existing product.
        Only provide the fields you want to change.
        Cannot update inventory details here; use the inventory endpoints for that.
        """
        # Check if product exists first
        db_product_check = crud.get_product(db, product_id=product_id)
        if db_product_check is None:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

        # Ensure at least one field is being updated
        if not product_update.model_dump(exclude_unset=True):
             raise HTTPException(status_code=400, detail="No update data provided.")

        try:
            updated_product = crud.update_product(db=db, product_id=product_id, product_update=product_update)
            # CRUD function returns the updated product, Pydantic handles response
            return updated_product
        except ValueError as e: # Catch specific errors like duplicate name
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Log error e
            print(f"Error in update_product_endpoint: {e}") # Basic logging
            raise HTTPException(status_code=500, detail="An internal error occurred during product update.")


@router.delete("/{product_id}", status_code=204)
def delete_product_endpoint( # Renamed endpoint function
        product_id: int = Path(..., gt=0, description="The ID of the product to delete"),
        db: Session = Depends(get_db)
    ):
        """
        Deletes a product and its associated inventory and sales records (due to cascading).
        This operation is permanent.
        Returns HTTP 204 No Content on success.
        """
        deleted_product = crud.delete_product(db=db, product_id=product_id)
        if deleted_product is None:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
        
        return Response(status_code=204)
    