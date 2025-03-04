from flask import Flask, request, jsonify, make_response
from flask_mysqldb import MySQL
import bcrypt
import jwt
import datetime
from functools import wraps

app = Flask(__name__)

# Configuración de la base de datos
app.config['MYSQL_HOST'] = 'roundhouse.proxy.rlwy.net'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'xkYZLWFxTIPyhBNbymyiZIGWxYbLEygD'
app.config['MYSQL_DB'] = 'railway'
app.config['MYSQL_PORT'] = 37225
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

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    password = data['password']
    email = data['email']
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, hashed_password, email))
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
        token = jwt.encode({'username': user[1], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token})
    else:
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'})

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

if __name__ == '__main__':
    app.run(debug=True)