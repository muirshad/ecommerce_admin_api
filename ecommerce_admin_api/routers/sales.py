
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta, time # Import time for combine

import crud
import schemas
from database import get_db

router = APIRouter(
        prefix="/sales", # All routes start with /sales
        tags=["Sales & Revenue"], # Tag for API docs
        responses={404: {"description": "Resource not found"}}, # More generic 404
    )

@router.post("/", response_model=schemas.Sale, status_code=201)
def record_sale_endpoint( # Renamed endpoint function
        sale: schemas.SaleCreate = Body(..., embed=True, description="Details of the sale to record"),
        db: Session = Depends(get_db)
    ):
        """
        Records a new sale transaction.
        This will automatically decrease the inventory count for the sold product.
        The sale price is recorded based on the product's current price at the time of the sale.

        - **product_id**: The ID of the product being sold.
        - **quantity_sold**: The number of units sold (must be > 0).
        """
        try:
            created_sale = crud.create_sale(db=db, sale=sale)
            return created_sale
        except ValueError as e:
            if "not found" in str(e):
                 raise HTTPException(status_code=404, detail=str(e))
            else:
                 raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Log error e
            print(f"Error in record_sale_endpoint: {e}") # Basic logging
            raise HTTPException(status_code=500, detail="An internal error occurred while recording the sale.")

@router.get("/", response_model=List[schemas.Sale])
def read_sales_endpoint( # Renamed endpoint function
        skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
        limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"), # Allow more sales records
        start_date: Optional[date] = Query(None, description="Filter sales from this date (YYYY-MM-DD)"),
        end_date: Optional[date] = Query(None, description="Filter sales up to this date (YYYY-MM-DD)"),
        product_id: Optional[int] = Query(None, gt=0, description="Filter sales by product ID"),
        category: Optional[str] = Query(None, description="Filter sales by product category (case-insensitive)"),
        db: Session = Depends(get_db)
    ):
        """
        Retrieves a list of sales records, supporting pagination and filtering.
        Filters can be applied by date range, product ID, and product category.
        """
        start_datetime: Optional[datetime] = None
        end_datetime: Optional[datetime] = None
        if start_date:
            start_datetime = datetime.combine(start_date, time.min) # Start of the day
        if end_date:
            end_datetime = datetime.combine(end_date, time.max) # End of the day 23:59:59.999999

        if start_datetime and end_datetime and start_datetime > end_datetime:
             raise HTTPException(status_code=400, detail="Start date cannot be after end date.")

        sales = crud.get_sales(
            db, skip=skip, limit=limit,
            start_date=start_datetime, end_date=end_datetime,
            product_id=product_id, category=category
        )
        return sales

@router.get("/revenue/summary", response_model=schemas.RevenueSummary)
def get_revenue_summary_endpoint( # Renamed endpoint function
        start_date: date = Query(..., description="Start date for revenue calculation (YYYY-MM-DD)"),
        end_date: date = Query(..., description="End date for revenue calculation (YYYY-MM-DD)"),
        product_id: Optional[int] = Query(None, gt=0, description="Optional: Filter revenue by product ID"),
        category: Optional[str] = Query(None, description="Optional: Filter revenue by product category"),
        db: Session = Depends(get_db)
    ):
        """
        Calculates the total revenue generated within a specified date range.
        Optionally filters by product ID or category.
        """
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date cannot be after end date.")

        start_datetime = datetime.combine(start_date, time.min)
        end_datetime = datetime.combine(end_date, time.max)

        total_revenue = crud.get_revenue_summary(
            db, start_date=start_datetime, end_date=end_datetime,
            product_id=product_id, category=category
        )

        return schemas.RevenueSummary(
            period="custom", # Indicate it's a custom range based on query params
            start_date=start_datetime,
            end_date=end_datetime,
            total_revenue=total_revenue
        )


@router.get("/revenue/analysis", response_model=List[schemas.RevenueSummary])
def get_revenue_analysis_endpoint( # Renamed endpoint function
        period: str = Query(..., pattern="^(day|week|month|year)$", description="Group revenue by 'day', 'week', 'month', or 'year'"),
        start_date: date = Query(..., description="Start date for analysis (YYYY-MM-DD)"),
        end_date: date = Query(..., description="End date for analysis (YYYY-MM-DD)"),
        db: Session = Depends(get_db)
    ):
        """
        Analyzes revenue over a specified date range, grouped by day, week, month, or year.
        Returns a list of revenue summaries for each period within the range.
        """
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date cannot be after end date.")

        start_datetime = datetime.combine(start_date, time.min)
        end_datetime = datetime.combine(end_date, time.max)

        try:
            revenue_data = crud.get_revenue_by_period(db, period=period, start_date=start_datetime, end_date=end_datetime)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) # Catch invalid period error
        except Exception as e:
            print(f"Error in get_revenue_analysis_endpoint: {e}") # Basic logging
            raise HTTPException(status_code=500, detail="Error during revenue analysis.")


        results = []
        for period_start_dt, revenue in revenue_data:
            period_end_dt = period_start_dt # Start with the beginning

            if period == 'day':
                period_end_dt = period_start_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == 'week':
                 period_end_dt = (period_start_dt + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == 'month':
                next_month_start = (period_start_dt.replace(day=1) + timedelta(days=32)).replace(day=1)
                period_end_dt = next_month_start - timedelta(microseconds=1)
            elif period == 'year':
                next_year_start = period_start_dt.replace(year=period_start_dt.year + 1, month=1, day=1)
                period_end_dt = next_year_start - timedelta(microseconds=1)

            actual_end_dt = min(period_end_dt, end_datetime)

            results.append(schemas.RevenueSummary(
                period=period,
                start_date=period_start_dt,
                end_date=actual_end_dt,
                total_revenue=revenue
            ))

        return results


@router.post("/revenue/comparison", response_model=schemas.RevenueComparisonResponse)
def compare_revenue_endpoint( # Renamed endpoint function
        request: schemas.RevenueComparisonRequest = Body(..., description="Details of the two periods to compare (use full datetime strings like 'YYYY-MM-DDTHH:MM:SS')"),
        db: Session = Depends(get_db)
    ):
        """
        Compares total revenue between two specified datetime periods.
        Optionally filters by a specific product category for the comparison.
        Requires precise start/end datetimes in the request body.
        """
        if request.period1_start >= request.period1_end or request.period2_start >= request.period2_end:
            raise HTTPException(status_code=400, detail="Start datetime must be before end datetime in each period.")

        try:
            revenue1 = crud.get_revenue_summary(
                db, start_date=request.period1_start, end_date=request.period1_end,
                category=request.category
            )
            revenue2 = crud.get_revenue_summary(
                db, start_date=request.period2_start, end_date=request.period2_end,
                category=request.category
            )
        except Exception as e:
             print(f"Error during revenue comparison calculation: {e}")
             raise HTTPException(status_code=500, detail="Error calculating revenue for comparison.")


        
        difference = revenue2 - revenue1
        percentage_change = None
        if revenue1 != 0:
            try:
                percentage_change = (difference / revenue1) * 100
            except ZeroDivisionError:
                percentage_change = float('inf') if difference > 0 else float('-inf') if difference < 0 else 0.0


        return schemas.RevenueComparisonResponse(
            period1_revenue=revenue1,
            period2_revenue=revenue2,
            difference=difference,
            percentage_change=percentage_change,
            category=request.category
        )
    