FROM nikolaik/python-nodejs:python3.11-nodejs20

WORKDIR /app

# Copiar manifests
COPY package*.json ./

# Instalar dependencias
RUN npm install --production

# Copiar código
COPY . .

EXPOSE 3030

CMD ["node", "server.cjs"]
