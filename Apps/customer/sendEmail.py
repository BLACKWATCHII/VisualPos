from email.message import EmailMessage
import smtplib
import os
from dotenv import load_dotenv
import mimetypes


from visualpos import settings

load_dotenv()

def send_email(destinatario, asunto, contenido_texto, contenido_html):
    remitente_real = os.getenv('EMAIL_USER')         
    remitente_alias = os.getenv('EMAIL_ALIAS')       
    password = os.getenv('EMAIL_PASS')

    mensaje = EmailMessage()
    mensaje['Subject'] = asunto
    mensaje['From'] = remitente_alias                 
    mensaje['To'] = destinatario
    mensaje.set_content(contenido_texto)
    mensaje.add_alternative(contenido_html, subtype='html')

    try:
        with smtplib.SMTP_SSL('smtp.zoho.com', 465) as smtp:
            smtp.login(remitente_real, password)
            smtp.send_message(mensaje)
            print(" Correo enviado con éxito desde el alias")
    except Exception as e:
        print(f" Error al enviar el correo: {e}")

def send_email_with_attachment(destinatario, asunto="", contenido_texto="", contenido_html="", attachment_path=None, attachment_name=None):
    try:
        remitente_real = os.getenv("EMAIL_USER")
        remitente_alias = os.getenv("EMAIL_ALIAS", remitente_real)
        password = os.getenv("EMAIL_PASS")

        if not remitente_real or not password:
            print("Credenciales SMTP no configuradas.")
            return False

        if not destinatario:
            print(" Destinatario no especificado.")
            return False

        mensaje = EmailMessage()
        mensaje["Subject"] = asunto or "Factura Adjunta"
        mensaje["From"] = remitente_alias
        mensaje["To"] = destinatario

        # Contenido plano + HTML
        mensaje.set_content(contenido_texto or "Adjunto encontrará su factura en formato PDF.")
        if contenido_html:
            mensaje.add_alternative(contenido_html, subtype="html")

        # Adjuntar archivo correctamente
        if attachment_path and os.path.exists(attachment_path):
            nombre_archivo = attachment_name or os.path.basename(attachment_path)
            ctype, encoding = mimetypes.guess_type(attachment_path)
            maintype, subtype = (ctype or "application/octet-stream").split("/", 1)

            with open(attachment_path, "rb") as f:
                mensaje.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=nombre_archivo
                )
            print(f" Archivo adjunto agregado: {nombre_archivo}")
        elif attachment_path:
            print(f"El archivo especificado no existe: {attachment_path}")

        with smtplib.SMTP_SSL("smtp.zoho.com", 465) as smtp:
            smtp.login(remitente_real, password)
            smtp.send_message(mensaje)
            print(f"Correo enviado a: {destinatario}")
            return True

    except Exception as e:
        print(f" Error enviando email: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False