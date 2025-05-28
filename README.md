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
6. Apply migrations:
   ```sh
   python manage.py migrate
   ```
7. Start the server:
   ```sh
   python manage.py runserver
   ```

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

Contributions are welcome! If you want to collaborate, please open an issue or submit a pull request.


## 📞 Contact

📧 Email: [contacto@berserker.com](mailto\:kevin.hernandez25@zohomail.com)\
🌐 Website: [berserker.com](https://berserker-v2.mailerpage.io/)\
🐦 Ceo: [Kevin Hernandez](https://www.linkedin.com/in/kevin-hernandez-431464235/)

---
Berserker is the ultimate tool to take your sales to the next level! ⚡