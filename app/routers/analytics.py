from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.database import get_session
from app.models import Customer
from app.schemas import SegmentQuery, SegmentResult
from app.routers.customers import build_customer_persona, preload_customer_data

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.post("/segment", response_model=SegmentResult)
def segment_customers(query_filters: SegmentQuery, session: Session = Depends(get_session)):
    query = select(Customer)
    
    # Dynamically apply filters if they are provided
    if query_filters.region:
        query = query.where(Customer.region == query_filters.region)
    if query_filters.acquisition_source:
        query = query.where(Customer.acquisition_source == query_filters.acquisition_source)
    if query_filters.relationship_tier:
        query = query.where(Customer.relationship_tier == query_filters.relationship_tier)
    if query_filters.favoured_shopping_method:
        query = query.where(Customer.favoured_shopping_method == query_filters.favoured_shopping_method)
    if query_filters.preferred_channel:
        query = query.where(Customer.preferred_channel == query_filters.preferred_channel)
        
    customers = session.exec(query).all()
    
    # Bulk preload database records
    customer_ids = [c.id for c in customers]
    orders_cache, latest_log_cache = preload_customer_data(customer_ids, session)
    
    matched_customers = []
    region_breakdown = {}
    shopping_method_breakdown = {}
    total_spend = 0.0
    
    for customer in customers:
        # Build customer persona using cached data
        persona = build_customer_persona(
            customer, 
            session, 
            orders=orders_cache.get(customer.id, []), 
            latest_log=latest_log_cache.get(customer.id)
        )
        
        # Filter by replenishment status in Python since it's a dynamic calculated field
        if query_filters.replenishment_status:
            if persona.replenishment_metrics.replenishment_status != query_filters.replenishment_status:
                continue
                
        matched_customers.append(persona)
        
        # Compute breakdowns and aggregate stats
        region = persona.region
        method = persona.favoured_shopping_method
        
        region_breakdown[region] = region_breakdown.get(region, 0) + 1
        shopping_method_breakdown[method] = shopping_method_breakdown.get(method, 0) + 1
        total_spend += persona.lifetime_spend
        
    return SegmentResult(
        total_matched=len(matched_customers),
        total_spend=round(total_spend, 2),
        region_breakdown=region_breakdown,
        shopping_method_breakdown=shopping_method_breakdown,
        customers=matched_customers
    )
