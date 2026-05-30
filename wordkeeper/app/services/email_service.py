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

    subject = "Vitaj v WordKeeper! 🎉"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
        <h2 style="color: #4F46E5;">Vitaj v WordKeeper, {name}! 👋</h2>
        <p>Sme radi, že si sa zaregistroval/a. Teraz môžeš začať učiť sa nové slovíčka.</p>
        <p>Čo môžeš robiť:</p>
        <ul>
            <li>Vytvárať kategórie slovíčok</li>
            <li>Testovať svoje znalosti</li>
            <li>Sledovať svoj pokrok</li>
        </ul>
        <a href="https://wordkeeper-1096007793591.us-central1.run.app/dashboard" 
           style="background-color: #4F46E5; color: white; padding: 12px 24px; 
                  text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 16px;">
            Začať učiť sa
        </a>
        <p style="margin-top: 32px; color: #888; font-size: 12px;">
            Tím WordKeeper
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