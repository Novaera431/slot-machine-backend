from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
CORS(app)

# Configurações do banco de dados
DB_CONFIG = {
    'dbname': 'slot_machine',
    'user': 'postgres',
    'password': 'senha123',
    'host': 'localhost'
}

# Chave secreta para JWT (use uma chave segura e única)
SECRET_KEY = 'chave_super_secreta_para_jwt'

# Conexão com o banco de dados
def conectar_db():
    return psycopg2.connect(**DB_CONFIG)

# Função para gerar token JWT
def gerar_token(cupom, valor):
    payload = {
        'cupom': cupom,
        'valor': valor,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5)  # Token expira em 5 minutos
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

# Middleware para verificar o token JWT nas requisições
def verificar_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'error': 'Token ausente!'}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.cupom = data['cupom']
            request.valor = data['valor']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido!'}), 401

        return f(*args, **kwargs)
    return decorated

# Rota para gerar token
@app.route('/api/token', methods=['POST'])
def gerar_token_endpoint():
    dados = request.get_json()
    cupom = dados.get('cupom')
    valor = dados.get('valor')

    if not cupom or not valor:
        return jsonify({'error': 'Dados incompletos'}), 400
    
    token = gerar_token(cupom, valor)
    return jsonify({'token': token})

# Função para sortear as frutas aleatoriamente
def sortear_frutas():
    import random
    frutas = ["🍇", "🍉", "🍒", "🍍", "🍓", "🍋", "🍈", "🥝"]
    return [random.choice(frutas) for _ in range(3)]

# Função para calcular o prêmio
def calcular_premio(frutas):
    if frutas[0] == frutas[1] == frutas[2]:
        premios = {
            "🍇": 1000,
            "🍉": 500,
            "🍒": 300,
            "🍍": 200,
            "🍓": 100,
            "🍋": 50,
            "🍈": 20,
            "🥝": 10
        }
        return premios.get(frutas[0], 0)
    return 0

# Rota protegida para jogar (verifica o token)
@app.route('/api/jogar', methods=['POST'])
@verificar_token
def jogar():
    cupom = request.cupom
    valor = request.valor

    if not cupom or not valor:
        return jsonify({'error': 'Dados incompletos'}), 400

    conn = conectar_db()
    cursor = conn.cursor()

    try:
        # Verifica se o cupom já foi utilizado
        cursor.execute('SELECT 1 FROM jogadas WHERE cupom = %s', (cupom,))
        if cursor.fetchone():
            return jsonify({'error': 'O cupom só pode ser usado uma vez'}), 400

        # Realiza o sorteio das frutas
        frutas = sortear_frutas()
        premio = calcular_premio(frutas)

        # Registra a jogada no banco de dados
        cursor.execute(
            'INSERT INTO jogadas (cupom, valor, frutas) VALUES (%s, %s, %s)',
            (cupom, valor, ''.join(frutas))
        )
        conn.commit()

        return jsonify({'frutas': frutas, 'premio': premio})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Erro interno no servidor'}), 500

    finally:
        cursor.close()
        conn.close()

# Rota para verificar cupons
@app.route('/api/verificar-cupom', methods=['POST'])
def verificar_cupom():
    dados = request.get_json()
    cupom = dados.get('cupom')

    if not cupom:
        return jsonify({'error': 'Cupom não informado'}), 400

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute('SELECT 1 FROM jogadas WHERE cupom = %s', (cupom,))
    if cursor.fetchone():
        return jsonify({'error': 'Cupom já utilizado'}), 400
    
    return jsonify({'message': 'Cupom válido'}), 200

# Inicialização do servidor
if __name__ == '__main__':
    app.run(debug=True)
