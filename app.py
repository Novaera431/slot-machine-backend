from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
import random

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL não configurado")

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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cupom ON jogadas(cupom);')
        conn.commit()

init_db()

# Sorteio de frutas no backend
def sortear_frutas():
    frutas = ["🍇", "🍉", "🍒", "🍍", "🍓", "🍋", "🍈", "🥝"]
    pesos = [1, 2, 3, 4, 5, 6, 7, 8]  # Probabilidades ponderadas
    return random.choices(frutas, weights=pesos, k=3)  # Sorteia 3 frutas

# Verifica se o cupom já foi utilizado
@app.route('/api/verificar-cupom', methods=['POST'])
def verificar_cupom():
    data = request.json
    cupom = data.get('cupom')

    if not cupom:
        return jsonify({'error': 'Cupom não informado'}), 400

    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM jogadas WHERE cupom = %s', (cupom,))
            resultado = cursor.fetchone()

            if resultado:
                return jsonify({'error': 'Cupom já utilizado!'}), 400

        return jsonify({'message': 'Cupom válido!'}), 200
    except psycopg2.Error as e:
        return jsonify({'error': 'Erro interno no banco de dados'}), 500
    except Exception:
        return jsonify({'error': 'Erro desconhecido'}), 500

# Realiza a jogada sorteando as frutas no backend
@app.route('/api/jogar', methods=['POST'])
def jogar():
    data = request.json
    cupom = data.get('cupom')
    valor = data.get('valor')

    if not cupom or not valor:
        return jsonify({'error': 'Dados incompletos'}), 400

    try:
        frutas = sortear_frutas()  # Sorteia as frutas no backend

        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO jogadas (cupom, valor, slot1, slot2, slot3)
                VALUES (%s, %s, %s, %s, %s)
            ''', (cupom, valor, frutas[0], frutas[1], frutas[2]))
            conn.commit()

        return jsonify({
            'message': 'Jogada registrada com sucesso!',
            'frutas': frutas  # Retorna as frutas sorteadas para o frontend
        }), 200
    except psycopg2.Error as e:
        return jsonify({'error': 'Erro interno no banco de dados'}), 500
    except Exception:
        return jsonify({'error': 'Erro desconhecido'}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


