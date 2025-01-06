from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import jwt
import datetime
from functools import wraps
import os
import logging

from twilio.rest import Client

# Configurações do Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')  # Sandbox do Twilio
MEU_WHATSAPP = os.getenv('MEU_WHATSAPP')

# Inicialização do cliente Twilio
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Rota para enviar prêmio via WhatsApp
@app.route('/enviar-premio', methods=['POST'])
def enviar_premio():
    dados = request.get_json()
    nome = dados.get('nome')
    telefone = dados.get('telefone')
    cupom = dados.get('cupom')
    valor = dados.get('valor')
    premio = dados.get('premio')
    fruta = dados.get('fruta')

    mensagem = (
        f"📩 Novo Ganhador!\n"
        f"Nome: {nome}\n"
        f"Telefone: {telefone}\n"
        f"Cupom Fiscal: {cupom}\n"
        f"Valor da Compra: R${valor}\n"
        f"Prêmio: R${premio}\n"
        f"Fruta: {fruta}"
    )

    try:
        message = client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            body=mensagem,
            to=MEU_WHATSAPP
        )
        return jsonify({'message': 'Mensagem enviada com sucesso!', 'sid': message.sid}), 200
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem pelo Twilio: {str(e)}")
        return jsonify({'error': 'Erro ao enviar mensagem via WhatsApp', 'detalhes': str(e)}), 500


app = Flask(__name__)
CORS(app)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL de conexão com o banco de dados PostgreSQL
DATABASE_URL = "postgresql://slot_machine_db_user:SGOF9BzWYw7uuWuErLHaIHkegFi0Glb1@dpg-cts27njqf0us73dnvnk0-a/slot_machine_db"

# Chave secreta para JWT
SECRET_KEY = 'chave_super_secreta_para_jwt'


# Conexão com o banco de dados
def conectar_db():
    return psycopg2.connect(DATABASE_URL)


# Função para gerar token JWT
def gerar_token(cupom, valor):
    payload = {
        'cupom': cupom,
        'valor': valor,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


# Middleware para verificar token JWT nas requisições
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


# Rota para gerar token JWT
@app.route('/api/token', methods=['POST'])
def gerar_token_endpoint():
    dados = request.get_json()
    cupom = dados.get('cupom')
    valor = dados.get('valor')

    if not cupom or not valor:
        return jsonify({'error': 'Dados incompletos'}), 400
    
    token = gerar_token(cupom, valor)
    return jsonify({'token': token})


# Função para sortear frutas aleatoriamente
def sortear_frutas():
    import random
    frutas = ["🍇", "🍉", "🍒", "🍍", "🍓", "🍋", "🍈", "🥝"]
    return [random.choice(frutas) for _ in range(3)]


# Função para calcular prêmio com base nas frutas
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


# Rota protegida para realizar a jogada
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
        # Verifica se o cupom tem jogadas disponíveis na tabela cupons
        cursor.execute('SELECT jogadas_disponiveis FROM cupons WHERE cupom = %s', (cupom,))
        resultado = cursor.fetchone()
        
        if not resultado:
            return jsonify({'error': 'Cupom não encontrado'}), 400
        
        jogadas_disponiveis = resultado[0]
        if jogadas_disponiveis <= 0:
            return jsonify({'error': 'Você já utilizou todas as jogadas disponíveis com este cupom'}), 400

        # Realiza o sorteio das frutas
        frutas = sortear_frutas()
        premio = calcular_premio(frutas)
        premio = premio if premio > 0 else 0  # Se não houver prêmio, registra 0

        logger.info(f"Frutas sorteadas: {''.join(frutas)} - Prêmio: R${premio}")

        # Insere a jogada na tabela jogadas (registrando o histórico)
        cursor.execute(
            'INSERT INTO jogadas (cupom, frutas, premio) VALUES (%s, %s, %s)',
            (cupom, ''.join(frutas), premio)
        )

        # Atualiza o número de jogadas restantes na tabela cupons
        cursor.execute(
            'UPDATE cupons SET jogadas_disponiveis = jogadas_disponiveis - 1 WHERE cupom = %s RETURNING jogadas_disponiveis',
            (cupom,)
        )
        jogadas_restantes = cursor.fetchone()[0]  # Captura o novo valor após o decremento

        # Commit da transação após as atualizações
        conn.commit()

        # Retorna as frutas sorteadas, prêmio e jogadas restantes para o frontend
        return jsonify({'frutas': frutas, 'premio': premio, 'jogadas_restantes': jogadas_restantes})

    except Exception as e:
        conn.rollback()
        logger.error(f"Erro interno no servidor: {str(e)}")
        return jsonify({'error': 'Erro interno no servidor', 'detalhes': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# Rota para verificar se o cupom já foi utilizado no popup
@app.route('/api/validar-cupom-popup', methods=['POST'])
def validar_cupom_popup():
    dados = request.get_json()
    logger.info(f"Dados recebidos: {dados}")  # Log para verificar o que está sendo recebido
    cupom = dados.get('cupom')
    valor = dados.get('valor')  # Novo campo de valor

    if not cupom or not valor:
        return jsonify({'valido': False, 'error': 'Cupom ou valor não informado'}), 400

    conn = conectar_db()
    cursor = conn.cursor()

    try:
        # Verifica se o cupom já existe na tabela cupons
        cursor.execute('SELECT jogadas_disponiveis FROM cupons WHERE cupom = %s', (cupom,))
        resultado = cursor.fetchone()
        
        # Se o cupom já existe
        if resultado:
            jogadas_disponiveis = resultado[0]
            if jogadas_disponiveis > 0:
                return jsonify({'valido': True, 'jogadas': jogadas_disponiveis}), 200
            else:
                return jsonify({'valido': False, 'error': 'Cupom já utilizado por completo'}), 400

        # Se o cupom não existe, calcula o número de jogadas com base no valor
        valor = float(valor)
        jogadas = int(valor // 50)  # Cada R$50 dá direito a uma jogada

        if jogadas == 0:
            return jsonify({'valido': False, 'error': 'Valor insuficiente para jogar'}), 400
        
        # Insere o cupom na tabela cupons com o total de jogadas
        cursor.execute(
            'INSERT INTO cupons (cupom, valor, jogadas_disponiveis, total_jogadas) VALUES (%s, %s, %s, %s)',
            (cupom, valor, jogadas, jogadas)
        )
        conn.commit()

        return jsonify({'valido': True, 'jogadas': jogadas}), 200

    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao validar cupom: {str(e)}")
        return jsonify({'valido': False, 'error': 'Erro ao validar o cupom'}), 500

    finally:
        cursor.close()
        conn.close()


# Inicialização do Flask na porta correta para Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
