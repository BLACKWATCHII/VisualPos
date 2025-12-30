# Imagen base
FROM nikolaik/python-nodejs:python3.11-nodejs20

# Instalar Chromium
RUN apt-get update && apt-get install -y chromium && apt-get clean

WORKDIR /app

# Copiar SOLO package.json primero (mejor cache)
COPY baileys/package*.json ./baileys/

# Instalar dependencias Node.js en la carpeta correcta
RUN cd baileys && npm install --production

# Copiar el resto del proyecto
COPY . .

# Dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Puppeteer config
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_DOWNLOAD=true

# Puertos
EXPOSE 8000
EXPOSE 3030

# Django por defecto
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
