from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import Campaign, Customer, Product
from app.schemas import CampaignCreate, CampaignResponse, CampaignTarget, ProductShort
from app.routers.customers import build_customer_persona, preload_customer_data
from app.services.dispatcher import dispatch_campaign_to_targets

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

@router.post("", response_model=CampaignResponse)
def create_campaign(campaign_in: CampaignCreate, session: Session = Depends(get_session)):
    campaign = Campaign(
        name=campaign_in.name,
        campaign_type=campaign_in.campaign_type,
        target_tier=campaign_in.target_tier,
        channel=campaign_in.channel,
        discount_rate=campaign_in.discount_rate
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign

@router.get("/{id}/targets", response_model=List[CampaignTarget])
def get_campaign_targets(id: int, session: Session = Depends(get_session)):
    campaign = session.get(Campaign, id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign with ID {id} not found")
        
    # Query customers in the target tier
    statement = select(Customer).where(Customer.relationship_tier == campaign.target_tier)
    customers = session.exec(statement).all()
    
    # Bulk preload database records
    customer_ids = [c.id for c in customers]
    orders_cache, latest_log_cache = preload_customer_data(customer_ids, session)
    
    targets = []
    for customer in customers:
        persona = build_customer_persona(
            customer, 
            session, 
            orders=orders_cache.get(customer.id, []), 
            latest_log=latest_log_cache.get(customer.id)
        )
        status = persona.replenishment_metrics.replenishment_status
        
        # Target if they are Due Soon or Overdue
        if status in ["Due Soon", "Overdue"]:
            recommended_product = None
            
            # Special Rule for Campaign ID 5 (Cross-Sell)
            if id == 5:
                last_product_id = persona.replenishment_metrics.last_product_id
                
                # Default recommendation
                rec_product_id = 1
                
                if last_product_id:
                    last_product = session.get(Product, last_product_id)
                    if last_product:
                        cat = last_product.category
                        if cat == "Coffee Beans & Accessories":
                            rec_product_id = 6   # French Press
                        elif cat == "Skincare":
                            rec_product_id = 20  # Retinol Eye Cream
                        elif cat == "Apparel":
                            rec_product_id = 21  # Denim Jacket
                
                rec_product = session.get(Product, rec_product_id)
                if rec_product:
                    recommended_product = ProductShort(
                        id=rec_product.id,
                        name=rec_product.name,
                        category=rec_product.category,
                        price=rec_product.price
                    )
            
            targets.append(CampaignTarget(
                customer=persona,
                recommended_product=recommended_product
            ))
            
    return targets

@router.post("/{id}/run")
async def run_campaign(id: int, session: Session = Depends(get_session)):
    campaign = session.get(Campaign, id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign with ID {id} not found")
        
    dispatched_count = await dispatch_campaign_to_targets(id, session)
    return {
        "status": "success",
        "detail": f"Dispatched campaign {id} to {dispatched_count} target customers."
    }
