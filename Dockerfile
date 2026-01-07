FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Atualizar pip e instalar uv
RUN pip install --upgrade pip && \
    pip install uv

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements.txt
COPY requirements.txt .

# Instalar dependências Python usando uv
RUN uv pip install --system -r requirements.txt

# Copiar código da aplicação
COPY app.py .

# Criar diretório de downloads
RUN mkdir -p downloads

# Expor porta
EXPOSE 5000

# Comando para produção usando gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "300", "app:app"]

