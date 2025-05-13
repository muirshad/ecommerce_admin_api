from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class BaseConfig:
    model_config = ConfigDict(from_attributes=True)


class InventoryBase(BaseModel):
    quantity: int = Field(..., ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)


class Inventory(InventoryBase):
    id: int
    product_id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=100)
    price: float = Field(..., gt=0)


class ProductCreate(ProductBase):
    initial_quantity: int = Field(..., ge=0)
    low_stock_threshold: Optional[int] = Field(10, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=100)
    price: Optional[float] = Field(None, gt=0)


class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    inventory: Optional[Inventory] = None
    model_config = ConfigDict(from_attributes=True)


class SaleBase(BaseModel):
    product_id: int
    quantity_sold: int = Field(..., gt=0)


class SaleCreate(SaleBase):
    pass


class Sale(SaleBase):
    id: int
    sale_price_per_unit: float
    total_revenue: float
    sale_date: datetime
    model_config = ConfigDict(from_attributes=True)


class RevenueSummary(BaseModel):
    period: str
    start_date: datetime
    end_date: datetime
    total_revenue: float


class RevenueComparisonRequest(BaseModel):
    period1_start: datetime
    period1_end: datetime
    period2_start: datetime
    period2_end: datetime
    category: Optional[str] = None


class RevenueComparisonResponse(BaseModel):
    period1_revenue: float
    period2_revenue: float
    difference: float
    percentage_change: Optional[float] = None
    category: Optional[str] = None
