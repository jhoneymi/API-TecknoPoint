import os
from flask import Flask, request, jsonify, make_response
from flask_mysqldb import MySQL
import bcrypt
import jwt
import datetime
from functools import wraps

app = Flask(__name__)

# Configuración de la base de datos
app.config['MYSQL_HOST'] = 'gondola.proxy.rlwy.net'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'lPVSZrKrYFXXLTwasxnCLAdAYOlHnukM'
app.config['MYSQL_DB'] = 'railway'
app.config['MYSQL_PORT'] = 59728
app.config['SECRET_KEY'] = 'Jhoneymi'

mysql = MySQL(app)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-tokens')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (data['username'],))
            current_user = cursor.fetchone()
        except:
            return jsonify({'message': 'Token is invalid!'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/')
def index():
    return jsonify({"message": "Welcome to the API!"})

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data['username']
        password = data['password']
        email = data['email']
        
        # Validación básica de datos
        if not username or not password or not email:
            return jsonify({'message': 'All fields are required'}), 400
        
        # Validar el formato del email
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            return jsonify({'message': 'Invalid email format'}), 400
        
        # Verificar si el usuario o email ya existe
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            return jsonify({'message': 'Username or email already exists'}), 400
        
        # Hashear la contraseña
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Insertar el nuevo usuario
        cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, hashed_password, email))
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500
        
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    
    # Conexión a la base de datos
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    
    if user:
        # Verificar si el formato del hash de la contraseña es válido
        stored_password = user[3]  # Asumiendo que user[2] es el campo de la contraseña
        
        # Limpiar posibles saltos de línea o espacios en blanco en el hash
        stored_password = stored_password.strip()
        print(f"Stored password: {stored_password}")
        print(password.encode('utf-8'))
        print(stored_password.encode('utf-8'))
        
        # Comprobar si el hash de la contraseña coincide
        if stored_password and bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            token = jwt.encode(
                {'username': user[1], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
                app.config['SECRET_KEY'], algorithm="HS256"
            )
            return jsonify({'token': token})
        else:
            return make_response('Invalid credentials', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'})
    else:
        return make_response('User not found', 404)
        
@app.route('/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({'message': 'This is a protected route.', 'user': current_user[1]})

@app.route('/productAdd', methods=['POST'])
def productadd():
    data = request.get_json()

    name = data.get('name')
    price = data.get('price')
    quantity = data.get('quantity')
    description = data.get('description')
    image_uri = data.get('image_uri')
    category = data.get('category')

    if not all([name, price, quantity, description, image_uri, category]):
        return jsonify({'message': 'All fields are required'}), 400

    cursor = mysql.connection.cursor()

    try:
        # Verificar si la categoría existe
        cursor.execute("SELECT * FROM category WHERE id = %s", (category,))
        category_exists = cursor.fetchone()
        
        if not category_exists:
            return jsonify({'message': 'Category does not exist'}), 400
        
        cursor.execute("INSERT INTO products (name, price, quantity, description, image_uri, category) VALUES (%s, %s, %s, %s, %s, %s)",
                       (name, price, quantity, description, image_uri, category))
        mysql.connection.commit()
        return jsonify({'message': 'Product added successfully'}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'Failed to add product', 'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/getproduct', methods=['GET'])
def getproduct():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        
        # Convertir los resultados a un formato JSON adecuado
        product_list = []
        for product in products:
            product_dict = {
                'id': product[0],
                'name': product[1],
                'price': product[2],
                'quantity': product[3],
                'description': product[4],
                'image_uri': product[5],
                'category': product[6]
            }
            product_list.append(product_dict)
        
        return jsonify({'products': product_list}), 200
    
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve products', 'error': str(e)}), 500
    
    finally:
        cursor.close()

@app.route('/deleteproduct/<int:id>', methods=['DELETE'])
def delete_product(id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM products WHERE id = %s", (id,))
        product = cursor.fetchone()
        
        if product is None:
            return jsonify({'message': 'Producto no encontrado'}), 404
        
        cursor.execute("DELETE FROM products WHERE id = %s", (id,))
        mysql.connection.commit()
        
        return jsonify({'message': 'Producto eliminado exitosamente'}), 200
    
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'Error al eliminar el producto', 'error': str(e)}), 500
    
    finally:
        cursor.close()

@app.route('/updateproduct/<int:id>', methods=['PUT'])
def update_product_quantity(id):
    data = request.get_json()

    # Obtener el nuevo valor de la cantidad
    quantity = data.get('quantity')

    # Verificar que la cantidad esté presente y sea válida
    if quantity is None or not isinstance(quantity, int) or quantity < 0:
        return jsonify({'message': 'Valid quantity is required'}), 400

    cursor = mysql.connection.cursor()

    try:
        # Verificar si el producto existe
        cursor.execute("SELECT * FROM products WHERE id = %s", (id,))
        product = cursor.fetchone()

        if product is None:
            return jsonify({'message': 'Product not found'}), 404

        # Actualizar la cantidad del producto
        cursor.execute("""
            UPDATE products
            SET quantity = %s
            WHERE id = %s
        """, (quantity, id))
        mysql.connection.commit()

        return jsonify({'message': 'Product quantity updated successfully'}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'Failed to update product quantity', 'error': str(e)}), 500

    finally:
        cursor.close()


@app.route('/addcategory', methods=['POST'])
def addcategory():
    data = request.get_json()

    description = data.get('description')

    if not description:
        return jsonify({'message': 'All fields are required'}), 400
    
    cursor = mysql.connection.cursor()

    try:
        cursor.execute('INSERT INTO category (description) VALUES (%s)', (description,))
        mysql.connection.commit()
        return jsonify({'message': 'Category added successfully'}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'Failed to add category', 'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/getcategory', methods=['GET'])
def getcategory():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM category")
        categories = cursor.fetchall()

        category_list = []
        for category in categories:
            category_dict = {
                'id': category[0],
                'description': category[1]
            }
            category_list.append(category_dict)
        
        return jsonify({'categories': category_list}), 200
    
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve categories', 'error': str(e)}), 500
    
    finally:
        cursor.close()

@app.route('/addbill', methods=['POST'])
def addbill():
    data = request.get_json()

    date = data.get('date')  # Esperado en formato 'YYYY-MM-DD'
    number_bill = data.get('number_bill')
    total_general = data.get('total_general')

    if not all([date, number_bill, total_general]):
        return jsonify({'message': 'All fields are required'}), 400

    cursor = mysql.connection.cursor()

    try:
        # Aquí el number_bill es tratado como el id
        cursor.execute("INSERT INTO bills (date, number_bill, total_general) VALUES (%s, %s, %s)",
                       (date, number_bill, total_general))
        mysql.connection.commit()

        # Se devuelve el mismo number_bill como id de la factura creada
        return jsonify({'message': 'Bill added successfully', 'bill_id': number_bill}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'Failed to add bill', 'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/getbills', methods=['GET'])
def getbills():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM bills")
        bills = cursor.fetchall()

        bill_list = []
        for bill in bills:
            bill_dict = {
                'id': bill[0],
                'date': bill[1].strftime('%Y-%m-%d') if isinstance(bill[1], datetime.date) else str(bill[1]),
                'number_bill': bill[2],
                'total_general': float(bill[3])
            }
            bill_list.append(bill_dict)

        return jsonify({'bills': bill_list}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve bills', 'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/addbilldetail', methods=['POST'])
def add_bill_detail():
    data = request.get_json()

    bill_id = data.get('bill_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity')
    total_price = data.get('total_price')

    if not all([bill_id, product_id, quantity, total_price]):
        return jsonify({'message': 'All fields are required'}), 400

    cursor = mysql.connection.cursor()

    try:
        # Verificar que la factura exista usando el bill_id (que es el number_bill)
        cursor.execute("SELECT * FROM bills WHERE number_bill = %s", (bill_id,))
        if cursor.fetchone() is None:
            return jsonify({'message': 'Bill not found'}), 404

        # Verificar que el producto exista
        cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        if cursor.fetchone() is None:
            return jsonify({'message': 'Product not found'}), 404

        # Insertar el detalle de la factura en billdetail
        cursor.execute("""
            INSERT INTO billdetail (id_bill, id_product, quantity, total_price)
            VALUES (%s, %s, %s, %s)
        """, (bill_id, product_id, quantity, total_price))
        mysql.connection.commit()
        return jsonify({'message': 'Bill detail added successfully'}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'Failed to add bill detail', 'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/getbilldetails/<int:bill_id>', methods=['GET'])
def get_bill_details(bill_id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT bd.id, bd.id_bill, bd.id_product, p.name, bd.quantity, bd.total_price
            FROM billdetail bd
            JOIN products p ON bd.id_product = p.id
            WHERE bd.id_bill = %s
        """, (bill_id,))
        details = cursor.fetchall()

        detail_list = []
        for d in details:
            detail_list.append({
                'id': d[0],
                'id_bill': d[1],
                'id_product': d[2],
                'product_name': d[3],
                'quantity': d[4],
                'total_price': float(d[5])
            })

        return jsonify({'bill_details': detail_list}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve bill details', 'error': str(e)}), 500
    finally:
        cursor.close()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
