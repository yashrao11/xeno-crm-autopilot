from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlmodel import Session, select
from app.models import Order, Product

def calculate_replenishment_metrics(customer_id: int, session: Session, comparison_date: Optional[datetime] = None, latest_order: Optional[Order] = None) -> Dict[str, Any]:
    """
    Calculates replenishment metrics for a given customer based on their most recent order.
    
    If comparison_date is not provided, defaults to the current UTC datetime (timezone-naive to match db).
    """
    if comparison_date is None:
        comparison_date = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if latest_order is None:
        # Find the customer's most recent order
        statement = select(Order).where(Order.customer_id == customer_id).order_by(Order.order_date.desc()).limit(1)
        latest_order = session.exec(statement).first()
    
    if not latest_order:
        # Fallback values if customer has no orders
        return {
            "last_order_id": None,
            "last_order_date": None,
            "last_product_id": None,
            "last_product_name": None,
            "estimated_lifespan_days": None,
            "days_since_last_purchase": None,
            "predicted_empty_date": None,
            "days_until_empty": None,
            "replenishment_status": "Healthy"
        }
    
    order = latest_order
    
    # Retrieve the product from that order (cached in-memory as there are only 30 products)
    if not hasattr(calculate_replenishment_metrics, "_product_cache"):
        calculate_replenishment_metrics._product_cache = {}
        
    product = calculate_replenishment_metrics._product_cache.get(order.product_id)
    if not product:
        product_statement = select(Product).where(Product.id == order.product_id)
        product = session.exec(product_statement).one()
        calculate_replenishment_metrics._product_cache[order.product_id] = product
    
    # Perform calculations
    days_since_last_purchase = (comparison_date - order.order_date).days
    predicted_empty_date = order.order_date + timedelta(days=product.estimated_lifespan_days)
    days_until_empty = (predicted_empty_date - comparison_date).days
    
    # Determine status
    if days_until_empty > 5:
        status = "Healthy"
    elif 0 <= days_until_empty <= 5:
        status = "Due Soon"
    else:
        status = "Overdue"
        
    return {
        "last_order_id": order.id,
        "last_order_date": order.order_date,
        "last_product_id": product.id,
        "last_product_name": product.name,
        "estimated_lifespan_days": product.estimated_lifespan_days,
        "days_since_last_purchase": days_since_last_purchase,
        "predicted_empty_date": predicted_empty_date,
        "days_until_empty": days_until_empty,
        "replenishment_status": status
    }
