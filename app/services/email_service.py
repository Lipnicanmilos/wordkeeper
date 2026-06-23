import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_welcome_email(to_email: str, name: str):
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")
    mail_from = os.getenv("MAIL_FROM")
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", 587))

    subject = "Vitaj v LexiNova! 🎉"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
        <h2 style="color: #4F46E5;">Vitaj v LexiNova, {name}! 👋</h2>
        <p>Sme radi, že si sa zaregistroval/a. Teraz môžeš začať učiť sa nové slovíčka.</p>
        <p>Čo môžeš robiť:</p>
        <ul>
            <li>Vytvárať kategórie slovíčok</li>
            <li>Testovať svoje znalosti</li>
            <li>Sledovať svoj pokrok</li>
        </ul>
        <a href="https://lexinova-1096007793591.us-central1.run.app/dashboard" 
           style="background-color: #4F46E5; color: white; padding: 12px 24px; 
                  text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 16px;">
            Začať učiť sa
        </a>
        <p style="margin-top: 32px; color: #888; font-size: 12px;">
            Tím LexiNova
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_from, to_email, msg.as_string())
        print(f"Welcome email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send welcome email: {e}")
        # Neblokujeme registráciu ak sa email neodošle


def send_inquiry_notification(name: str, email: str, message: str, page: str = ""):
    """Odošle notifikáciu o novom dotaze administrátorovi.
    Cieľová adresa je INQUIRY_TO (default lipnicanmilos@gmail.com)."""
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")
    mail_from = os.getenv("MAIL_FROM")
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", 587))
    to_email = os.getenv("INQUIRY_TO", "lipnicanmilos@gmail.com")

    safe_name = (name or "—").strip()
    safe_email = (email or "—").strip()
    safe_msg = (message or "").strip()
    safe_page = (page or "—").strip()

    subject = f"📩 Nový dotaz na LexiNova od {safe_name}"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
        <h2 style="color: #4F46E5;">Nový dotaz z LexiNova</h2>
        <table style="width:100%; border-collapse:collapse;">
            <tr><td style="padding:6px 0; color:#888;">Meno:</td><td style="padding:6px 0;"><strong>{safe_name}</strong></td></tr>
            <tr><td style="padding:6px 0; color:#888;">E-mail:</td><td style="padding:6px 0;"><strong>{safe_email}</strong></td></tr>
            <tr><td style="padding:6px 0; color:#888;">Stránka:</td><td style="padding:6px 0;">{safe_page}</td></tr>
        </table>
        <div style="margin-top:16px; padding:16px; background:#f5f5f7; border-radius:8px; white-space:pre-wrap;">{safe_msg}</div>
        <p style="margin-top:24px;">
            <a href="https://lexinova-1096007793591.us-central1.run.app/admin"
               style="background-color:#4F46E5; color:white; padding:10px 20px;
                      text-decoration:none; border-radius:6px; display:inline-block;">
                Otvoriť admin
            </a>
        </p>
        <p style="margin-top:24px; color:#888; font-size:12px;">Tím LexiNova</p>
    </body>
    </html>
    """

    msg_obj = MIMEMultipart("alternative")
    msg_obj["Subject"] = subject
    msg_obj["From"] = mail_from
    msg_obj["To"] = to_email
    if safe_email and "@" in safe_email:
        msg_obj["Reply-To"] = safe_email
    msg_obj.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_from, to_email, msg_obj.as_string())
        print(f"Inquiry notification sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send inquiry notification: {e}")
        # Neblokujeme uloženie dotazu, ak sa email neodošle
        return False
