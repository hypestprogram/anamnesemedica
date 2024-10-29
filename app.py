from flask import Flask, render_template, request, redirect, url_for, send_file, session
from openpyxl import Workbook
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necessário para a sessão funcionar

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    corte = request.form['corte']
    peso = float(request.form['peso'])
    preco = float(request.form['preco'])
    quantidade = int(request.form['quantidade'])

    total = peso * preco * quantidade

    # Salvar os dados na sessão para exibir na página de resumo
    session['corte'] = corte
    session['peso'] = peso
    session['preco'] = preco
    session['quantidade'] = quantidade
    session['total'] = total

    # Criar e salvar o arquivo Excel
    filename = 'calculo_carnes.xlsx'
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['Corte de Carne', 'Peso (kg)', 'Preço por Kg', 'Quantidade', 'Total'])
    sheet.append([corte, peso, preco, quantidade, total])
    workbook.save(filename)

    session['filename'] = filename  # Armazena o nome do arquivo na sessão

    return redirect(url_for('carnes'))

@app.route('/carnes', methods=['GET'])
def carnes():
    if 'corte' not in session:
        return "Nenhum pedido foi realizado.", 400

    corte = session['corte']
    peso = session['peso']
    preco = session['preco']
    quantidade = session['quantidade']
    total = session['total']
    filename = session['filename']

    return render_template('carnes.html', corte=corte, peso=peso, preco=preco,
                           quantidade=quantidade, total=total, filename=filename)

@app.route('/download', methods=['GET'])
def download():
    filename = session.get('filename')
    if filename and os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    else:
        return "Arquivo não encontrado.", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
