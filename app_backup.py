from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_migrate import Migrate
import json
from datetime import datetime
from config import DB_URL
from models import db, Product, Customer, Order, OrderItem, Bike
import csv
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# Remove old init_db since Flask-Migrate will handle schema creation via upgrades.
# However, for first run convenience, we can use db.create_all() inside app context,
# but usually migrations are preferred.

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

# Product API
@app.route('/api/products', methods=['GET', 'POST'])
def handle_products():
    if request.method == 'POST':
        data = request.json
        try:
            new_product = Product(
                brand=data['brand'],
                item_code=data['item_code'],
                pack_size=data.get('pack_size'),
                category=data['category'],
                mrp=float(data.get('mrp', 0)),
                cost=float(data.get('cost_price', 0)),
                brand_type=data.get('brand_type'),
                item_name=data.get('item_name', ''),
                also_known_as=data.get('also_known_as'),
                oem_part_no=data.get('oem_part_no'),
                list_price=float(data.get('list_price', 0)) if data.get('list_price') else None,
                hsn_code=data.get('hsn_code'),
                description=data.get('description')
            )
            
            # Handle compatible bikes
            if 'compatible_bikes' in data:
                for bike_name in data['compatible_bikes']:
                    bike = Bike.query.filter_by(name=bike_name).first()
                    if not bike:
                        bike = Bike(name=bike_name, model=bike_name)
                        db.session.add(bike)
                    new_product.compatible_bikes.append(bike)

            db.session.add(new_product)
            db.session.commit()
            return jsonify({'id': new_product.id, 'message': 'Product added successfully'}), 201
        except Exception as e:
            db.session.rollback()
            print(f"Error adding product: {str(e)}")
            return jsonify({'error': str(e)}), 400
    
    else:
        products = Product.query.order_by(Product.id.desc()).all()
        products_list = []
        for p in products:
            p_dict = {
                'id': p.id, 
                'brand': p.brand, 
                'item_code': p.item_code,
                'pack_size': p.pack_size, 
                'category': p.category,
                'mrp': p.mrp,
                'cost_price': p.cost, # Map cost to cost_price for frontend
                'sale_price': p.mrp, # Map mrp to sale_price for frontend if sale_price is missing
                'brand_type': p.brand_type,
                'item_name': p.item_name,
                'also_known_as': p.also_known_as,
                'oem_part_no': p.oem_part_no,
                'list_price': p.list_price,
                'hsn_code': p.hsn_code,
                'description': p.description,
                'compatible_bikes': [b.name for b in p.compatible_bikes]
            }
            products_list.append(p_dict)
        return jsonify(products_list)


@app.route('/api/products/<int:id>', methods=['PUT', 'DELETE'])
def manage_product(id):
    product = Product.query.get_or_404(id)

    if request.method == 'DELETE':
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted'})
    
    elif request.method == 'PUT':
        data = request.json
        product.brand = data['brand']
        product.item_code = data['item_code']
        product.pack_size = data.get('pack_size')
        product.category = data['category']
        product.cost = float(data.get('cost_price', 0))
        product.mrp = float(data.get('mrp', 0))
        product.brand_type = data.get('brand_type')
        product.item_name = data.get('item_name', product.item_name)
        product.also_known_as = data.get('also_known_as')
        product.oem_part_no = data.get('oem_part_no')
        product.list_price = float(data.get('list_price', 0)) if data.get('list_price') else None
        product.hsn_code = data.get('hsn_code')
        product.description = data.get('description')

        # Handle compatible bikes
        if 'compatible_bikes' in data:
            product.compatible_bikes = [] # Clear existing
            for bike_name in data['compatible_bikes']:
                bike = Bike.query.filter_by(name=bike_name).first()
                if not bike:
                    bike = Bike(name=bike_name, model=bike_name)
                    db.session.add(bike)
                product.compatible_bikes.append(bike)
        
        db.session.commit()
        return jsonify({'message': 'Product updated'})



# Customer API
@app.route('/api/customers', methods=['GET', 'POST'])
def handle_customers():
    if request.method == 'POST':
        data = request.json
        try:
            new_customer = Customer(
                name=data['name'],
                phone=data.get('phone'),
                city=data.get('city'),
                state=data.get('state'),
                pincode=data.get('pincode'),
                map_location=data.get('map_location'),
                street=data.get('street'),
                owner_name=data.get('owner_name'),
                contact_type=data.get('contact_type'),
                customer_type=data.get('customer_type'),
                customer_size=data.get('customer_size'),
                gst=data.get('gst')
            )
            db.session.add(new_customer)
            db.session.commit()
            return jsonify({'id': new_customer.id, 'message': 'Customer added successfully'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    else:
        customers = Customer.query.order_by(Customer.name.asc()).all()
        customers_list = []
        for c in customers:
            customers_list.append({
                'id': c.id, 'name': c.name, 'phone': c.phone,
                'city': c.city, 'state': c.state, 'pincode': c.pincode,
                'map_location': c.map_location, 'street': c.street,
                'owner_name': c.owner_name, 'contact_type': c.contact_type,
                'customer_type': c.customer_type, 'customer_size': c.customer_size,
                'gst': c.gst
            })
        return jsonify(customers_list)

@app.route('/api/customers/<int:id>', methods=['PUT', 'DELETE'])
def manage_customer(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'DELETE':
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'message': 'Customer deleted'})
    elif request.method == 'PUT':
        data = request.json
        customer.name = data['name']
        customer.phone = data.get('phone')
        customer.city = data.get('city')
        customer.state = data.get('state')
        customer.pincode = data.get('pincode')
        customer.map_location = data.get('map_location')
        customer.street = data.get('street')
        customer.owner_name = data.get('owner_name')
        customer.contact_type = data.get('contact_type')
        customer.customer_type = data.get('customer_type')
        customer.customer_size = data.get('customer_size')
        customer.gst = data.get('gst')

        db.session.commit()
        return jsonify({'message': 'Customer updated'})

# Order API
@app.route('/api/orders', methods=['GET', 'POST'])
def handle_orders():
    if request.method == 'POST':
        data = request.json
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # Create Order
            new_order = Order(
                customer_id=data['customer_id'],
                order_date=now,
                delivery_charges=float(data.get('delivery_charges', 0)),
                total_amount=float(data['total_amount']),
                status='Draft'
            )
            db.session.add(new_order)
            db.session.flush() # flush to get ID
            
            # Create Line Items
            for item in data['items']:
                order_item = OrderItem(
                    order_id=new_order.id,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    unit_price=float(item['unit_price']),
                    tax_amount=float(item['tax_amount']),
                    line_total=float(item['line_total'])
                )
                db.session.add(order_item)
            
            db.session.commit()
            return jsonify({'id': new_order.id, 'message': 'Order created successfully'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    else:
        # Get orders with customer details
        orders = Order.query.order_by(Order.id.desc()).all()
        orders_list = []
        for o in orders:
            o_dict = {
                'id': o.id, 'customer_id': o.customer_id, 'order_date': o.order_date,
                'delivery_charges': o.delivery_charges, 'total_amount': o.total_amount, 'status': o.status,
                'customer_name': o.customer.name if o.customer else None
            }
            orders_list.append(o_dict)
        return jsonify(orders_list)

@app.route('/api/orders/<int:id>', methods=['GET'])
def get_order(id):
    order = Order.query.get_or_404(id)
    
    order_dict = {
        'id': order.id, 'customer_id': order.customer_id, 'order_date': order.order_date,
        'delivery_charges': order.delivery_charges, 'total_amount': order.total_amount, 'status': order.status,
        'customer_name': order.customer.name if order.customer else None,
        'phone': order.customer.phone if order.customer else None,
        'city': order.customer.city if order.customer else None,
        'gst': order.customer.gst if order.customer else None
    }
    
    items_list = []
    for item in order.items:
        i_dict = {
            'id': item.id, 'order_id': item.order_id, 'product_id': item.product_id,
            'quantity': item.quantity, 'unit_price': item.unit_price,
            'tax_amount': item.tax_amount, 'line_total': item.line_total,
            'item_code': item.product.item_code if item.product else None,
            'brand': item.product.brand if item.product else None,
            'pack_size': item.product.pack_size if item.product else None
        }
        items_list.append(i_dict)
    
    order_dict['items'] = items_list
    return jsonify(order_dict)

@app.route('/api/orders/<int:id>/status', methods=['PUT'])
def update_order_status(id):
    order = Order.query.get_or_404(id)
    status = request.json.get('status')
    order.status = status
    db.session.commit()
    return jsonify({'message': 'Status updated'})

# Route to archive/unarchive a product
@app.route('/api/products/<int:product_id>/archive', methods=['PUT'])
def archive_product(product_id):
    data = request.json
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    product.is_archived = data.get('is_archived', True)
    db.session.commit()
    return jsonify({'message': 'Product updated successfully'})

# Route to archive/unarchive a customer
@app.route('/api/customers/<int:customer_id>/archive', methods=['PUT'])
def archive_customer(customer_id):
    data = request.json
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    customer.is_archived = data.get('is_archived', True)
    db.session.commit()
    return jsonify({'message': 'Customer updated successfully'})

# Bulk upload route
@app.route('/api/upload', methods=['POST'])
def bulk_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            with open(filepath, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Map CSV columns to database fields
                    new_product = Product(
                        brand=row.get('brand'),
                        item_code=row.get('item_code'),
                        pack_size=row.get('pack_size'),
                        category=row.get('category'),
                        sale_price=float(row.get('sale_price', 0)),
                        cost_price=float(row.get('cost_price', 0)),
                        tax_rate=float(row.get('tax_rate', 0)),
                        mrp=float(row.get('mrp', 0))
                    )
                    db.session.add(new_product)
                db.session.commit()
            return jsonify({'message': 'Bulk upload successful'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({'error': 'Invalid file type'}), 400

# Route to handle bulk product uploads
@app.route('/api/products/bulk_upload', methods=['POST'])
def bulk_upload_products():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Please upload a CSV file.'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                product_id = row.get('id')
                if product_id:
                    # Update existing product
                    product = Product.query.get(product_id)
                    if product:
                        product.brand = row.get('brand', product.brand)
                        product.item_code = row.get('item_code', product.item_code)
                        product.pack_size = row.get('pack_size', product.pack_size)
                        product.category = row.get('category', product.category)
                        product.sale_price = float(row.get('sale_price', product.sale_price))
                        product.cost_price = float(row.get('cost_price', product.cost_price))
                        product.tax_rate = float(row.get('tax_rate', product.tax_rate))
                        product.mrp = float(row.get('mrp', product.mrp))
                    else:
                        return jsonify({'error': f'Product with ID {product_id} not found.'}), 404
                else:
                    # Create new product
                    new_product = Product(
                        brand=row['brand'],
                        item_code=row['item_code'],
                        pack_size=row.get('pack_size'),
                        category=row['category'],
                        sale_price=float(row['sale_price']),
                        cost_price=float(row['cost_price']),
                        tax_rate=float(row.get('tax_rate', 18.0)),
                        mrp=float(row['mrp'])
                    )
                    db.session.add(new_product)

            db.session.commit()
        return jsonify({'message': 'Products uploaded successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    return jsonify({'error': 'Invalid file type'}), 400

# --- UI Routes ---

@app.route('/products')
def products_page():
    with open('config/brands.json', 'r') as f:
        brands = json.load(f)
    with open('config/category.json', 'r') as f:
        categories = json.load(f)
    return render_template('products.html', brands=brands, categories=categories)

@app.route('/customers')
def customers_page():
    return render_template('customers.html')

@app.route('/orders')
def orders_page():
    return render_template('orders.html')

@app.route('/orders/create')
def create_order_page():
    return render_template('order_form.html')

@app.route('/orders/<int:id>')
def view_order_page(id):
    order = Order.query.get_or_404(id)
    
    # Prepare order dict manually to match template expectations
    order_data = {
         'id': order.id, 'customer_id': order.customer_id, 'order_date': order.order_date,
         'delivery_charges': order.delivery_charges, 'total_amount': order.total_amount, 'status': order.status,
         'name': order.customer.name if order.customer else '',
         'phone': order.customer.phone if order.customer else '',
         'street': order.customer.street if order.customer else '',
         'city': order.customer.city if order.customer else '',
         'state': order.customer.state if order.customer else '',
         'pincode': order.customer.pincode if order.customer else '',
         'gst': order.customer.gst if order.customer else ''
    }
    
    # Convert date string to datetime object for Jinja filter if needed
    try:
        if isinstance(order_data['order_date'], str):
             order_data['order_date'] = datetime.strptime(order_data['order_date'], "%Y-%m-%d %H:%M:%S")
    except:
        pass 
        
    items_data = []
    for item in order.items:
        items_data.append({
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'tax_amount': item.tax_amount,
            'line_total': item.line_total,
            'item_code': item.product.item_code if item.product else '',
            'brand': item.product.brand if item.product else '',
            'pack_size': item.product.pack_size if item.product else '',
            'category': item.product.category if item.product else ''
        })
    
    return render_template('invoice.html', order=order_data, items=items_data)


@app.route('/api/bikes', methods=['GET'])
def get_bikes():
    bikes = Bike.query.order_by(Bike.brand, Bike.name).all()
    grouped_bikes = {}
    
    # Group bikes by brand
    for bike in bikes:
        # Some bikes might not have a brand, handle gracefully
        brand = bike.brand if bike.brand else "Other"
        
        if brand not in grouped_bikes:
            grouped_bikes[brand] = []
        
        # Use bike.name as the value
        grouped_bikes[brand].append(bike.name)
            
    return jsonify(grouped_bikes)


if __name__ == '__main__':
    app.run(debug=True, port=8000)
