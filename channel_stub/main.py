import asyncio
import logging
import random
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, status
from pydantic import BaseModel
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChannelStub")

app = FastAPI(
    title="Mock Channel Service Stub",
    description="Simulates sending messages and triggering async status callback webhooks.",
    version="1.0.0"
)

class SendMessageRequest(BaseModel):
    message_id: int
    recipient_phone_or_email: str
    channel: str
    content: str
    callback_url: str

REPLIES_POSITIVE = [
    "Tell me more!",
    "Love this product, just ordered more!",
    "Thanks for the discount!",
    "Great reminder, thank you!"
]
REPLIES_NEUTRAL = [
    "Do you have other sizes?",
    "Can you send the link again?",
    "Is this discount valid in stores?",
    "Will check it out later."
]
REPLIES_NEGATIVE = [
    "Stop texting me",
    "Too expensive",
    "Please unsubscribe me",
    "I didn't like my last order"
]

async def post_webhook(client: httpx.AsyncClient, url: str, payload: dict):
    try:
        logger.info(f"Firing callback to {url} with data: {payload}")
        response = await client.post(url, json=payload, timeout=5.0)
        logger.info(f"Callback response status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send webhook to {url}: {e}")

async def simulate_message_lifecycle(req: SendMessageRequest):
    async with httpx.AsyncClient() as client:
        # Simulate network delay for transmission
        delay = random.uniform(1.0, 4.0)
        logger.info(f"Simulating sending message {req.message_id} on channel {req.channel}. Delay: {delay:.2f}s")
        await asyncio.sleep(delay)
        
        # Transition 1: delivered (95% success) or failed (5% failure)
        is_delivered = random.random() < 0.95
        delivery_status = "delivered" if is_delivered else "failed"
        
        await post_webhook(client, req.callback_url, {
            "message_id": req.message_id,
            "status": delivery_status
        })
        
        if not is_delivered:
            logger.info(f"Message {req.message_id} failed delivery. Stopping cycle.")
            return
            
        # Transition 2: read (70% probability for Email/WhatsApp/RCS, 0% for SMS/Others)
        if req.channel in ["Email", "WhatsApp", "Instagram", "Facebook", "RCS"]:
            await asyncio.sleep(2.0)
            has_read = random.random() < 0.70
            if has_read:
                await post_webhook(client, req.callback_url, {
                    "message_id": req.message_id,
                    "status": "read"
                })
                
                # Transition 3: clicked (30% probability)
                await asyncio.sleep(2.0)
                has_clicked = random.random() < 0.30
                if has_clicked:
                    await post_webhook(client, req.callback_url, {
                        "message_id": req.message_id,
                        "status": "clicked"
                    })
                    
                    # Transition 4: replied (10% probability)
                    await asyncio.sleep(3.0)
                    has_replied = random.random() < 0.10
                    if has_replied:
                        # Select random reply category
                        reply_cat = random.choice(["positive", "neutral", "negative"])
                        if reply_cat == "positive":
                            reply_text = random.choice(REPLIES_POSITIVE)
                        elif reply_cat == "neutral":
                            reply_text = random.choice(REPLIES_NEUTRAL)
                        else:
                            reply_text = random.choice(REPLIES_NEGATIVE)
                            
                        await post_webhook(client, req.callback_url, {
                            "message_id": req.message_id,
                            "status": "replied",
                            "customer_reply": reply_text
                        })

@app.post("/channel/send", status_code=status.HTTP_202_ACCEPTED)
def send_message(req: SendMessageRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received send request for message_id {req.message_id} to {req.recipient_phone_or_email}")
    background_tasks.add_task(simulate_message_lifecycle, req)
    return {"status": "Accepted", "detail": "Message queued for delivery simulation"}
