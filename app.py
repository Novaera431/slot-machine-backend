from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# URL de conexão ao PostgreSQL
DATABASE_URL = "postgresql://slot_machine_db_user:SGOF9BzWYw7uuWuErLHaIHkegFi0Glb1@dpg-cts27njqf0us73dnvnk0-a/slot_machine_db"

# Função para conectar ao banco de dados PostgreSQL
def connect_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Inicializa o banco de dados e cria a tabela se não existir
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

# Chama a função para inicializar o banco de dados
init_db()

# Rota para registrar uma jogada
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
            
            # Verifica se o cupom já foi utilizado
            cursor.execute('SELECT * FROM jogadas WHERE cupom = %s', (cupom,))
            resultado = cursor.fetchone()

            if resultado:
                return jsonify({'error': 'Cupom já utilizado!'}), 400

            # Insere a nova jogada no banco de dados
            cursor.execute('''
                INSERT INTO jogadas (cupom, valor, slot1, slot2, slot3)
                VALUES (%s, %s, %s, %s, %s)
            ''', (cupom, valor, frutas[0], frutas[1], frutas[2]))
            conn.commit()

        return jsonify({'message': 'Jogada registrada com sucesso!'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Inicializa o servidor Flask
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
