import random
from datetime import datetime, timedelta
from sqlmodel import Session, SQLModel, create_engine
from app.database import engine
from app.models import Customer, Product, Order

# Ensure tables are created
SQLModel.metadata.create_all(engine)

# Indian Names and Cities for realistic data
FIRST_NAMES = ["Aarav", "Aditya", "Amit", "Ananya", "Arjun", "Deepak", "Divya", "Ishaan", "Karan", "Meera", "Neha", "Pooja", "Priya", "Rahul", "Rohan", "Sanjay", "Shreya", "Siddharth", "Sneha", "Vikram"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Patel", "Mehta", "Singh", "Sen", "Joshi", "Rao", "Nair", "Iyer", "Reddy", "Choudhury", "Das", "Banerjee", "Mishra", "Pandey", "Saxena", "Kapoor", "Malhotra"]
REGIONS = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune", "Ahmedabad"]
SOURCES = ["Instagram Ads", "Facebook Ads", "Google Search", "Organic Referral"]
CHANNELS = ["WhatsApp", "Email", "SMS"]

def seed_database():
    with Session(engine) as session:
        # 1. Check and Seed Products
        existing_products = session.query(Product).all()
        if not existing_products:
            products = [
                Product(name="Arabica House Blend", category="Coffee", price=450.0, estimated_lifespan_days=15),
                Product(name="Organic Green Tea Pack", category="Tea", price=320.0, estimated_lifespan_days=25),
                Product(name="Leather Daily Tote Bag", category="Handbag", price=3500.0, estimated_lifespan_days=180),
                Product(name="Classic Slim-Fit Shirt", category="Shirts", price=1200.0, estimated_lifespan_days=90),
                Product(name="Cold Brew Concentrate", category="Coffee", price=600.0, estimated_lifespan_days=10)
            ]
            session.add_all(products)
            session.commit()
            print("Successfully seeded products.")
            products = session.query(Product).all()
        else:
            products = existing_products

        # 2. Check and Seed Customers (1,000 count)
        existing_customers = session.query(Customer).count()
        if existing_customers < 1000:
            print("Generating 1,000 customers...")
            customers = []
            for i in range(1000):
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                email = f"{name.lower().replace(' ', '')}{random.randint(10,99)}@mail.in"
                phone = f"+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}"
                
                # Assign region, source, and initial parameters
                region = random.choice(REGIONS)
                source = random.choice(SOURCES)
                favoured_social = "Instagram" if "Instagram" in source else "Facebook" if "Facebook" in source else "Google"
                
                cust = Customer(
                    name=name,
                    email=email,
                    phone=phone,
                    acquisition_source=source,
                    favoured_social_channel=favoured_social,
                    relationship_tier="Early",  # Will be dynamically updated by orders
                    preferred_channel=random.choice(CHANNELS),
                    is_blocked_on_whatsapp=False
                )
                customers.append(cust)
            
            # Batch save customers
            session.add_all(customers)
            session.commit()
            print("1,000 Customers created.")
            customers = session.query(Customer).all()
        else:
            customers = session.query(Customer).all()

        # 3. Check and Seed Orders (5,000+ count)
        existing_orders = session.query(Order).count()
        if existing_orders < 5000:
            print("Generating 5,000+ orders. This may take a few seconds...")
            orders = []
            now = datetime.utcnow()
            
            # Generate orders spanning the last 6 months
            for _ in range(5200):
                cust = random.choice(customers)
                prod = random.choice(products)
                qty = random.choice([1, 2, 3])
                
                # Order date distribution over the last 180 days
                days_ago = random.randint(0, 180)
                order_date = now - timedelta(days=days_ago)
                
                order = Order(
                    customer_id=cust.id,
                    product_id=prod.id,
                    quantity=qty,
                    total_amount=prod.price * qty,
                    order_date=order_date
                )
                orders.append(order)
            
            # Batch save orders
            session.add_all(orders)
            session.commit()
            print(f"Successfully seeded {len(orders)} orders.")
            
            # 4. Dynamically recalculate relationship tiers (Early vs. Loyal)
            print("Updating customer relationship tiers...")
            for cust in customers:
                order_count = session.query(Order).filter(Order.customer_id == cust.id).count()
                if order_count >= 3:
                    cust.relationship_tier = "Loyal"
                else:
                    cust.relationship_tier = "Early"
            session.commit()
            print("Customer relationship tiers updated.")
        else:
            print(f"Orders already seeded ({existing_orders} count).")

if __name__ == "__main__":
    seed_database()