import os
import sys
from sqlmodel import Session, select, func

# Add the parent directory to the python path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine
from app.models import Product, Customer, Campaign, Order, CommunicationLog

def run_verification():
    print("Starting database verification script...\n")
    
    with Session(engine) as session:
        # 1. Row count validations
        num_products = session.exec(select(func.count(Product.id))).one()
        num_campaigns = session.exec(select(func.count(Campaign.id))).one()
        num_customers = session.exec(select(func.count(Customer.id))).one()
        num_orders = session.exec(select(func.count(Order.id))).one()
        num_logs = session.exec(select(func.count(CommunicationLog.id))).one()
        
        print(f"Record Counts:")
        print(f"  Products: {num_products}")
        print(f"  Campaigns: {num_campaigns}")
        print(f"  Customers: {num_customers}")
        print(f"  Orders: {num_orders}")
        print(f"  Communication Logs: {num_logs}")
        print()


        # Verify min constraints
        assert num_products == 30, f"Expected exactly 30 products, found {num_products}"
        assert num_campaigns >= 6, f"Expected >= 6 campaigns, found {num_campaigns}"
        assert num_customers >= 5000, f"Expected >= 5000 customers, found {num_customers}"
        assert num_orders >= 15000, f"Expected >= 15000 orders, found {num_orders}"
        assert num_logs >= 2000, f"Expected >= 2000 communication logs, found {num_logs}"
        
        print("✓ Record count validation passed.")
        
        # 2. Relationship Tier and 60/40 Ratio Verification
        early_custs = session.exec(select(Customer).where(Customer.relationship_tier == "Early")).all()
        loyal_custs = session.exec(select(Customer).where(Customer.relationship_tier == "Loyal")).all()
        
        total_custs = len(early_custs) + len(loyal_custs)
        early_pct = (len(early_custs) / total_custs) * 100
        loyal_pct = (len(loyal_custs) / total_custs) * 100
        
        print(f"Customer Tiers:")
        print(f"  Early-Stage: {len(early_custs)} ({early_pct:.2f}%)")
        print(f"  Loyal: {len(loyal_custs)} ({loyal_pct:.2f}%)")
        print()
        
        # We target a 60/40 ratio (approx 60% early and 40% loyal). Let's verify it falls within acceptable range.
        assert abs(early_pct - 60.0) < 1.0, f"Expected ~60% Early-stage, found {early_pct:.2f}%"
        assert abs(loyal_pct - 40.0) < 1.0, f"Expected ~40% Loyal, found {loyal_pct:.2f}%"
        
        print("✓ Customer tier distribution (60/40 ratio) validation passed.")
        
        # 3. Check Order count per tier consistency
        print("Validating order counts per relationship tier...")
        
        # Build map of customer_id -> order count
        order_counts = {}
        all_orders = session.exec(select(Order)).all()
        for order in all_orders:
            order_counts[order.customer_id] = order_counts.get(order.customer_id, 0) + 1
            
        for customer in early_custs:
            count = order_counts.get(customer.id, 0)
            assert 1 <= count <= 2, f"Early customer {customer.id} has invalid order count: {count}"
            
        for customer in loyal_custs:
            count = order_counts.get(customer.id, 0)
            assert count >= 3, f"Loyal customer {customer.id} has invalid order count: {count}"
            
        print("✓ Order count consistency per customer tier validated successfully.")
        
        # 4. Foreign Key Integrity Checks
        print("Validating foreign key relations...")
        
        customer_ids = set(session.exec(select(Customer.id)).all())
        product_ids = set(session.exec(select(Product.id)).all())
        campaign_ids = set(session.exec(select(Campaign.id)).all())
        
        # Check Orders integrity
        for order in all_orders:
            assert order.customer_id in customer_ids, f"Order {order.id} references non-existent Customer {order.customer_id}"
            assert order.product_id in product_ids, f"Order {order.id} references non-existent Product {order.product_id}"
            if order.attributed_campaign_id is not None:
                assert order.attributed_campaign_id in campaign_ids, f"Order {order.id} references non-existent Campaign {order.attributed_campaign_id}"
                
        # Check Communication Logs integrity
        all_logs = session.exec(select(CommunicationLog)).all()
        for log in all_logs:
            assert log.customer_id in customer_ids, f"Log {log.id} references non-existent Customer {log.customer_id}"
            assert log.campaign_id in campaign_ids, f"Log {log.id} references non-existent Campaign {log.campaign_id}"
            
        print("✓ All foreign key relations verified and intact.")
        print("\nVerification successful! All checks passed.")

if __name__ == "__main__":
    try:
        run_verification()
        sys.exit(0)
    except AssertionError as err:
        print(f"\n❌ Verification Failed: {err}")
        sys.exit(1)
