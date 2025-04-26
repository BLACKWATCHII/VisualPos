from dotenv import load_dotenv
import os
from email.message import EmailMessage
import smtplib

load_dotenv()

def send_email(destinatario, asunto, contenido_texto, contenido_html):
    remitente = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')

    mensaje = EmailMessage()
    mensaje['Subject'] = asunto
    mensaje['From'] = remitente
    mensaje['To'] = destinatario
    mensaje.set_content(contenido_texto)
    mensaje.add_alternative(contenido_html, subtype='html')


    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(remitente, password)
        smtp.send_message(mensaje)
