from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

product_bike_association = db.Table('product_bike_association',
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True),
    db.Column('bike_id', db.Integer, db.ForeignKey('bikes.id'), primary_key=True)
)

class Bike(db.Model):
    __tablename__ = 'bikes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    brand = db.Column(db.String)
    model = db.Column(db.String)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String, nullable=False)
    brand = db.Column(db.String, nullable=False)
    brand_type = db.Column(db.String)
    compatible_bikes = db.relationship('Bike', secondary=product_bike_association, backref=db.backref('products', lazy=True))
    item_name = db.Column(db.String, nullable=False)
    also_known_as = db.Column(db.String)
    oem_part_no = db.Column(db.String)
    item_code = db.Column(db.String, nullable=False)
    list_price = db.Column(db.Float)
    mrp = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    sale_price = db.Column(db.Float, nullable=True)
    pack_size = db.Column(db.String)
    hsn_code = db.Column(db.String)
    description = db.Column(db.String)
    is_archived = db.Column(db.Boolean, default=False)

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String)
    city = db.Column(db.String)
    state = db.Column(db.String)
    pincode = db.Column(db.String)
    map_location = db.Column(db.String)
    street = db.Column(db.String)
    owner_name = db.Column(db.String)
    contact_type = db.Column(db.String)
    customer_type = db.Column(db.String)
    customer_size = db.Column(db.String)
    gst = db.Column(db.String)
    is_archived = db.Column(db.Boolean, default=False)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String, unique=True, nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    order_date = db.Column(db.String)
    delivery_charges = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float)
    status = db.Column(db.String, default='Draft')
    
    customer = db.relationship('Customer', backref='orders')
    items = db.relationship('OrderItem', backref='order', cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer)
    unit_price = db.Column(db.Float)
    tax_amount = db.Column(db.Float)
    line_total = db.Column(db.Float)
    
    product = db.relationship('Product')
