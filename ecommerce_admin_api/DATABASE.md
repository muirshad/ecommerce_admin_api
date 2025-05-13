    # Database Schema Documentation (E-commerce Admin API)

    This document describes the MySQL database schema used by the E-commerce Admin API. The schema is designed using SQLAlchemy ORM models defined in `models.py` and is intended to support product management, inventory tracking, and sales analysis.

    ## Database Engine

    * **Type:** MySQL (Compatibility tested with v5.7+ and v8.0+)
    * **Character Set:** `utf8mb4`
    * **Collation:** `utf8mb4_unicode_ci` (Recommended for broad language support)

    ## Tables

    ### 1. `products`

    Stores core information about each product offered.

    | Column        | Type             | Constraints/Indexes                               | Description                                         |
    | :------------ | :--------------- | :------------------------------------------------ | :-------------------------------------------------- |
    | `id`          | `INTEGER`        | `PRIMARY KEY`, `AUTO_INCREMENT`, `INDEX`          | Unique identifier for the product.                  |
    | `name`        | `VARCHAR(255)`   | `NOT NULL`, `UNIQUE`, `INDEX`                     | Name of the product. Must be unique.                |
    | `description` | `VARCHAR(1000)`  | `NULLABLE`                                        | Detailed description of the product.                |
    | `category`    | `VARCHAR(100)`   | `NULLABLE`, `INDEX`                               | Category the product belongs to (e.g., Electronics). |
    | `price`       | `FLOAT`          | `NOT NULL`, `CHECK (price >= 0)`                  | Current selling price per unit of the product.      |
    | `created_at`  | `DATETIME(timezone=True)` | `NOT NULL`, `DEFAULT CURRENT_TIMESTAMP`           | Timestamp (UTC recommended) when the product was created. |
    | `updated_at`  | `DATETIME(timezone=True)` | `NULLABLE`, `ON UPDATE CURRENT_TIMESTAMP`       | Timestamp (UTC recommended) when the product was last updated. |

    **Relationships:**

    * **One-to-One with `inventory`:** Each product has exactly one inventory record (`products.id` <-> `inventory.product_id`). The `inventory` record is deleted if the product is deleted (cascade).
    * **One-to-Many with `sales`:** One product can be associated with many sales records (`products.id` -> `sales.product_id`). Sales records are deleted if the product is deleted (cascade).

    **Indexes:**

    * `PRIMARY` on `id` (Implicitly created)
    * `ix_products_id` on `id` (Explicit index often created by ORM)
    * `ix_products_name` on `name` (Implicitly created by `UNIQUE` constraint)
    * `ix_products_category` on `category` (For filtering by category)

    ### 2. `inventory`

    Tracks the stock levels and thresholds for each product.

    | Column              | Type      | Constraints/Indexes                                      | Description                                                |
    | :------------------ | :-------- | :------------------------------------------------------- | :--------------------------------------------------------- |
    | `id`                | `INTEGER` | `PRIMARY KEY`, `AUTO_INCREMENT`, `INDEX`                 | Unique identifier for the inventory record.                |
    | `product_id`        | `INTEGER` | `NOT NULL`, `UNIQUE`, `INDEX`, `FOREIGN KEY (products.id)` | Links to the `products` table. Ensures one inventory record per product. |
    | `quantity`          | `INTEGER` | `NOT NULL`, `DEFAULT 0`, `CHECK (quantity >= 0)`         | Current number of units in stock. Cannot be negative.      |
    | `low_stock_threshold` | `INTEGER` | `NOT NULL`, `DEFAULT 10`, `CHECK (low_stock_threshold >= 0)` | Threshold below (or equal to) which the product is considered low stock. |
    | `last_updated`      | `DATETIME(timezone=True)` | `NOT NULL`, `DEFAULT CURRENT_TIMESTAMP`, `ON UPDATE CURRENT_TIMESTAMP` | Timestamp (UTC recommended) when the inventory record was last modified (e.g., quantity change). |

    **Relationships:**

    * **One-to-One with `products`:** Links back to the product this inventory record belongs to.

    **Indexes:**

    * `PRIMARY` on `id`
    * `ix_inventory_id` on `id`
    * `ix_inventory_product_id` on `product_id` (Implicitly created by `UNIQUE`)
    * *(Consider an index on `quantity` if frequently querying low stock items across many products)*

    ### 3. `sales`

    Records each individual sales transaction event.

    | Column              | Type      | Constraints/Indexes                                      | Description                                                |
    | :------------------ | :-------- | :------------------------------------------------------- | :--------------------------------------------------------- |
    | `id`                | `INTEGER` | `PRIMARY KEY`, `AUTO_INCREMENT`, `INDEX`                 | Unique identifier for the sale record.                     |
    | `product_id`        | `INTEGER` | `NOT NULL`, `INDEX`, `FOREIGN KEY (products.id)`         | Links to the `products` table for the item that was sold.  |
    | `quantity_sold`     | `INTEGER` | `NOT NULL`, `CHECK (quantity_sold > 0)`                  | Number of units sold in this transaction. Must be positive. |
    | `sale_price_per_unit`| `FLOAT`   | `NOT NULL`, `CHECK (sale_price_per_unit >= 0)`           | Price per unit *at the time the sale occurred*. Stored to preserve historical pricing. |
    | `total_revenue`     | `FLOAT`   | `NOT NULL`, `CHECK (total_revenue >= 0)`                 | Total revenue from this transaction (`quantity_sold * sale_price_per_unit`). Stored for easy querying. |
    | `sale_date`         | `DATETIME(timezone=True)` | `NOT NULL`, `DEFAULT CURRENT_TIMESTAMP`, `INDEX` | Timestamp (UTC recommended) when the sale occurred.         |

    **Relationships:**

    * **Many-to-One with `products`:** Multiple sales records can point to the same product.

    **Indexes:**

    * `PRIMARY` on `id`
    * `ix_sales_id` on `id`
    * `ix_sales_product_id` on `product_id` (For filtering sales by product)
    * `ix_sales_sale_date` on `sale_date` (Crucial for filtering sales by date range)
    * `ix_sale_product_date` on (`product_id`, `sale_date`) (Composite index for optimizing queries filtering by both product and date)

    ## General Notes

    * **SQLAlchemy Models:** The actual table creation is handled by SQLAlchemy based on the models defined in `models.py`. Constraints like `CheckConstraint`, `ForeignKey`, `Index`, `UniqueConstraint` are defined within the Python models.
    * **Timezones:** Using `DateTime(timezone=True)` in SQLAlchemy instructs it to handle timezone-aware datetime objects. It's crucial that the database server and the Python application environment agree on timezone handling (preferably UTC) to avoid confusion. MySQL's `TIMESTAMP` type often stores in UTC and converts based on session timezone, while `DATETIME` stores literally. Check your MySQL configuration.
    * **Cascading Deletes:** Foreign key constraints in `inventory` and `sales` are configured (via SQLAlchemy's `cascade="all, delete-orphan"` option on the `relationship` in `models.py`) to automatically delete associated inventory and sales records when a product is deleted. **This is a destructive operation and should be used with caution.** Ensure appropriate authorization checks are in place before allowing product deletion via the API.
    * **Database Migrations:** For production environments or any scenario where the schema might evolve after initial deployment, using a database migration tool like **Alembic** is strongly recommended. Alembic allows for version-controlled, incremental, and reversible changes to the database schema, preventing data loss and ensuring consistency across different environments. The `Base.metadata.create_all(bind=engine)` method used in `main.py` is suitable for initial setup and development but **not** for managing updates to an existing database with data.
    