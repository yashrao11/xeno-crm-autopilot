import os
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session, select
import httpx

from app.database import get_session, engine
from app.models import Customer, Campaign, CommunicationLog

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CRMWebhooks")

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

class WebhookPayload(BaseModel):
    message_id: int
    status: str
    customer_reply: Optional[str] = None

def analyze_sentiment(reply: str) -> str:
    reply_lower = reply.lower()
    negative_keywords = ["stop", "unsubscribe", "block", "remove", "no", "expensive", "bad", "hate", "cancel", "dont like", "don't like"]
    positive_keywords = ["like", "love", "thanks", "thank you", "great", "yes", "more", "awesome", "good", "perfect", "interested"]
    
    for word in negative_keywords:
        if word in reply_lower:
            return "Negative"
    for word in positive_keywords:
        if word in reply_lower:
            return "Positive"
    return "Neutral"

async def trigger_email_fallback(customer_id: int, campaign_id: int, original_content: str):
    logger.info(f"Starting Email fallback for Customer {customer_id}, Campaign {campaign_id}...")
    
    # 1. Execute DB changes in a localized session block
    with Session(engine) as session:
        customer = session.get(Customer, customer_id)
        campaign = session.get(Campaign, campaign_id)
        if not customer or not campaign:
            logger.error(f"Fallback aborted: Customer {customer_id} or Campaign {campaign_id} not found")
            return
            
        # Create a new fallback communication log
        fallback_log = CommunicationLog(
            campaign_id=campaign_id,
            customer_id=customer_id,
            channel_used="Email",
            sent_at=datetime.utcnow(),
            status="sent"
        )
        session.add(fallback_log)
        session.commit()
        session.refresh(fallback_log)
        
        # Read attributes before closing the session to prevent lazy-loading issues
        customer_name = customer.name
        customer_email = customer.email
        campaign_name = campaign.name
        discount_rate = campaign.discount_rate
        log_id = fallback_log.id

    # Session closed, connection returned to QueuePool
    fallback_content = f"Hi {customer_name}, we couldn't reach you on WhatsApp. Here is your campaign fallback: {campaign_name}! Discount: {int(discount_rate * 100)}%."
    
    callback_url = os.getenv("CRM_CALLBACK_URL", "http://localhost:8000/api/webhooks/receipt")
    payload = {
        "message_id": log_id,
        "recipient_phone_or_email": customer_email,
        "channel": "Email",
        "content": fallback_content,
        "callback_url": callback_url
    }
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Dispatching fallback message {log_id} to Channel Stub...")
            channel_service_url = os.getenv("CHANNEL_SERVICE_URL", "http://localhost:8001/channel/send")
            response = await client.post(channel_service_url, json=payload, timeout=5.0)
            logger.info(f"Fallback dispatch result status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to dispatch fallback message to channel stub: {e}")

@router.post("/receipt")
def receive_receipt(payload: WebhookPayload, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    logger.info(f"Received webhook callback for message {payload.message_id}. Status: {payload.status}")
    
    log = session.get(CommunicationLog, payload.message_id)
    if not log:
        logger.error(f"Communication log with ID {payload.message_id} not found.")
        session.close()
        return {"status": "error", "detail": "Log not found"}
        
    # Update log status
    log.status = payload.status
    
    # Analyze sentiment if customer replied
    sentiment = None
    if payload.status == "replied" and payload.customer_reply:
        log.customer_reply = payload.customer_reply
        sentiment = analyze_sentiment(payload.customer_reply)
        log.reply_sentiment = sentiment
        logger.info(f"Parsed sentiment for reply: '{payload.customer_reply}' -> {sentiment}")
        
    session.add(log)
    session.commit()
    
    # WhatsApp Block Mitigation Rule
    is_whatsapp = (log.channel_used == "WhatsApp")
    is_failed = (payload.status == "failed")
    is_negative = (sentiment == "Negative")
    
    if is_whatsapp and (is_failed or is_negative):
        logger.info(f"WhatsApp block trigger activated for Customer {log.customer_id} (Reason: Failed={is_failed}, Negative={is_negative})")
        
        customer = session.get(Customer, log.customer_id)
        if customer:
            customer.is_blocked_on_whatsapp = True
            customer.preferred_channel = "Email"
            session.add(customer)
            session.commit()
            logger.info(f"Customer {customer.id} blocked on WhatsApp. Preferred channel switched to Email.")
            
            # Capture variables for fallback background task
            cust_id = customer.id
            camp_id = log.campaign_id
            
            # Close session before yielding to background task to free connection immediately
            session.close()
            
            # Trigger background task for email fallback
            original_content = f"Campaign: {camp_id}"
            background_tasks.add_task(trigger_email_fallback, cust_id, camp_id, original_content)
            return {"status": "success", "detail": "Callback receipt processed successfully"}
            
    session.close()
    return {"status": "success", "detail": "Callback receipt processed successfully"}

@router.get("/recent")
def get_recent_receipts(limit: int = 15, session: Session = Depends(get_session)):
    statement = (
        select(CommunicationLog, Customer.name, Campaign.name)
        .join(Customer, Customer.id == CommunicationLog.customer_id)
        .join(Campaign, Campaign.id == CommunicationLog.campaign_id)
        .order_by(CommunicationLog.sent_at.desc())
        .limit(limit)
    )
    results = session.exec(statement).all()
    
    log_list = []
    for log, cust_name, camp_name in results:
        log_list.append({
            "id": log.id,
            "campaign_id": log.campaign_id,
            "campaign_name": camp_name,
            "customer_id": log.customer_id,
            "customer_name": cust_name,
            "channel_used": log.channel_used,
            "sent_at": log.sent_at,
            "status": log.status,
            "customer_reply": log.customer_reply,
            "reply_sentiment": log.reply_sentiment
        })
    return log_list
