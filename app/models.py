from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship

# Define SQLModel base classes or models

class Product(SQLModel, table=True):
    __tablename__ = "products"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    category: str = Field(index=True)
    price: float
    estimated_lifespan_days: int

    # Relationships
    orders: List["Order"] = Relationship(back_populates="product")


class Customer(SQLModel, table=True):
    __tablename__ = "customers"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    phone: str = Field(unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acquisition_source: str = Field(index=True)  # e.g., "Facebook Ads", "Google"
    favoured_social_channel: str
    relationship_tier: str = Field(default="Early")  # "Early" or "Loyal"
    preferred_channel: str
    is_blocked_on_whatsapp: bool = Field(default=False)
    favoured_shopping_method: str = Field(default="Website")  # "Store", "Website", "App"
    region: str = Field(default="North", index=True)

    # Relationships
    orders: List["Order"] = Relationship(back_populates="customer")
    communication_logs: List["CommunicationLog"] = Relationship(back_populates="customer")


class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    campaign_type: str  # "Replenishment", "Feedback", "Cross_Sell", "Loyalty"
    target_tier: str  # "Early", "Loyal", or "All"
    channel: str  # "WhatsApp", "Email", "SMS"
    discount_rate: float = Field(default=0.0)

    # Relationships
    orders: List["Order"] = Relationship(back_populates="campaign")
    communication_logs: List["CommunicationLog"] = Relationship(back_populates="campaign")


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customers.id", index=True)
    order_date: datetime = Field(index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    quantity: int = Field(default=1)
    total_amount: float
    attributed_campaign_id: Optional[int] = Field(default=None, foreign_key="campaigns.id", nullable=True, index=True)

    # Relationships
    customer: Optional["Customer"] = Relationship(back_populates="orders")
    product: Optional["Product"] = Relationship(back_populates="orders")
    campaign: Optional["Campaign"] = Relationship(back_populates="orders")


class CommunicationLog(SQLModel, table=True):
    __tablename__ = "communication_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaigns.id", index=True)
    customer_id: int = Field(foreign_key="customers.id", index=True)
    channel_used: str  # "WhatsApp", "Email", "SMS"
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    status: str  # "sent", "delivered", "failed", "opened", "read", "clicked", "replied"
    customer_reply: Optional[str] = Field(default=None, nullable=True)
    reply_sentiment: Optional[str] = Field(default=None, nullable=True)

    # Relationships
    campaign: Optional["Campaign"] = Relationship(back_populates="communication_logs")
    customer: Optional["Customer"] = Relationship(back_populates="communication_logs")
