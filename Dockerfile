# Usamos una versión ligera de Python
FROM python:3.9-slim

# Instalamos ffmpeg en el servidor de la nube
RUN apt-get update && apt-get install -y ffmpeg

# Creamos una carpeta de trabajo
WORKDIR /app

# Copiamos los requisitos y los instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de tu código
COPY . .

# Comando para arrancar el servidor
CMD ["python", "app.py"]