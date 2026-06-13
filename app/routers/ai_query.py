from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from app.database import get_session
from app.schemas import SegmentQuery, SegmentResult
from app.routers.analytics import segment_customers
from app.services.ai_query import translate_natural_language_to_filters

router = APIRouter(prefix="/api/ai", tags=["AI Copilot"])

class AIQueryRequest(BaseModel):
    query: str

class AIQueryResponse(BaseModel):
    query: str
    filters: dict
    result: SegmentResult

@router.post("/query", response_model=AIQueryResponse)
def run_ai_search(request: AIQueryRequest, session: Session = Depends(get_session)):
    # 1. Translate NL query to filters
    filters_dict = translate_natural_language_to_filters(request.query, session)
    
    # Save a copy for the output response representation
    output_filters = dict(filters_dict)
    
    # Extract custom filters so they don't break static query filters
    product_filter = filters_dict.pop("product_name", None)
    overdue_days_filter = filters_dict.pop("overdue_days", None)
    
    # 2. Convert to SegmentQuery model
    segment_filters = SegmentQuery(**filters_dict)
    
    # 3. Call segment_customers router function
    result = segment_customers(segment_filters, session)
    
    # 4. Apply custom filters in Python on returned personas
    filtered_customers = []
    total_spend = 0.0
    region_breakdown = {}
    shopping_method_breakdown = {}
    
    for customer in result.customers:
        # Check product name match
        if product_filter:
            if customer.replenishment_metrics.last_product_name != product_filter:
                continue
                
        # Check overdue days threshold (e.g. overdue by 15+ days -> days_until_empty <= -15)
        if overdue_days_filter:
            days_until_empty = customer.replenishment_metrics.days_until_empty
            if days_until_empty is None or days_until_empty > -overdue_days_filter:
                continue
                
        filtered_customers.append(customer)
        total_spend += customer.lifetime_spend
        
        region = customer.region
        method = customer.favoured_shopping_method
        region_breakdown[region] = region_breakdown.get(region, 0) + 1
        shopping_method_breakdown[method] = shopping_method_breakdown.get(method, 0) + 1
        
    # Re-assign updated cohort aggregates
    result.customers = filtered_customers
    result.total_matched = len(filtered_customers)
    result.total_spend = round(total_spend, 2)
    result.region_breakdown = region_breakdown
    result.shopping_method_breakdown = shopping_method_breakdown
    
    return AIQueryResponse(
        query=request.query,
        filters=output_filters,
        result=result
    )
