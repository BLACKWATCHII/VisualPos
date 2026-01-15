![Banner image](https://form.quantum-staffing.com/wp-content/uploads/2025/04/BerserkerWelcome.png)

# Berserker - Boost Your Sales to the Maximum

## 🚀 About Berserker

Berserker is a sales software designed to optimize and streamline the commercial management of any business. With an intuitive interface and advanced features, Berserker helps you increase efficiency, improve inventory control, and maximize customer satisfaction.

## 🎯 Key Features

- 🛒 **Product Management**: Easily add, edit, and delete products.
- 📦 **Inventory Control**: Keep an accurate track of available stock.
- 💰 **Billing Module**: Generate invoices quickly and easily.
- 📊 **Reports and Analytics**: Obtain key insights for decision-making.
- 🧑‍💼 **Customer Management**: Manage clients and their purchase history.
- 🔄 **Integrations**: Compatible with multiple payment platforms and external providers.
- 🔐 **Security**: Robust authentication system and user permissions.

## 🛠️ Technologies Used

- **Backend**: Django
- **Frontend**: HTML, CSS, Pure JavaScript
- **Database**: SQLite

## 📌 Installation and Setup

:::warning
Vesion python ---> 3.11.0
:::

1. Clone the repository:
   ```sh
   git clone https://github.com/user/berserker.git
   ```
2. Navigate to the project directory:
   ```sh
   cd berserker
   ```
3. Install Virtual environment
   ```sh
   python -m venv env
   ```
4. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
5. Configure the environment in the `.env` file.

6. Makemigrations
   - python manage.py makemigrations customer
   - python manage.py makemigrations inventory
   - python manage.py makemigrations Invoice
   - python manage.py makemigrations item
   - python manage.py makemigrations tax
   - python manage.py makemigrations user
7. Apply migrations:
   ```sh
   python manage.py migrate
   ```
8. Start the server:
   ```sh
   python manage.py runserver
   ```

## 🐳 Docker (Django + WhatsApp/Baileys)

Este proyecto usa un servicio Node (Baileys) para WhatsApp en el puerto `3030`.

Punto clave del error de tu captura:
- `http://whatsapp:3030` **solo existe dentro de Docker Compose** (es el nombre DNS del servicio en la red de Compose).
- Si ejecutas Django en Windows (fuera de Docker) y apuntas a `whatsapp`, te dará `NameResolutionError: Failed to resolve 'whatsapp'`.

### Opción A: Todo dentro de Docker Compose (recomendado)
1. Levanta ambos servicios:
   ```sh
   docker compose up --build
   ```
2. Abre Django: `http://localhost:8000`

En esta opción, Django se comunica con Baileys usando `BAILEYS_URL=http://whatsapp:3030` (ya está configurado en `docker-compose.yml`).

### Opción B: Django en Windows + Baileys en Docker
1. Levanta solo WhatsApp/Baileys:
   ```sh
   docker compose up --build whatsapp
   ```
2. En Windows, configura `BAILEYS_URL` a:
   - `http://127.0.0.1:3030` (o `http://localhost:3030`)

En esta opción NO uses `http://whatsapp:3030` porque ese hostname no se resuelve en tu máquina host.

## Extra📢

Command Delete file migrations and cache

  ```sh
Get-ChildItem -Recurse -Directory -Filter "migrations" | Where-Object { $_.FullName -notmatch "\\env\\" } | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Where-Object { $_.FullName -notmatch "\\env\\" } | Remove-Item -Recurse -Force
  ```
  
  ```sh mac
  find . -type d \( -name "migrations" -o -name "__pycache__" \) -not -path "*env*" -exec rm -rf {} +
   ```
## 📢 Contributions

Contributions are welcome! If you want to collaborate, please open an issue or submit a pull request!!.


## 📞 Contact

📧 Email: [contacto@berserker.com](mailto\:kevin.hernandez25@zohomail.com)\
🌐 Website: [berserker.com](https://berserker-v2.mailerpage.io/)\
🐦 Ceo: [Kevin Hernandez](https://www.linkedin.com/in/kevin-hernandez-431464235/)

---
Berserker is the ultimate tool to take your sales to the next level! ⚡