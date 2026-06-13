from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RelationshipTier(str, Enum):
    EARLY = "Early"
    LOYAL = "Loyal"


class CommunicationStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    OPENED = "opened"
    READ = "read"
    CLICKED = "clicked"
    REPLIED = "replied"


class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    acquisition_source: Optional[str] = None
    favoured_social_channel: Optional[str] = None
    relationship_tier: RelationshipTier = Field(default=RelationshipTier.EARLY)
    preferred_channel: Optional[str] = None
    is_blocked_on_whatsapp: bool = Field(default=False)

    orders: List["Order"] = Relationship(back_populates="customer")
    communication_logs: List["CommunicationLog"] = Relationship(
        back_populates="customer"
    )


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    category: str = Field(index=True)
    price: float
    estimated_lifespan_days: Optional[int] = None

    orders: List["Order"] = Relationship(back_populates="product")


class Campaign(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    campaign_type: str
    target_tier: RelationshipTier
    channel: str
    discount_rate: float = Field(ge=0.0, le=1.0)

    orders: List["Order"] = Relationship(back_populates="campaign")
    communication_logs: List["CommunicationLog"] = Relationship(
        back_populates="campaign"
    )


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    quantity: int = Field(ge=1)
    total_amount: float = Field(ge=0.0)
    order_date: datetime = Field(default_factory=utc_now, index=True)
    attributed_campaign_id: Optional[int] = Field(
        default=None,
        foreign_key="campaign.id",
        index=True,
    )

    customer: Customer = Relationship(back_populates="orders")
    product: Product = Relationship(back_populates="orders")
    campaign: Optional[Campaign] = Relationship(back_populates="orders")


class CommunicationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id", index=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    channel_used: str
    status: CommunicationStatus = Field(default=CommunicationStatus.SENT)
    sent_at: datetime = Field(default_factory=utc_now, index=True)
    customer_reply: Optional[str] = None
    reply_sentiment: Optional[str] = None

    campaign: Campaign = Relationship(back_populates="communication_logs")
    customer: Customer = Relationship(back_populates="communication_logs")
