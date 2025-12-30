FROM nikolaik/python-nodejs:python3.11-nodejs20

WORKDIR /app

# Copiar manifests de WhatsApp
COPY package*.json ./

# Instalar dependencias
RUN npm install --omit=dev

# Copiar código
COPY . .

EXPOSE 3030

CMD ["node", "server.cjs"]
