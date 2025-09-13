# Usar imagen oficial de Python
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para Pillow y QR
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY app.py .

# Crear directorio para la base de datos
RUN mkdir -p /app/data

# Exponer puerto de Streamlit
EXPOSE 8501

# Configurar variables de entorno para Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Crear usuario no-root para seguridad y asignar permisos
RUN useradd -m -u 1000 streamlit && \
    chown -R streamlit:streamlit /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/data
USER streamlit

# Comando de inicio
CMD ["streamlit", "run", "app.py"]