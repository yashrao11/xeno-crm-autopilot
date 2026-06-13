import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from app.database import engine
from app.models import Customer, Order, Product
from openai import OpenAI

router = APIRouter()

# Initialize OpenAI client if key is set
api_key = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=api_key) if api_key else None

class QueryRequest(BaseModel):
    prompt: str

class QueryResponse(BaseModel):
    customers: List[Dict[str, Any]]
    regional_breakdown: Dict[str, int]
    channel_breakdown: Dict[str, int]
    tier_breakdown: Dict[str, int]

@router.post("/api/ai/query", response_model=QueryResponse)
def query_customers_by_nlp(request: QueryRequest):
    if not client:
        # Safe fallback search if no OpenAI Key is present (prevents system crashes)
        with Session(engine) as session:
            stmt = select(Customer).limit(50)
            results = session.exec(stmt).all()
            return format_response(results, session)

    # 1. Instruct the LLM to return parsed filter JSON parameters
    system_instruction = (
        "You are an assistant that parses natural language queries for a retail CRM into structured filter options.\n"
        "Analyze the user prompt and return ONLY a JSON block containing these filter keys if mentioned:\n"
        "- relationship_tier: 'Early' or 'Loyal'\n"
        "- acquisition_source: 'Instagram Ads', 'Facebook Ads', 'Google Search', 'Organic Referral'\n"
        "- preferred_channel: 'WhatsApp', 'Email', 'SMS'\n"
        "- region: 'Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad'\n"
        "Return empty fields for filters not explicitly mentioned. Output strictly raw valid JSON."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": request.prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        filters = json.loads(completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Parsing failed: {str(e)}")

    # 2. Build dynamic database query based on LLM filters
    with Session(engine) as session:
        query = select(Customer)
        if filters.get("relationship_tier"):
            query = query.where(Customer.relationship_tier == filters["relationship_tier"])
        if filters.get("acquisition_source"):
            query = query.where(Customer.acquisition_source == filters["acquisition_source"])
        if filters.get("preferred_channel"):
            query = query.where(Customer.preferred_channel == filters["preferred_channel"])
        # Simple string matching for region/phone indicators
        if filters.get("region"):
            query = query.where(Customer.email.contains(filters["region"].lower()) | Customer.phone.contains(filters["region"]))

        results = session.exec(query.limit(100)).all() # Limit results to prevent UI lag
        return format_response(results, session)

def format_response(customers: List[Customer], session: Session) -> Dict[str, Any]:
    formatted_list = []
    regions = {}
    channels = {}
    tiers = {"Early": 0, "Loyal": 0}

    for cust in customers:
        # Calculate dynamic metrics for display
        orders = session.query(Order).filter(Order.customer_id == cust.id).all()
        total_spent = sum(o.total_amount for o in orders)
        
        # Categorizations
        channels[cust.preferred_channel] = channels.get(cust.preferred_channel, 0) + 1
        tiers[cust.relationship_tier] = tiers.get(cust.relationship_tier, 0) + 1

        formatted_list.append({
            "id": cust.id,
            "name": cust.name,
            "email": cust.email,
            "phone": cust.phone,
            "tier": cust.relationship_tier,
            "preferred_channel": cust.preferred_channel,
            "total_orders": len(orders),
            "total_spent": round(total_spent, 2)
        })

    return {
        "customers": formatted_list,
        "regional_breakdown": regions,
        "channel_breakdown": channels,
        "tier_breakdown": tiers
    }