from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)

DATABASE_URL = "postgresql://slot_machine_db_user:SGOF9BzWYw7uuWuErLHaIHkegFi0Glb1@dpg-cts27njqf0us73dnvnk0-a/slot_machine_db"

def connect_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Inicializa o banco de dados
def init_db():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jogadas (
                id SERIAL PRIMARY KEY,
                cupom TEXT UNIQUE,
                valor REAL,
                slot1 TEXT,
                slot2 TEXT,
                slot3 TEXT
            )
        ''')
        conn.commit()

init_db()

# Verifica se o cupom já foi utilizado antes de girar
@app.route('/api/verificar-cupom', methods=['POST'])
def verificar_cupom():
    data = request.json
    cupom = data.get('cupom')

    if not cupom:
        return jsonify({'error': 'Cupom não informado'}), 400

    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM jogadas WHERE cupom = %s', (cupom,))
            resultado = cursor.fetchone()

            if resultado:
                return jsonify({'error': 'Cupom já utilizado!'}), 400

        return jsonify({'message': 'Cupom válido!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jogar', methods=['POST'])
def jogar():
    data = request.json
    cupom = data.get('cupom')
    valor = data.get('valor')
    frutas = data.get('frutas')

    if not cupom or not valor or not frutas:
        return jsonify({'error': 'Dados incompletos'}), 400

    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO jogadas (cupom, valor, slot1, slot2, slot3)
                VALUES (%s, %s, %s, %s, %s)
            ''', (cupom, valor, frutas[0], frutas[1], frutas[2]))
            conn.commit()

        return jsonify({'message': 'Jogada registrada com sucesso!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
