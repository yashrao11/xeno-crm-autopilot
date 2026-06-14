import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
import httpx

from app.models import Campaign, Customer, CommunicationLog, Product
from app.routers.customers import build_customer_persona, preload_customer_data

logger = logging.getLogger("CampaignDispatcher")

async def dispatch_campaign_to_targets(
    campaign_id: int, 
    session: Session,
    customer_ids: Optional[List[int]] = None,
    message_template: Optional[str] = None,
    discount_rate: Optional[float] = None,
    channel: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves target customers (either custom segment or matching campaign target tier) and
    dispatches personalized marketing messages to the Channel Service.
    
    Returns details of all dispatched logs for live progress tracking.
    """
    logger.info(f"Retrieving target list for Campaign {campaign_id}...")
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        logger.error(f"Campaign with ID {campaign_id} not found.")
        return []
        
    active_channel = channel if channel is not None else campaign.channel
    active_discount = discount_rate if discount_rate is not None else campaign.discount_rate
    
    # 1. Retrieve the list of customers to evaluate
    if customer_ids is not None:
        statement = select(Customer).where(Customer.id.in_(customer_ids))
        customers = session.exec(statement).all()
    else:
        statement = select(Customer).where(Customer.relationship_tier == campaign.target_tier)
        customers = session.exec(statement).all()
        
    # Bulk preload database records
    preload_ids = [c.id for c in customers]
    orders_cache, latest_log_cache = preload_customer_data(preload_ids, session)
    
    # 2. Filter targets (checking WhatsApp blocks and replenishment status if legacy run)
    targets = []
    for customer in customers:
        if active_channel == "WhatsApp" and customer.is_blocked_on_whatsapp:
            logger.info(f"Skipping customer {customer.id} for WhatsApp campaign (WhatsApp is blocked)")
            continue
            
        persona = build_customer_persona(
            customer, 
            session, 
            orders=orders_cache.get(customer.id, []), 
            latest_log=latest_log_cache.get(customer.id)
        )
        
        if customer_ids is not None:
            # Explicitly target this custom segment customer
            targets.append((customer, persona))
        else:
            # Legacy replenishment campaign check
            status = persona.replenishment_metrics.replenishment_status
            if status in ["Due Soon", "Overdue"]:
                targets.append((customer, persona))
                
    logger.info(f"Found {len(targets)} target customers for Campaign {campaign_id}")
    if not targets:
        return []
        
    # 3. Create communication logs in bulk first
    logs_to_send = []
    for customer, persona in targets:
        log = CommunicationLog(
            campaign_id=campaign.id,
            customer_id=customer.id,
            channel_used=active_channel,
            sent_at=datetime.utcnow(),
            status="sent"
        )
        session.add(log)
        logs_to_send.append((log, customer, persona))
        
    session.commit()
    
    # 4. Prepare message payloads
    payloads = []
    dispatched_log_details = []
    
    for log, customer, persona in logs_to_send:
        last_prod = persona.replenishment_metrics.last_product_name or "favorite items"
        discount_pct = int(active_discount * 100)
        
        # Apply custom template parsing
        if message_template:
            content = message_template.replace("{customer_name}", customer.name)\
                                      .replace("{product_name}", last_prod)\
                                      .replace("{discount_percent}", str(discount_pct))\
                                      .replace("{campaign_name}", campaign.name)
        else:
            content = f"Hi {customer.name}, time to replenish your {last_prod}! Use code {campaign.name} to get {discount_pct}% off."
            
        recipient = customer.email if active_channel == "Email" else customer.phone
        
        payload = {
            "message_id": log.id,
            "recipient_phone_or_email": recipient,
            "channel": active_channel,
            "content": content,
            "callback_url": "http://localhost:8000/api/webhooks/receipt"
        }
        payloads.append(payload)
        
        # Track log detail
        dispatched_log_details.append({
            "message_id": log.id,
            "customer_id": customer.id,
            "customer_name": customer.name,
            "channel": active_channel,
            "content": content,
            "status": "sent"
        })
        
    # 5. Dispatch payloads concurrently
    async with httpx.AsyncClient() as client:
        async def send_message(payload):
            try:
                logger.info(f"Dispatching message {payload['message_id']} to Channel Service ({active_channel})...")
                response = await client.post("http://localhost:8001/channel/send", json=payload, timeout=10.0)
                if response.status_code != 202:
                    logger.error(f"Channel Service returned error code {response.status_code} for message {payload['message_id']}")
            except Exception as e:
                logger.error(f"Failed to dispatch message {payload['message_id']} to Channel Service: {e}")
                
        tasks = [send_message(p) for p in payloads]
        await asyncio.gather(*tasks)
        
    return dispatched_log_details
