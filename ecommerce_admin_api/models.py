from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), index=True, nullable=False, unique=True)
    description = Column(String(1000), nullable=True)
    category = Column(String(100), index=True, nullable=True)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('price >= 0', name='check_product_price_positive'),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=False, default=10)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="inventory")

    __table_args__ = (
        CheckConstraint('quantity >= 0', name='check_inventory_quantity_non_negative'),
        CheckConstraint('low_stock_threshold >= 0', name='check_low_stock_threshold_non_negative'),
    )

    def __repr__(self):
        return f"<Inventory(product_id={self.product_id}, quantity={self.quantity})>"


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity_sold = Column(Integer, nullable=False)
    sale_price_per_unit = Column(Float, nullable=False)
    total_revenue = Column(Float, nullable=False)
    sale_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    product = relationship("Product", back_populates="sales")

    __table_args__ = (
        CheckConstraint('quantity_sold > 0', name='check_sale_quantity_positive'),
        CheckConstraint('sale_price_per_unit >= 0', name='check_sale_price_non_negative'),
        CheckConstraint('total_revenue >= 0', name='check_total_revenue_non_negative'),
        Index('ix_sale_product_date', 'product_id', 'sale_date'),
    )

    def __repr__(self):
        return f"<Sale(id={self.id}, product_id={self.product_id}, quantity={self.quantity_sold}, date={self.sale_date})>"
