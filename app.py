from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import errorcode
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            port=app.config['MYSQL_PORT']
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

@app.route('/items', methods=['GET'])
def get_items():
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(items)

@app.route('/selectitems/<int:item_id>', methods=['GET'])
def get_item(item_id):
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    connection.close()
    if item:
        return jsonify(item)
    else:
        return jsonify({'error': 'Item no encontrado'}), 404

@app.route('/additems', methods=['POST'])
def create_item():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    cursor = connection.cursor()
    cursor.execute("INSERT INTO items (name, description) VALUES (%s, %s)", (name, description))
    connection.commit()
    new_id = cursor.lastrowid
    cursor.close()
    connection.close()
    return jsonify({'id': new_id, 'name': name, 'description': description}), 201

@app.route('/updateitems/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    cursor = connection.cursor()
    cursor.execute("UPDATE items SET name = %s, description = %s WHERE id = %s", (name, description, item_id))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({'id': item_id, 'name': name, 'description': description})

@app.route('/deleteitems/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    cursor = connection.cursor()
    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({'result': 'Item eliminado'})

if __name__ == '__main__':
    app.run(debug=True)