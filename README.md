# Bike Store Manager

A mobile-friendly web application for managing bike spare parts store operations, including inventory, customers, orders, and invoicing.

## Features
- **Product Management**: CRUD operations for products with Brand, Category, Pricing, etc.
- **CRM**: Manage customer details including map location, GST, and type.
- **Order Management**: Create quotations/orders with multiple line items, tax calculations, and delivery charges.
- **Invoicing**: Generate print-friendly invoices.
- **PostgreSQL Database**: Robust data storage.

## Setup

### Prerequisites
- Python 3.8+
- PostgreSQL
- pip

### 1. Database Setup
Create a PostgreSQL database named `bike_store`. You can do this via the command line or a GUI tool like pgAdmin.

```bash
createdb bike_store
```

If `createdb` is not available, log in to `psql` and run:
```sql
CREATE DATABASE bike_store;
```

### 2. Install Dependencies
Navigate to the project directory and install the required Python packages.

```bash
pip install -r requirements.txt
```

### 3. Configuration
The application connects to `postgresql://localhost/bike_store` by default. 
If your database requires a username/password or is hosted elsewhere, set the `DATABASE_URL` environment variable.

**Example:**
```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/bike_store"
```

### 4. Run the Application
Start the Flask server.

```bash
python app.py
```

The application will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Usage
- **Add Products**: Go to "Products" to add your inventory items.
- **Add Customers**: Go to "Customers" to add customer details.
- **Create Order**: Go to "Orders" -> "New Order". Select a customer and add products by searching for Item Code or Brand.
- **Invoice**: After creating an order, you will be redirected to the invoice page which can be printed or saved as PDF.
