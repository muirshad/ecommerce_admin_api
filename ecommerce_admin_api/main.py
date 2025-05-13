import logging # Use standard logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError # To catch DB connection errors

    # Import database setup functions and models
import models
import database # Contains Base, engine, SessionLocal, get_db
from database import engine, get_db

    # Import API routers from the routers directory
from routers import products, inventory, sales

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


    # --- Database Initialization ---
    # Create database tables based on models defined in models.py
    # This should ideally be handled by a migration tool like Alembic in production,
    # but for simplicity, we create them here if they don't exist.
def initialize_database():
        try:
            logger.info("Attempting to connect to database and check/create tables...")
            # Test connection before creating tables
            with engine.connect() as connection:
                 logger.info("Database connection successful.")
            # Create tables
            models.Base.metadata.create_all(bind=engine)
            logger.info("Database tables checked/created successfully.")
        except OperationalError as e:
            logger.error(f"FATAL: Database connection failed: {e}")
            logger.error(f"Please ensure the database server is running, the database '{engine.url.database}' exists, and connection details in .env are correct.")
            # Exit if DB connection fails on startup, essential for the app to function
            exit(1)
        except Exception as e:
            logger.error(f"An unexpected error occurred during database initialization: {e}", exc_info=True)
            # Depending on the error, you might want to exit or just log it.
            # Exiting might be safer if the state is uncertain.
            exit(1)

    # Call initialization function
initialize_database()


    # --- FastAPI Application Instance ---
app = FastAPI(
        title="E-commerce Admin API",
        description="API for managing products, inventory, and sales data for an e-commerce admin dashboard. Uses FastAPI, SQLAlchemy, and MySQL.",
        version="1.0.1", # Increment version
        # Add OpenAPI tags metadata for better organization in docs
        openapi_tags=[
            {"name": "Root", "description": "API Root and Health Check"},
            {"name": "Products", "description": "Operations related to products."},
            {"name": "Inventory", "description": "Operations related to product inventory."},
            {"name": "Sales & Revenue", "description": "Operations related to sales records and revenue analysis."},
        ],
        contact={
            "name": "API Support",
            "email": "dev@example.com", # Placeholder email
        },
        license_info={
            "name": "MIT License", # Example license
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    # --- Include Routers ---
    # Add the routers defined in separate files to the main application
    # These routers contain the specific API endpoints (/products, /inventory, /sales)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(sales.router)

    # --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
        """
        Root endpoint providing basic information about the API.
        """
        logger.info("Root endpoint '/' accessed.")
        return {
            "message": "Welcome to the E-commerce Admin API!",
            "version": app.version,
            "documentation_url": app.docs_url, # Use FastAPI's built-in property
            "redoc_url": app.redoc_url,
        }

    # --- Global Exception Handler Example ---
    # Catching specific exceptions globally can be useful for standardization
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
        # Log the HTTP exception details
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} for request {request.method} {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

@app.exception_handler(Exception) # Catch any other unhandled exceptions
async def generic_exception_handler(request: Request, exc: Exception):
        # Log the full traceback for unexpected errors
        logger.error(f"Unhandled exception for request {request.method} {request.url}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected internal server error occurred."},
        )

    # --- Health Check Endpoint ---
@app.get("/health", tags=["Root"]) # Changed tag to Root for grouping
async def health_check(db: Session = Depends(get_db)):
        """
        Simple health check endpoint to verify API and database connectivity.
        Returns status 'ok' if database connection is working.
        """
        try:
            # Perform a simple query to check DB connection liveness
            # Using `SELECT 1` is a common lightweight check
            db.execute(models.Product.__table__.select().limit(1)) # Keep existing check
            # or use: db.execute(text("SELECT 1")) # Requires `from sqlalchemy import text`
            logger.info("Health check successful.")
            return {"status": "ok", "database_status": "connected"}
        except OperationalError as db_err:
            logger.error(f"Health check failed: Database connection error - {db_err}")
            raise HTTPException(status_code=503, detail="Database connection error") # 503 Service Unavailable
        except Exception as e:
            logger.error(f"Health check failed: Unexpected error - {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Health check failed due to an internal error.")


    # --- Running the App (for development) ---
    # This block allows running the app directly using `python main.py`
    # For production, use a proper ASGI server like Uvicorn or Hypercorn directly.
    # Example: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
if __name__ == "__main__":
        import uvicorn
        logger.info("Starting Uvicorn development server...")
        # Host 0.0.0.0 makes it accessible on the network, 127.0.0.1 is local only
        # Reload=True watches for code changes, disable in production
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, log_level="info")
    