import logging
import asyncio
from datetime import datetime, timezone
from sqlmodel import Session, select
import httpx

from app.models import Campaign, Customer, CommunicationLog, Product
from app.routers.customers import build_customer_persona, preload_customer_data

logger = logging.getLogger("CampaignDispatcher")

async def dispatch_campaign_to_targets(campaign_id: int, session: Session) -> int:
    """
    Retrieves target customers for a campaign and dispatches personalized payloads to the Mock Channel Service.
    
    Returns the number of messages successfully sent.
    """
    logger.info(f"Retrieving target list for Campaign {campaign_id}...")
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        logger.error(f"Campaign with ID {campaign_id} not found.")
        return 0
        
    # Query customers in the target tier
    statement = select(Customer).where(Customer.relationship_tier == campaign.target_tier)
    customers = session.exec(statement).all()
    
    # Bulk preload database records
    customer_ids = [c.id for c in customers]
    orders_cache, latest_log_cache = preload_customer_data(customer_ids, session)
    
    # Filter customers who are Due Soon or Overdue
    targets = []
    for customer in customers:
        # Check if the customer is blocked on WhatsApp for WhatsApp campaigns
        if campaign.channel == "WhatsApp" and customer.is_blocked_on_whatsapp:
            logger.info(f"Skipping customer {customer.id} for WhatsApp campaign (WhatsApp is blocked)")
            continue
            
        persona = build_customer_persona(
            customer, 
            session, 
            orders=orders_cache.get(customer.id, []), 
            latest_log=latest_log_cache.get(customer.id)
        )
        status = persona.replenishment_metrics.replenishment_status
        if status in ["Due Soon", "Overdue"]:
            targets.append((customer, persona))
            
    logger.info(f"Found {len(targets)} target customers for Campaign {campaign_id}")
    if not targets:
        return 0
        
    # Create all communication logs in bulk first to avoid slow synchronous commits
    logs_to_send = []
    for customer, persona in targets:
        log = CommunicationLog(
            campaign_id=campaign.id,
            customer_id=customer.id,
            channel_used=campaign.channel,
            sent_at=datetime.utcnow(),
            status="sent"
        )
        session.add(log)
        logs_to_send.append((log, customer, persona))
        
    # Single-transaction commit (extremely fast)
    session.commit()
    
    # Prepare payloads using the generated log IDs synchronously to prevent threading/session issues
    payloads = []
    for log, customer, persona in logs_to_send:
        last_prod = persona.replenishment_metrics.last_product_name or "favorite items"
        discount_pct = int(campaign.discount_rate * 100)
        content = f"Hi {customer.name}, time to replenish your {last_prod}! Use code {campaign.name} to get {discount_pct}% off."
        recipient = customer.email if campaign.channel == "Email" else customer.phone
        
        payloads.append({
            "message_id": log.id,
            "recipient_phone_or_email": recipient,
            "channel": campaign.channel,
            "content": content,
            "callback_url": "http://localhost:8000/api/webhooks/receipt"
        })
        
    sent_count = 0
    async with httpx.AsyncClient() as client:
        # Dispatch webhook requests concurrently in tasks
        async def send_message(payload):
            nonlocal sent_count
            try:
                logger.info(f"Dispatching message {payload['message_id']} to Channel Service ({campaign.channel})...")
                response = await client.post("http://localhost:8001/channel/send", json=payload, timeout=10.0)
                if response.status_code == 202:
                    sent_count += 1
                else:
                    logger.error(f"Channel Service returned error code {response.status_code} for message {payload['message_id']}")
            except Exception as e:
                logger.error(f"Failed to dispatch message {payload['message_id']} to Channel Service: {e}")
                
        # Run all send tasks concurrently
        tasks = [send_message(p) for p in payloads]
        await asyncio.gather(*tasks)
            
    logger.info(f"Dispatched {sent_count} of {len(targets)} messages for Campaign {campaign_id}")
    return sent_count
