from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import os

app = Flask(__name__)
CORS(app)

cupons_validos = {
    "ABC123": True,
    "XYZ789": True
}

premios = ["R$ 10,00 de desconto", "R$ 50,00 de desconto", "Nenhum prêmio"]

@app.route('/api/jogar', methods=['POST'])
def jogar():
    data = request.json
    cupom = data.get('cupom')
    
    if cupom in cupons_validos and cupons_validos[cupom]:
        cupons_validos[cupom] = False  # Marca como utilizado
        premio = random.choice(premios)
        return jsonify({"message": f"Você ganhou: {premio}"})
    else:
        return jsonify({"message": "Cupom inválido ou já utilizado!"})

# Rota de teste para GET (navegador)
@app.route('/api/testar', methods=['GET'])
def testar():
    return jsonify({"message": "Backend do Slot Machine está funcionando!"})

@app.route('/')
def home():
    return "Slot Machine Backend está rodando!"

port = int(os.environ.get("PORT", 5000))
app.run(host='0.0.0.0', port=port)
