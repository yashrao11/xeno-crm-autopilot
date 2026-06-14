from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel

class ReplenishmentMetrics(BaseModel):
    last_order_id: Optional[int] = None
    last_order_date: Optional[datetime] = None
    last_product_id: Optional[int] = None
    last_product_name: Optional[str] = None
    estimated_lifespan_days: Optional[int] = None
    days_since_last_purchase: Optional[int] = None
    predicted_empty_date: Optional[datetime] = None
    days_until_empty: Optional[int] = None
    replenishment_status: str

class CustomerPersona(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    created_at: datetime
    acquisition_source: str
    favoured_social_channel: str
    relationship_tier: str
    preferred_channel: str
    is_blocked_on_whatsapp: bool
    favoured_shopping_method: str
    region: str
    
    # Aggregated & Predictive Metrics
    total_orders: int
    lifetime_spend: float
    replenishment_metrics: ReplenishmentMetrics
    
    # Campaign Communication History
    last_campaign_name: Optional[str] = None
    last_campaign_sent_at: Optional[datetime] = None
    last_campaign_status: Optional[str] = None
    last_campaign_reply: Optional[str] = None
    last_campaign_reply_sentiment: Optional[str] = None

    class Config:
        from_attributes = True

class SegmentQuery(BaseModel):
    region: Optional[str] = None
    acquisition_source: Optional[str] = None
    relationship_tier: Optional[str] = None
    favoured_shopping_method: Optional[str] = None
    replenishment_status: Optional[str] = None
    preferred_channel: Optional[str] = None
    
    # Dynamic segmentation filters parsed by Groq
    product_id: Optional[int] = None
    category: Optional[str] = None
    campaign_id: Optional[int] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    has_discount: Optional[bool] = None

class CampaignRunRequest(BaseModel):
    customer_ids: Optional[List[int]] = None
    message_template: Optional[str] = None
    discount_rate: Optional[float] = None
    channel: Optional[str] = None

class CustomCampaignRunRequest(BaseModel):
    name: str
    campaign_type: str = "Replenishment"
    channel: str
    discount_rate: float
    message_template: str
    customer_ids: List[int]

class SegmentResult(BaseModel):
    total_matched: int
    total_spend: float
    region_breakdown: Dict[str, int]
    shopping_method_breakdown: Dict[str, int]
    customers: List[CustomerPersona]

class CampaignCreate(BaseModel):
    name: str
    campaign_type: str  # "Replenishment", "Feedback", "Cross_Sell", "Loyalty"
    target_tier: str    # "Early" or "Loyal"
    channel: str        # "WhatsApp", "Email", "SMS", "Instagram"
    discount_rate: float

class CampaignResponse(CampaignCreate):
    id: int

    class Config:
        from_attributes = True

class ProductShort(BaseModel):
    id: int
    name: str
    category: str
    price: float

    class Config:
        from_attributes = True

class CampaignTarget(BaseModel):
    customer: CustomerPersona
    recommended_product: Optional[ProductShort] = None
