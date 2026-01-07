from flask import Flask, render_template_string, request, redirect, url_for, flash, send_file, jsonify
import yt_dlp
import os
import threading
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size

# Criar pasta de downloads se não existir
if not os.path.exists(app.config['DOWNLOAD_FOLDER']):
    os.makedirs(app.config['DOWNLOAD_FOLDER'])

# Armazenar status de downloads em andamento
download_status = {}

def baixar_video_youtube(url, pasta_destino='downloads'):
    """
    Baixa um vídeo do YouTube
    
    Args:
        url: URL do vídeo do YouTube
        pasta_destino: Pasta onde o vídeo será salvo
    
    Returns:
        dict: Informações do vídeo baixado ou None em caso de erro
    """
    # Criar pasta de destino se não existir
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
    
    # Estratégias de formato para tentar (em ordem de preferência)
    estrategias_formato = [
        'bestvideo+bestaudio/best',  # Vídeo + áudio separados
        'best',  # Melhor formato único
        'worst',  # Qualquer formato disponível
    ]
    
    # Opções base
    opcoes_base = {
        'outtmpl': os.path.join(pasta_destino, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': False,
        'ignoreerrors': False,
        # Opções para contornar problemas do YouTube
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],  # Tenta Android primeiro, depois web
            }
        },
    }
    
    # Tentar cada estratégia de formato
    for i, formato in enumerate(estrategias_formato, 1):
        opcoes = opcoes_base.copy()
        opcoes['format'] = formato
        
        # Adicionar merge apenas para primeira estratégia
        if i == 1:
            opcoes['merge_output_format'] = 'mp4'
        
        try:
            with yt_dlp.YoutubeDL(opcoes) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    'success': True,
                    'title': info.get('title', 'Sem título'),
                    'filename': os.path.basename(ydl.prepare_filename(info))
                }
            
        except yt_dlp.utils.DownloadError as e:
            if i < len(estrategias_formato):
                continue
            else:
                return {
                    'success': False,
                    'error': str(e)
                }
        except Exception as e:
            if i < len(estrategias_formato):
                continue
            else:
                return {
                    'success': False,
                    'error': str(e)
                }
    
    return {
        'success': False,
        'error': 'Todas as estratégias de download falharam'
    }

def download_worker(url, download_id):
    """Worker thread para download assíncrono"""
    download_status[download_id] = {'status': 'downloading', 'message': 'Iniciando download...'}
    result = baixar_video_youtube(url, app.config['DOWNLOAD_FOLDER'])
    
    if result['success']:
        download_status[download_id] = {
            'status': 'completed',
            'message': f"Download concluído: {result['title']}",
            'filename': result['filename']
        }
    else:
        download_status[download_id] = {
            'status': 'error',
            'message': f"Erro: {result.get('error', 'Erro desconhecido')}"
        }

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baixador de Videos do Mozão</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #ffeef5 0%, #ffd6e8 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(255, 105, 180, 0.2);
            padding: 40px;
            margin-top: 20px;
        }
        
        h1 {
            color: #ff69b4;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(255, 105, 180, 0.2);
        }
        
        .subtitle {
            text-align: center;
            color: #d63384;
            font-size: 1.1em;
            margin-bottom: 30px;
            font-style: italic;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            color: #c2185b;
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 1.1em;
        }
        
        input[type="text"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #ffb3d9;
            border-radius: 10px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #ff69b4;
            box-shadow: 0 0 10px rgba(255, 105, 180, 0.3);
        }
        
        .btn {
            background: linear-gradient(135deg, #ff69b4 0%, #ff1493 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            width: 100%;
            margin-top: 15px;
        }
        
        .btn-container .btn {
            margin-top: 0;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 105, 180, 0.4);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #ffb3d9 0%, #ff91c4 100%);
            display: block;
            text-align: center;
            text-decoration: none;
        }
        
        form {
            margin-bottom: 0;
        }
        
        .btn-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin-top: 15px;
        }
        
        .alert {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .alert-success {
            background-color: #d4edda;
            border: 2px solid #c3e6cb;
            color: #155724;
        }
        
        .alert-error {
            background-color: #f8d7da;
            border: 2px solid #f5c6cb;
            color: #721c24;
        }
        
        .alert-info {
            background-color: #d1ecf1;
            border: 2px solid #bee5eb;
            color: #0c5460;
        }
        
        .videos-list {
            margin-top: 30px;
        }
        
        .video-item {
            background: #fff5f9;
            border: 2px solid #ffb3d9;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .video-item:hover {
            border-color: #ff69b4;
            box-shadow: 0 3px 10px rgba(255, 105, 180, 0.2);
        }
        
        .video-name {
            color: #c2185b;
            font-weight: bold;
            flex: 1;
            word-break: break-word;
        }
        
        .video-actions {
            display: flex;
            gap: 10px;
        }
        
        .btn-small {
            padding: 8px 15px;
            font-size: 0.9em;
            width: auto;
            margin: 0;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff4757 0%, #ff3838 100%);
        }
        
        .loading {
            text-align: center;
            color: #ff69b4;
            font-size: 1.2em;
            margin: 20px 0;
        }
        
        .spinner {
            border: 4px solid #ffb3d9;
            border-top: 4px solid #ff69b4;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .empty-state {
            text-align: center;
            color: #d63384;
            padding: 40px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Baixador de Videos do Mozão</h1>
        <p class="subtitle">ferramenta de download de videos do Mozão</p>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" action="/download" id="downloadForm">
            <div class="form-group">
                <label for="url">URL do Vídeo do YouTube:</label>
                <input type="text" id="url" name="url" placeholder="https://www.youtube.com/watch?v=..." required>
            </div>
            <div class="btn-container">
                <button type="submit" class="btn">📥 Baixar Vídeo</button>
                <a href="/videos" class="btn btn-secondary">📋 Ver Vídeos Baixados</a>
            </div>
        </form>
        
        <div id="loading" style="display: none;">
            <div class="spinner"></div>
            <div class="loading">Processando download... Por favor, aguarde.</div>
        </div>
    </div>
    
    <script>
        document.getElementById('downloadForm').addEventListener('submit', function(e) {
            document.getElementById('loading').style.display = 'block';
        });
    </script>
</body>
</html>
'''

VIDEOS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vídeos Baixados - Baixador de Videos do Mozão</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #ffeef5 0%, #ffd6e8 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(255, 105, 180, 0.2);
            padding: 40px;
            margin-top: 20px;
        }
        
        h1 {
            color: #ff69b4;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(255, 105, 180, 0.2);
        }
        
        .subtitle {
            text-align: center;
            color: #d63384;
            font-size: 1.1em;
            margin-bottom: 30px;
            font-style: italic;
        }
        
        .btn {
            background: linear-gradient(135deg, #ff69b4 0%, #ff1493 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
            display: inline-block;
            margin-bottom: 20px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 105, 180, 0.4);
        }
        
        .videos-list {
            margin-top: 30px;
        }
        
        .video-item {
            background: #fff5f9;
            border: 2px solid #ffb3d9;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .video-item:hover {
            border-color: #ff69b4;
            box-shadow: 0 3px 10px rgba(255, 105, 180, 0.2);
        }
        
        .video-name {
            color: #c2185b;
            font-weight: bold;
            flex: 1;
            word-break: break-word;
        }
        
        .video-actions {
            display: flex;
            gap: 10px;
        }
        
        .btn-small {
            padding: 8px 15px;
            font-size: 0.9em;
            width: auto;
            margin: 0;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff4757 0%, #ff3838 100%);
        }
        
        .empty-state {
            text-align: center;
            color: #d63384;
            padding: 40px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Baixador de Videos do Mozão</h1>
        <p class="subtitle">ferramenta de download de videos do Mozão</p>
        
        <a href="/" class="btn">🏠 Voltar</a>
        
        <div class="videos-list">
            {% if videos %}
                {% for video in videos %}
                <div class="video-item">
                    <div class="video-name">{{ video }}</div>
                    <div class="video-actions">
                        <a href="/download_file/{{ video }}" class="btn btn-small">⬇️ Baixar</a>
                        <form method="POST" action="/delete/{{ video }}" style="display: inline;" onsubmit="return confirm('Tem certeza que deseja deletar este vídeo?');">
                            <button type="submit" class="btn btn-small btn-danger">🗑️ Deletar</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty-state">
                    Nenhum vídeo baixado ainda. <a href="/">Voltar para baixar um vídeo</a>
                </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

DOWNLOAD_WAIT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preparando Vídeo - Baixador de Videos do Mozão</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #ffeef5 0%, #ffd6e8 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            max-width: 600px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(255, 105, 180, 0.2);
            padding: 40px;
            text-align: center;
        }
        
        h1 {
            color: #ff69b4;
            font-size: 2em;
            margin-bottom: 20px;
        }
        
        .spinner {
            border: 4px solid #ffb3d9;
            border-top: 4px solid #ff69b4;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin: 30px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .message {
            color: #c2185b;
            font-size: 1.2em;
            margin-top: 20px;
        }
        
        .error {
            color: #d32f2f;
            background: #ffebee;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
        
        .success {
            color: #2e7d32;
            background: #e8f5e9;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Baixador de Videos do Mozão</h1>
        <div class="spinner"></div>
        <div class="message" id="message">O vídeo está sendo preparado para download. Por favor, aguarde...</div>
        <div id="status"></div>
    </div>
    
    <script>
        const downloadId = '{{ download_id }}';
        let checkCount = 0;
        const maxChecks = 300; // 5 minutos máximo (1 segundo * 300)
        
        function checkStatus() {
            checkCount++;
            if (checkCount > maxChecks) {
                document.getElementById('message').textContent = 'Tempo limite excedido. Por favor, tente novamente.';
                document.getElementById('status').innerHTML = '<div class="error">O download está demorando mais que o esperado. <a href="/">Voltar</a></div>';
                return;
            }
            
            fetch('/check_download/' + downloadId)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'completed') {
                        // Redirecionar para tela de seleção de pasta
                        window.location.href = '/ready/' + downloadId;
                    } else if (data.status === 'error') {
                        document.getElementById('message').textContent = 'Erro no download';
                        document.getElementById('status').innerHTML = '<div class="error">' + data.message + '<br><a href="/">Voltar</a></div>';
                    } else {
                        // Continuar verificando
                        setTimeout(checkStatus, 1000);
                    }
                })
                .catch(error => {
                    console.error('Erro:', error);
                    setTimeout(checkStatus, 2000);
                });
        }
        
        // Iniciar verificação após 2 segundos
        setTimeout(checkStatus, 2000);
    </script>
</body>
</html>
'''

READY_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vídeo Pronto - Baixador de Videos do Mozão</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #ffeef5 0%, #ffd6e8 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            max-width: 600px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(255, 105, 180, 0.2);
            padding: 40px;
            text-align: center;
        }
        
        h1 {
            color: #ff69b4;
            font-size: 2em;
            margin-bottom: 20px;
        }
        
        .message {
            color: #c2185b;
            font-size: 1.2em;
            margin-bottom: 30px;
        }
        
        .btn {
            background: linear-gradient(135deg, #ff69b4 0%, #ff1493 100%);
            color: white;
            padding: 20px 40px;
            border: none;
            border-radius: 10px;
            font-size: 1.3em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
            font-family: inherit;
        }
        
        form {
            display: inline-block;
            margin: 0;
            padding: 0;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 105, 180, 0.4);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .error {
            color: #d32f2f;
            background: #ffebee;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Baixador de Videos do Mozão</h1>
        <div class="message">O vídeo está pronto! Clique no botão abaixo para escolher onde salvar.</div>
        <form id="downloadForm" method="get" target="_blank" style="display: inline;">
            <button type="submit" id="downloadBtn" class="btn">📁 Escolher Pasta e Baixar Vídeo</button>
        </form>
        <div id="status"></div>
    </div>
    
    <script>
        const downloadId = '{{ download_id }}';
        
        // Buscar informações do download
        fetch('/check_download/' + downloadId)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    const filename = encodeURIComponent(data.filename);
                    const downloadUrl = '/download_file/' + filename;
                    
                    // Configurar o formulário para fazer o download
                    const downloadForm = document.getElementById('downloadForm');
                    downloadForm.action = downloadUrl;
                    
                    // Interceptar o submit do formulário
                    downloadForm.onsubmit = function(e) {
                        // Não prevenir o comportamento padrão - deixar o formulário abrir em nova aba
                        // Isso vai iniciar o download e abrir a janela "Salvar como"
                        
                        // Aguardar um tempo antes de redirecionar a página atual
                        setTimeout(() => {
                            window.location.href = '/downloading';
                        }, 3000); // 3 segundos para dar tempo da janela "Salvar como" abrir
                        
                        return true; // Permitir que o formulário funcione normalmente
                    };
                } else if (data.status === 'error') {
                    document.getElementById('status').innerHTML = '<div class="error">' + data.message + '<br><a href="/">Voltar</a></div>';
                    document.getElementById('downloadBtn').style.display = 'none';
                } else {
                    // Ainda processando, redirecionar de volta
                    window.location.href = '/download';
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                document.getElementById('status').innerHTML = '<div class="error">Erro ao carregar informações. <a href="/">Voltar</a></div>';
            });
    </script>
</body>
</html>
'''

DOWNLOADING_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baixando Vídeo - Baixador de Videos do Mozão</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #ffeef5 0%, #ffd6e8 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            max-width: 600px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(255, 105, 180, 0.2);
            padding: 40px;
            text-align: center;
        }
        
        h1 {
            color: #ff69b4;
            font-size: 2em;
            margin-bottom: 20px;
        }
        
        .spinner {
            border: 4px solid #ffb3d9;
            border-top: 4px solid #ff69b4;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin: 30px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .message {
            color: #c2185b;
            font-size: 1.2em;
            margin-top: 20px;
        }
        
        .timer {
            color: #ff69b4;
            font-size: 1.5em;
            font-weight: bold;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Baixador de Videos do Mozão</h1>
        <div class="spinner"></div>
        <div class="message">O vídeo está sendo baixado para o seu computador...</div>
        <div class="timer" id="timer">Aguarde 10 segundos...</div>
    </div>
    
    <script>
        let secondsLeft = 10;
        const timerElement = document.getElementById('timer');
        
        function updateTimer() {
            if (secondsLeft > 0) {
                timerElement.textContent = `Aguarde ${secondsLeft} segundo${secondsLeft > 1 ? 's' : ''}...`;
                secondsLeft--;
                setTimeout(updateTimer, 1000);
            } else {
                // Redirecionar para tela de sucesso após 10 segundos
                window.location.href = '/success';
            }
        }
        
        // Iniciar timer
        updateTimer();
    </script>
</body>
</html>
'''

SUCCESS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Download Concluído - Baixador de Videos do Mozão</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #ffeef5 0%, #ffd6e8 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            max-width: 600px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(255, 105, 180, 0.2);
            padding: 40px;
            text-align: center;
        }
        
        h1 {
            color: #ff69b4;
            font-size: 2em;
            margin-bottom: 20px;
        }
        
        .success-icon {
            font-size: 5em;
            margin: 20px 0;
        }
        
        .message {
            color: #c2185b;
            font-size: 1.2em;
            margin-bottom: 30px;
        }
        
        .btn {
            background: linear-gradient(135deg, #ff69b4 0%, #ff1493 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 105, 180, 0.4);
        }
        
        .btn:active {
            transform: translateY(0);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Baixador de Videos do Mozão</h1>
        <div class="success-icon">✅</div>
        <div class="message">Vídeo Baixado com Sucesso!</div>
        <p style="color: #666; margin-bottom: 20px;">O vídeo foi baixado com sucesso para a pasta selecionada.</p>
        <a href="/" class="btn">🏠 Voltar à Página Inicial</a>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url', '').strip()
    
    if not url:
        flash('Por favor, forneça uma URL válida.', 'error')
        return redirect(url_for('index'))
    
    # Validar se é uma URL do YouTube
    if 'youtube.com' not in url and 'youtu.be' not in url:
        flash('Por favor, forneça uma URL válida do YouTube.', 'error')
        return redirect(url_for('index'))
    
    # Criar thread para download assíncrono
    import uuid
    download_id = str(uuid.uuid4())
    
    thread = threading.Thread(target=download_worker, args=(url, download_id))
    thread.daemon = True
    thread.start()
    
    # Retornar página de aguardo que verifica o status e inicia download automaticamente
    return render_template_string(DOWNLOAD_WAIT_TEMPLATE, download_id=download_id)

@app.route('/check_download/<download_id>')
def check_download(download_id):
    """Verifica o status de um download"""
    if download_id in download_status:
        status = download_status[download_id].copy()
        return jsonify(status)
    return jsonify({'status': 'not_found', 'message': 'Download não encontrado'})

@app.route('/ready/<download_id>')
def ready(download_id):
    """Exibe tela de seleção de pasta (Tela 3)"""
    if download_id not in download_status:
        flash('Download não encontrado.', 'error')
        return redirect(url_for('index'))
    
    status = download_status[download_id]
    if status['status'] != 'completed':
        # Se ainda não estiver pronto, redirecionar para tela de preparação
        return redirect(url_for('index'))
    
    return render_template_string(READY_TEMPLATE, download_id=download_id)

@app.route('/downloading')
def downloading():
    """Exibe tela de download em progresso (Tela 4)"""
    return render_template_string(DOWNLOADING_TEMPLATE)

@app.route('/success')
def success():
    """Exibe tela de sucesso (Tela 5)"""
    return render_template_string(SUCCESS_TEMPLATE)

@app.route('/videos')
def videos():
    try:
        files = []
        if os.path.exists(app.config['DOWNLOAD_FOLDER']):
            for filename in os.listdir(app.config['DOWNLOAD_FOLDER']):
                filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
                if os.path.isfile(filepath) and not filename.endswith('.part'):
                    files.append(filename)
        
        files.sort(reverse=True)  # Mais recentes primeiro
        return render_template_string(VIDEOS_TEMPLATE, videos=files)
    except Exception as e:
        flash(f'Erro ao listar vídeos: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/download_file/<path:filename>')
def download_file(filename):
    try:
        # Decodificar o nome do arquivo se necessário
        from urllib.parse import unquote
        filename = unquote(filename)
        
        # Não usar secure_filename para preservar o nome original do arquivo
        
        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        
        if os.path.exists(filepath) and os.path.isfile(filepath):
            # Usar send_file com as_attachment=True para abrir a janela "Salvar como"
            # Importar quote para codificar o nome do arquivo corretamente
            from urllib.parse import quote
            
            # Codificar o nome do arquivo para o header
            encoded_filename = quote(filename.encode('utf-8'))
            
            response = send_file(
                filepath, 
                as_attachment=True,
                download_name=filename,
                mimetype='video/mp4'
            )
            # Adicionar headers para forçar download com nome codificado
            response.headers['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_filename}'
            response.headers['Content-Type'] = 'video/mp4'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response
        else:
            flash('Arquivo não encontrado.', 'error')
            return redirect(url_for('videos'))
    except Exception as e:
        flash(f'Erro ao baixar arquivo: {str(e)}', 'error')
        return redirect(url_for('videos'))

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    try:
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        
        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)
            flash(f'Vídeo "{filename}" deletado com sucesso!', 'success')
        else:
            flash('Arquivo não encontrado.', 'error')
    except Exception as e:
        flash(f'Erro ao deletar arquivo: {str(e)}', 'error')
    
    return redirect(url_for('videos'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

