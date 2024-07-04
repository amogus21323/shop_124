from account.send_email import send_confirmation_email, send_confirmation_password
from .celery import app


@app.task()
def send_confirmation_email_task(email, code):
    send_confirmation_email(email, code)


@app.task()
def send_confirmation_password_task(email, code):
    send_confirmation_password(email, code)
