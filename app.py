import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from dotenv import load_dotenv
import io
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import queue
import time
from pathlib import Path

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurar a chave da API da OpenAI usando variável de ambiente
openai.api_key = os.getenv("OPENAI_API_KEY")

# Criar a aplicação Flask para servir de backend
app = Flask(__name__)
CORS(app)  # Habilitar CORS

PASTA_TEMP = Path(__file__).parent / 'temp'
PASTA_TEMP.mkdir(exist_ok=True)
ARQUIVO_AUDIO_TEMP = PASTA_TEMP / 'audio.mp3'

# Capturar áudio com Streamlit
def streamlit_audio_capture():
    webrtc_ctx = webrtc_streamer(
        key="audio_transcriber",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={"audio": True, "video": False},
    )

    if not webrtc_ctx.state.playing:
        st.warning("Clique no botão acima para iniciar a gravação.")
        return None

    audio_data = []
    status_container = st.empty()

    while webrtc_ctx.audio_receiver:
        try:
            audio_frames = webrtc_ctx.audio_receiver.get_frames(timeout=1)
        except queue.Empty:
            time.sleep(0.1)
            continue

        audio_data.extend(audio_frames)
        status_container.write(f"Gravando: {len(audio_data)} frames capturados.")

    return audio_data

# Endpoint para transcrição de áudio
@app.route('/transcrever', methods=['POST'])
def transcrever_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "Nenhum arquivo de áudio enviado"}), 400

    audio_file = request.files['audio']
    try:
        # Ler o arquivo de áudio e garantir que seja um formato suportado
        audio_bytes = audio_file.read()
        audio_stream = io.BytesIO(audio_bytes)

        # Verificar o tipo de arquivo enviado
        mime_type = audio_file.mimetype
        print(f"Tipo de arquivo recebido: {mime_type}")  # Log para depuração

        # Certificar que o arquivo é de um dos formatos suportados
        supported_formats = ['audio/webm', 'audio/ogg', 'audio/mpeg', 'audio/wav']
        if mime_type not in supported_formats:
            return jsonify({"error": f"Formato de arquivo não suportado: {mime_type}. Formatos suportados: {supported_formats}"}), 400

        # Definir o nome do arquivo como requerido pela API Whisper
        audio_stream.name = audio_file.filename or 'audio.webm'

        # Transcrever o áudio usando o modelo Whisper da OpenAI
        transcript = openai.Audio.transcribe("whisper-1", audio_stream)
        return jsonify({"transcricao": transcript['text']})
    except Exception as e:
        # Imprimir o erro nos logs do servidor para depuração
        error_message = str(e)
        print(f"Erro na transcrição: {error_message}")
        return jsonify({"error": error_message}), 500

# Endpoint para processar o texto de anamnese
@app.route('/anamnese', methods=['POST'])
def anamnese_texto():
    data = request.get_json()
    texto = data.get('texto', '')

    if not texto:
        return jsonify({"error": "Nenhum texto de anamnese enviado"}), 400

    try:
        # Criar a solicitação para o GPT para gerar um resumo
        resumo_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Resuma o seguinte texto:"},
                {"role": "user", "content": texto}
            ],
            max_tokens=150
        )

        # Criar a solicitação para listar os tópicos principais
        topicos_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Liste os tópicos principais do seguinte texto:"},
                {"role": "user", "content": texto}
            ],
            max_tokens=100
        )

        # Criar a solicitação para listar possíveis tratamentos e medicamentos (somente nome)
        tratamentos_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Liste apenas os nomes dos tratamentos e medicamentos para o seguinte caso clínico:"},
                {"role": "user", "content": texto}
            ],
            max_tokens=100  # Limitando o tamanho para focar apenas nos nomes
        )

        resumo = resumo_response['choices'][0]['message']['content'].strip()
        topicos = topicos_response['choices'][0]['message']['content'].strip()
        tratamentos = tratamentos_response['choices'][0]['message']['content'].strip()

        return jsonify({
            "resumo": resumo,
            "topicos": topicos,
            "tratamentos": tratamentos
        })
    except Exception as e:
        error_message = str(e)
        print(f"Erro na anamnese: {error_message}")
        return jsonify({"error": error_message}), 500

# Função principal do Streamlit para captura e transcrição de áudio
def main():
    st.title("Captura e Transcrição de Áudio")
    
    # Captura o áudio do microfone
    st.header("Capture seu áudio")
    audio_data = streamlit_audio_capture()

    if audio_data:
        # Salva o áudio capturado em arquivo temporário
        with open(ARQUIVO_AUDIO_TEMP, "wb") as f:
            f.write(b"".join([frame.to_ndarray().tobytes() for frame in audio_data]))

        st.success("Áudio capturado com sucesso!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    main()
