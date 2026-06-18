from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import redis
import json
import os
import smtplib
import threading
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ShopNest Notification Service",
    description="Handles all notifications via Redis Pub/Sub",
    version="1.0.0"
)

# Config
REDIS_URL = REDIS_URL = os.getenv("REDIS_URL")
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USER = os.environ.get('EMAIL_USER', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


# ── Email sender ──
def send_email(to_email: str, subject: str, body: str):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        logger.info(f"[EMAIL MOCK] To: {to_email} | Subject: {subject}")
        logger.info(f"[EMAIL MOCK] Body: {body}")
        return True
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


# ── Email templates ──
def product_created_email(product_name: str, product_id: int) -> str:
    return f"""
    <html><body style="font-family:Arial;padding:20px;background:#f5f5f5;">
    <div style="max-width:600px;margin:0 auto;background:white;border-radius:10px;padding:30px;">
        <h2 style="color:#6c63ff;">✅ Product Created Successfully!</h2>
        <p>Your product <strong>{product_name}</strong> has been added to ShopNest.</p>
        <div style="background:#f0f0ff;padding:15px;border-radius:8px;margin:20px 0;">
            <p><strong>Product ID:</strong> #{product_id}</p>
            <p><strong>Name:</strong> {product_name}</p>
        </div>
        <p style="color:#666;">Thank you for using ShopNest! 🚀</p>
    </div>
    </body></html>
    """

def low_stock_email(product_name: str, stock: int) -> str:
    return f"""
    <html><body style="font-family:Arial;padding:20px;background:#f5f5f5;">
    <div style="max-width:600px;margin:0 auto;background:white;border-radius:10px;padding:30px;">
        <h2 style="color:#f87171;">⚠️ Low Stock Alert!</h2>
        <p>Product <strong>{product_name}</strong> is running low on stock.</p>
        <div style="background:#fff0f0;padding:15px;border-radius:8px;margin:20px 0;border-left:4px solid #f87171;">
            <p><strong>Current Stock:</strong> {stock} units remaining</p>
        </div>
        <p>Please restock soon to avoid stockouts!</p>
    </div>
    </body></html>
    """


# ── Redis Pub/Sub listener ──
def redis_listener():
    logger.info("🔔 Notification Service — Redis listener started!")
    pubsub = redis_client.pubsub()
    pubsub.subscribe('product-events')

    for message in pubsub.listen():
        if message['type'] != 'message':
            continue
        try:
            data = json.loads(message['data'])
            event = data.get('event')
            user_email = data.get('user_email', '')

            logger.info(f"Event received: {event}")

            if event == 'product_created':
                subject = f"✅ Product '{data['product_name']}' Created!"
                body = product_created_email(
                    data['product_name'],
                    data['product_id']
                )
                send_email(user_email, subject, body)

            elif event == 'low_stock_alert':
                subject = f"⚠️ Low Stock: {data['product_name']}"
                body = low_stock_email(
                    data['product_name'],
                    data['stock']
                )
                send_email(user_email, subject, body)

        except Exception as e:
            logger.error(f"Error processing event: {e}")


# Start listener in background thread
@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=redis_listener, daemon=True)
    thread.start()
    logger.info("✅ Notification Service started!")


# ── REST endpoints ──
class DirectNotification(BaseModel):
    to_email: str
    subject: str
    body: str

@app.post("/api/notifications/send")
def send_direct_notification(
    notification: DirectNotification,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(
        send_email,
        notification.to_email,
        notification.subject,
        notification.body
    )
    return {"message": "Notification queued!"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "notification-service"}