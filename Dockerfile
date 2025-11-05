# Imagen base con Python y Node.js
FROM nikolaik/python-nodejs:python3.11-nodejs20

# Instalar Chromium
RUN apt-get update && apt-get install -y chromium && apt-get clean

# Directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar dependencias Node.js (incluye Puppeteer)
RUN npm install --production

# Configurar Puppeteer para usar el Chromium instalado
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_DOWNLOAD=true

# Exponer puerto Django
EXPOSE 8000

# Comando principal
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
