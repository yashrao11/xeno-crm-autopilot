from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from app.database import get_session
from app.models import Customer, Order, Campaign, CommunicationLog
from app.schemas import CustomerPersona, ReplenishmentMetrics
from app.services.replenishment import calculate_replenishment_metrics

router = APIRouter(prefix="/api/customers", tags=["Customers"])

def preload_customer_data(customer_ids: List[int], session: Session) -> tuple[Dict[int, List[Order]], Dict[int, tuple]]:
    """
    Preloads orders and latest communication logs for a collection of customer IDs in bulk.
    Safe from SQLite parameter count limits by chunking execution.
    """
    if not customer_ids:
        return {}, {}
        
    orders_cache = {}
    latest_log_cache = {}
    chunk_size = 900
    
    for i in range(0, len(customer_ids), chunk_size):
        chunk = customer_ids[i:i+chunk_size]
        
        # 1. Fetch orders for this chunk
        orders_stmt = select(Order).where(Order.customer_id.in_(chunk))
        orders = session.exec(orders_stmt).all()
        for o in orders:
            if o.customer_id not in orders_cache:
                orders_cache[o.customer_id] = []
            orders_cache[o.customer_id].append(o)
            
        # 2. Fetch all logs for this chunk, ordered by sent_at desc so the first seen is the latest
        log_stmt = (
            select(CommunicationLog, Campaign.name)
            .join(Campaign, Campaign.id == CommunicationLog.campaign_id)
            .where(CommunicationLog.customer_id.in_(chunk))
            .order_by(CommunicationLog.sent_at.desc())
        )
        all_logs = session.exec(log_stmt).all()
        for log, campaign_name in all_logs:
            if log.customer_id not in latest_log_cache:
                latest_log_cache[log.customer_id] = (log, campaign_name)
                
    return orders_cache, latest_log_cache

def build_customer_persona(
    customer: Customer, 
    session: Session,
    orders: Optional[List[Order]] = None,
    latest_log: Optional[tuple] = None
) -> CustomerPersona:
    # Query all orders for aggregation if not preloaded
    if orders is None:
        orders_statement = select(Order).where(Order.customer_id == customer.id)
        orders = session.exec(orders_statement).all()
    
    total_orders = len(orders)
    lifetime_spend = sum(o.total_amount for o in orders)
    
    # Calculate replenishment metrics
    latest_order = None
    if orders:
        latest_order = max(orders, key=lambda o: o.order_date)
        
    metrics_dict = calculate_replenishment_metrics(customer.id, session, latest_order=latest_order)
    replenishment_metrics = ReplenishmentMetrics(**metrics_dict)
    
    # Query most recent campaign communication log if not preloaded
    if latest_log is None:
        log_stmt = (
            select(CommunicationLog, Campaign.name)
            .join(Campaign, Campaign.id == CommunicationLog.campaign_id)
            .where(CommunicationLog.customer_id == customer.id)
            .order_by(CommunicationLog.sent_at.desc())
            .limit(1)
        )
        latest_log = session.exec(log_stmt).first()
    
    last_campaign_name = None
    last_campaign_sent_at = None
    last_campaign_status = None
    last_campaign_reply = None
    last_campaign_reply_sentiment = None
    
    if latest_log:
        log, campaign_name = latest_log
        last_campaign_name = campaign_name
        last_campaign_sent_at = log.sent_at
        last_campaign_status = log.status
        last_campaign_reply = log.customer_reply
        last_campaign_reply_sentiment = log.reply_sentiment
    
    return CustomerPersona(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        created_at=customer.created_at,
        acquisition_source=customer.acquisition_source,
        favoured_social_channel=customer.favoured_social_channel,
        relationship_tier=customer.relationship_tier,
        preferred_channel=customer.preferred_channel,
        is_blocked_on_whatsapp=customer.is_blocked_on_whatsapp,
        favoured_shopping_method=customer.favoured_shopping_method,
        region=customer.region,
        total_orders=total_orders,
        lifetime_spend=round(lifetime_spend, 2),
        replenishment_metrics=replenishment_metrics,
        last_campaign_name=last_campaign_name,
        last_campaign_sent_at=last_campaign_sent_at,
        last_campaign_status=last_campaign_status,
        last_campaign_reply=last_campaign_reply,
        last_campaign_reply_sentiment=last_campaign_reply_sentiment
    )

@router.get("/{id}", response_model=CustomerPersona)
def get_customer(id: int, session: Session = Depends(get_session)):
    customer = session.get(Customer, id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with ID {id} not found")
    
    return build_customer_persona(customer, session)

@router.get("", response_model=List[CustomerPersona])
def list_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session)
):
    statement = select(Customer).offset(skip).limit(limit)
    customers = session.exec(statement).all()
    
    customer_ids = [c.id for c in customers]
    orders_cache, latest_log_cache = preload_customer_data(customer_ids, session)
    
    return [
        build_customer_persona(
            c, 
            session, 
            orders=orders_cache.get(c.id, []), 
            latest_log=latest_log_cache.get(c.id)
        ) 
        for c in customers
    ]
