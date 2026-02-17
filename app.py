from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_migrate import Migrate
import json
from datetime import datetime
from config import DB_URL
from models import db, Product, Customer, Order, OrderItem, Bike
from sqlalchemy import or_
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
                sale_price=float(data.get('sale_price', 0)),
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



        search_query = request.args.get('search', '').strip()
        show_archived = request.args.get('show_archived', 'false').lower() == 'true'
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Column filters
        brand_filter = request.args.get('brand_filter', '').strip()
        category_filter = request.args.get('category_filter', '').strip()
        
        query = Product.query
        
        # Filter out archived products by default
        if not show_archived:
            query = query.filter(Product.is_archived == False)

        # Apply column filters
        if brand_filter:
            query = query.filter(Product.brand.ilike(f"%{brand_filter}%"))
        if category_filter:
            query = query.filter(Product.category.ilike(f"%{category_filter}%"))

        # Apply search
        if search_query:
            term = f"%{search_query}%"
            query = query.filter(or_(
                Product.item_name.ilike(term),
                Product.brand.ilike(term),
                Product.category.ilike(term),
                Product.item_code.ilike(term),
                Product.oem_part_no.ilike(term),
                Product.also_known_as.ilike(term),
                Product.description.ilike(term)
            ))
        
        # Apply sorting
        valid_sort_columns = {
            'id': Product.id,
            'brand': Product.brand,
            'category': Product.category,
            'item_name': Product.item_name,
            'mrp': Product.mrp,
            'cost': Product.cost,
            'sale_price': Product.sale_price
        }
        
        sort_column = valid_sort_columns.get(sort_by, Product.id)
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        products = pagination.items
        
        products_list = []
        for p in products:
            p_dict = {
                'id': p.id, 
                'brand': p.brand, 
                'item_code': p.item_code,
                'pack_size': p.pack_size, 
                'category': p.category,
                'mrp': p.mrp,
                'cost_price': p.cost, 
                'sale_price': p.sale_price,
                'brand_type': p.brand_type,
                'item_name': p.item_name,
                'also_known_as': p.also_known_as,
                'oem_part_no': p.oem_part_no,
                'list_price': p.list_price,
                'hsn_code': p.hsn_code,
                'description': p.description,
                'compatible_bikes': [b.name for b in p.compatible_bikes],
                'is_archived': p.is_archived
            }
            products_list.append(p_dict)
            
        return jsonify({
            'items': products_list,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page
        })


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
        product.sale_price = float(data.get('sale_price', 0))

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
        search_query = request.args.get('search', '').strip()
        show_archived = request.args.get('show_archived', 'false').lower() == 'true'
        
        query = Customer.query
        
        # Filter out archived customers by default
        if not show_archived:
            query = query.filter(Customer.is_archived == False)
        
        # Apply search
        if search_query:
            term = f"%{search_query}%"
            query = query.filter(or_(
                Customer.name.ilike(term),
                Customer.phone.ilike(term),
                Customer.city.ilike(term),
                Customer.state.ilike(term),
                Customer.street.ilike(term),
                Customer.owner_name.ilike(term),
                Customer.gst.ilike(term),
                Customer.customer_type.ilike(term)
            ))
        
        customers = query.order_by(Customer.name.asc()).all()
        customers_list = []
        for c in customers:
            customers_list.append({
                'id': c.id, 'name': c.name, 'phone': c.phone,
                'city': c.city, 'state': c.state, 'pincode': c.pincode,
                'map_location': c.map_location, 'street': c.street,
                'owner_name': c.owner_name, 'contact_type': c.contact_type,
                'customer_type': c.customer_type, 'customer_size': c.customer_size,
                'gst': c.gst, 'is_archived': c.is_archived
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
                status=data.get('status', 'Draft')
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

@app.route('/api/orders/<int:id>', methods=['GET', 'PUT'])
def manage_order(id):
    order = Order.query.get_or_404(id)
    
    if request.method == 'PUT':
        data = request.json
        try:
            order.customer_id = data.get('customer_id', order.customer_id)
            order.delivery_charges = float(data.get('delivery_charges', order.delivery_charges))
            order.total_amount = float(data.get('total_amount', order.total_amount))
            order.status = data.get('status', order.status)
            
            # If items are provided, replace them
            if 'items' in data:
                # Remove existing items
                OrderItem.query.filter_by(order_id=id).delete()
                
                # Add new items
                for item in data['items']:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item['product_id'],
                        quantity=item['quantity'],
                        unit_price=float(item['unit_price']),
                        tax_amount=float(item['tax_amount']),
                        line_total=float(item['line_total'])
                    )
                    db.session.add(order_item)
            
            db.session.commit()
            return jsonify({'id': order.id, 'message': 'Order updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    # GET logic
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
            'pack_size': item.product.pack_size if item.product else None,
            'item_name': item.product.item_name if item.product else None
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

# Route to analyze customer CSV headers
@app.route('/api/customers/analyze_upload', methods=['POST'])
def analyze_customer_upload():
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
            with open(filepath, 'r', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, [])
                
            return jsonify({
                'filename': filename,
                'headers': headers,
                'message': 'File uploaded and analyzed successfully'
            })
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Error analyzing file: {str(e)}'}), 500

    return jsonify({'error': 'Invalid file type'}), 400

# Route to handle bulk customer imports with mapping
@app.route('/api/customers/bulk_import', methods=['POST'])
def bulk_import_customers():
    data = request.json
    filename = data.get('filename')
    mapping = data.get('mapping')

    if not filename or not mapping:
        return jsonify({'error': 'Missing filename or mapping'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found. Please upload again.'}), 404

    try:
        with open(filepath, 'r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Helper to get mapped value safely
            def get_val(row, field, default=None):
                csv_col = mapping.get(field)
                if csv_col and csv_col in row:
                    val = row[csv_col]
                    return val if val.strip() != '' else default
                return default

            for row in reader:
                # Check for existing customer override if ID is mapped and present
                customer_id = get_val(row, 'id')
                
                if customer_id:
                    customer = Customer.query.get(customer_id)
                    if customer:
                        customer.name = get_val(row, 'name', customer.name)
                        customer.phone = get_val(row, 'phone', customer.phone)
                        customer.city = get_val(row, 'city', customer.city)
                        customer.state = get_val(row, 'state', customer.state)
                        customer.pincode = get_val(row, 'pincode', customer.pincode)
                        customer.map_location = get_val(row, 'map_location', customer.map_location)
                        customer.street = get_val(row, 'street', customer.street)
                        customer.owner_name = get_val(row, 'owner_name', customer.owner_name)
                        customer.contact_type = get_val(row, 'contact_type', customer.contact_type)
                        customer.customer_type = get_val(row, 'customer_type', customer.customer_type)
                        customer.customer_size = get_val(row, 'customer_size', customer.customer_size)
                        customer.gst = get_val(row, 'gst', customer.gst)
                    else:
                        # Skip if ID provided but not found
                        continue
                else:
                    # Create new customer
                    try:
                        new_customer = Customer(
                            name=get_val(row, 'name', ''),
                            phone=get_val(row, 'phone'),
                            city=get_val(row, 'city'),
                            state=get_val(row, 'state'),
                            pincode=get_val(row, 'pincode'),
                            map_location=get_val(row, 'map_location'),
                            street=get_val(row, 'street'),
                            owner_name=get_val(row, 'owner_name'),
                            contact_type=get_val(row, 'contact_type'),
                            customer_type=get_val(row, 'customer_type'),
                            customer_size=get_val(row, 'customer_size'),
                            gst=get_val(row, 'gst')
                        )
                        db.session.add(new_customer)
                    except Exception as e:
                        print(f"Error creating customer from row {row}: {e}")
                        continue

            db.session.commit()
        return jsonify({'message': 'Customers imported successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


# Route to analyze CSV headers
@app.route('/api/products/analyze_upload', methods=['POST'])
def analyze_upload():
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
            with open(filepath, 'r', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, [])
                
            return jsonify({
                'filename': filename,
                'headers': headers,
                'message': 'File uploaded and analyzed successfully'
            })
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Error analyzing file: {str(e)}'}), 500

    return jsonify({'error': 'Invalid file type'}), 400


# Route to handle bulk product uploads with mapping
@app.route('/api/products/bulk_import', methods=['POST'])
def bulk_import_products():
    data = request.json
    filename = data.get('filename')
    mapping = data.get('mapping')

    if not filename or not mapping:
        return jsonify({'error': 'Missing filename or mapping'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found. Please upload again.'}), 404

    try:
        with open(filepath, 'r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Helper to get mapped value safely
            def get_val(row, field, default=None):
                csv_col = mapping.get(field)
                if csv_col and csv_col in row:
                    val = row[csv_col]
                    return val if val.strip() != '' else default
                return default

            for row in reader:
                # Check for existing product override if ID is mapped and present
                product_id = get_val(row, 'id')
                
                # Check mapping for key fields to decide if we update or create?
                # The prompt implies we just map columns.
                # Let's support ID update if mapped.
                
                if product_id:
                     product = Product.query.get(product_id)
                     if product:
                        product.brand = get_val(row, 'brand', product.brand)
                        product.item_code = get_val(row, 'item_code', product.item_code)
                        product.pack_size = get_val(row, 'pack_size', product.pack_size)
                        product.category = get_val(row, 'category', product.category)
                        product.brand_type = get_val(row, 'brand_type', product.brand_type)
                        product.item_name = get_val(row, 'item_name', product.item_name)
                        product.also_known_as = get_val(row, 'also_known_as', product.also_known_as)
                        product.oem_part_no = get_val(row, 'oem_part_no', product.oem_part_no)
                        product.hsn_code = get_val(row, 'hsn_code', product.hsn_code)
                        product.description = get_val(row, 'description', product.description)
                        
                        try:
                            product.sale_price = float(get_val(row, 'sale_price', product.sale_price))
                        except (ValueError, TypeError): pass
                        
                        try:
                             product.cost = float(get_val(row, 'cost', product.cost))
                        except (ValueError, TypeError): pass
                        
                        try:
                            product.mrp = float(get_val(row, 'mrp', product.mrp))
                        except (ValueError, TypeError): pass

                        try:
                            product.list_price = float(get_val(row, 'list_price', product.list_price))
                        except (ValueError, TypeError): pass

                     else:
                        # Skip or error? Let's skip if ID provided but not found
                        continue
                else:
                    # Create new product
                    try:
                        new_product = Product(
                            brand=get_val(row, 'brand', ''),
                            item_code=get_val(row, 'item_code', ''),
                            pack_size=get_val(row, 'pack_size'),
                            category=get_val(row, 'category', ''),
                            brand_type=get_val(row, 'brand_type'),
                            item_name=get_val(row, 'item_name', ''),
                            also_known_as=get_val(row, 'also_known_as'),
                            oem_part_no=get_val(row, 'oem_part_no'),
                            hsn_code=get_val(row, 'hsn_code'),
                            description=get_val(row, 'description'),
                            sale_price=0,
                            cost=0,
                            mrp=0,
                            list_price=0
                        )
                        
                        # Handle Numeric Fields Safely
                        try: new_product.sale_price = float(get_val(row, 'sale_price', 0))
                        except: pass
                        try: new_product.cost = float(get_val(row, 'cost', 0))
                        except: pass
                        try: new_product.mrp = float(get_val(row, 'mrp', 0))
                        except: pass
                        try: new_product.list_price = float(get_val(row, 'list_price', 0))
                        except: pass

                        db.session.add(new_product)
                    except Exception as e:
                        print(f"Error creating product from row {row}: {e}")
                        continue

            db.session.commit()
        return jsonify({'message': 'Products imported successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
             os.remove(filepath)

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
