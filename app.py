from flask import Flask, request, jsonify
import random

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)

