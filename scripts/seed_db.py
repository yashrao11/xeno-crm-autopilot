import os
import sys
import random
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, text

# Add the parent directory to the python path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db, engine
from app.models import Product, Customer, Campaign, Order, CommunicationLog

# Define current time for seed consistency
CURRENT_TIME = datetime(2026, 6, 13, 18, 0, 0)

# Rich pool of names to generate realistic combinations (mixed Indian and Western)
FIRST_NAMES = [
    "Aarav", "Vihaan", "Vivaan", "Ananya", "Diya", "Aditya", "Ishaan", "Krishna", "Pranav", "Kavya",
    "Riya", "Advait", "Dev", "Kiara", "Priya", "Rohan", "Rohit", "Sneha", "Vivek", "Arjun",
    "Sanjay", "Rajesh", "Amit", "Sunita", "Geeta", "Vikram", "Rahul", "Sameer", "Nisha", "Pooja",
    "Neha", "Karan", "Kabir", "Akash", "Rakesh", "Deepa", "Shreya", "Abhinav", "Tanvi", "Harish",
    "Manoj", "Divya", "Swati", "Preeti", "Ajay", "Vijay", "Suresh", "Ramesh", "James", "John",
    "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Mary", "Patricia",
    "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen", "Emily", "Daniel",
    "Matthew", "Chloe", "Emma", "Olivia", "Sophia", "Ava", "Mia", "Isabella", "George", "Paul",
    "Mark", "Steven", "Edward", "Brian", "Kevin", "Ronald", "Sandra", "Donna", "Carol", "Ruth",
    "Sharon", "Michelle", "Laura", "Kimberly", "Deborah", "Helen", "Ryan", "Justin", "Ashley", "Brandon"
]

LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Gupta", "Reddy", "Nair", "Kumar", "Singh", "Rao", "Joshi",
    "Mehta", "Shah", "Bhat", "Kulkarni", "Iyer", "Choudhury", "Pillai", "Saxena", "Das", "Banerjee",
    "Menon", "Patil", "Deshmukh", "Gowda", "Sen", "Mishra", "Prasad", "Bhatia", "Johar", "Malhotra",
    "Kapoor", "Khanna", "Nanda", "Gill", "Sodhi", "Grewal", "Dhillon", "Sandhu", "Cheema", "Smith",
    "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez",
    "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee",
    "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts", "Gomez",
    "Phillips", "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Stewart", "Morris"
]

DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me", "zoho.com"]
ACQUISITION_SOURCES = ["Facebook Ads", "Google Search", "Instagram Ads", "Referral", "Organic", "TikTok", "YouTube"]
CHANNELS = ["WhatsApp", "Email", "SMS", "Instagram", "Facebook"]
SOCIAL_CHANNELS = ["WhatsApp", "Instagram", "Email", "SMS"]
SHOPPING_METHODS = ["Store", "Website", "App"]
REGIONS = ["North", "South", "East", "West", "Central"]

STATUS_OPTIONS = ["sent", "delivered", "failed", "opened", "read", "clicked", "replied"]

REPLIES_POSITIVE = [
    "Love this product, just ordered more!",
    "Thanks for the discount, using it now!",
    "Great reminder, thank you!",
    "Excellent service, count me in."
]
REPLIES_NEUTRAL = [
    "Can you send the link again?",
    "Is this discount valid in stores?",
    "What other colors/types do you have?",
    "Will check it out later."
]
REPLIES_NEGATIVE = [
    "Stop texting me",
    "Too expensive",
    "I didn't like my last order",
    "Please unsubscribe me"
]

def batch_insert(session, model_class, records, batch_size=1000):
    """Inserts records in chunks to optimize memory and speed."""
    for i in range(0, len(records), batch_size):
        chunk = records[i:i+batch_size]
        session.add_all(chunk)
        session.commit()

def main():
    print("Initializing database...")
    init_db()

    with Session(engine) as session:
        print("Cleaning up old data...")
        session.exec(text("DELETE FROM communication_logs"))
        session.exec(text("DELETE FROM orders"))
        session.exec(text("DELETE FROM campaigns"))
        session.exec(text("DELETE FROM customers"))
        session.exec(text("DELETE FROM products"))
        session.commit()

        print("Seeding 30 Products (10 per category)...")
        products_data = [
            # Category 1: Coffee Beans & Accessories
            # Consumables
            Product(id=1, name="Premium Espresso Roast", category="Coffee Beans & Accessories", price=18.99, estimated_lifespan_days=25),
            Product(id=2, name="Organic Light Roast", category="Coffee Beans & Accessories", price=16.50, estimated_lifespan_days=30),
            Product(id=3, name="Cold Brew Coarse Ground", category="Coffee Beans & Accessories", price=14.99, estimated_lifespan_days=28),
            Product(id=4, name="Decaf French Roast", category="Coffee Beans & Accessories", price=17.99, estimated_lifespan_days=25),
            Product(id=5, name="Hazelnut Flavored Whole Bean", category="Coffee Beans & Accessories", price=15.99, estimated_lifespan_days=30),
            Product(id=9, name="Gourmet Vanilla Syrup (750ml)", category="Coffee Beans & Accessories", price=12.99, estimated_lifespan_days=60),
            # Accessories (long lifespans)
            Product(id=6, name="Classic French Press (8-Cup)", category="Coffee Beans & Accessories", price=34.99, estimated_lifespan_days=1095),
            Product(id=7, name="Premium Paper Coffee Filters (100-pack)", category="Coffee Beans & Accessories", price=6.50, estimated_lifespan_days=90),
            Product(id=8, name="Stainless Steel Milk Frothing Pitcher", category="Coffee Beans & Accessories", price=14.99, estimated_lifespan_days=1825),
            Product(id=10, name="Ceramic Double-Walled Mug", category="Coffee Beans & Accessories", price=18.00, estimated_lifespan_days=730),

            # Category 2: Skincare
            # Consumables (20-90 days)
            Product(id=11, name="Sandalwood Clay Cleanser", category="Skincare", price=24.50, estimated_lifespan_days=45),
            Product(id=12, name="Vitamin C Glow Serum", category="Skincare", price=32.00, estimated_lifespan_days=60),
            Product(id=13, name="Saffron Night Cream", category="Skincare", price=45.00, estimated_lifespan_days=90),
            Product(id=14, name="Hydrating Gel Sunscreen SPF 50", category="Skincare", price=29.99, estimated_lifespan_days=75),
            Product(id=15, name="Gentle Rosewater Toner", category="Skincare", price=18.50, estimated_lifespan_days=60),
            Product(id=16, name="Nourishing Shea Lip Balm", category="Skincare", price=8.00, estimated_lifespan_days=45),
            Product(id=17, name="Deep Cleansing Facial Oil", category="Skincare", price=26.00, estimated_lifespan_days=90),
            Product(id=20, name="Retinol Anti-Aging Eye Cream", category="Skincare", price=38.00, estimated_lifespan_days=60),
            # Less frequent skincare/treatments
            Product(id=18, name="Tea Tree Spot Treatment", category="Skincare", price=15.50, estimated_lifespan_days=120),
            Product(id=19, name="Aloe Vera Soothing Gel", category="Skincare", price=12.00, estimated_lifespan_days=90),

            # Category 3: Apparel
            # Durable/Semi-Durable Accessories/Clothing
            Product(id=21, name="Classic Denim Jacket", category="Apparel", price=89.00, estimated_lifespan_days=730),
            Product(id=22, name="Organic Cotton Tee", category="Apparel", price=22.00, estimated_lifespan_days=180),
            Product(id=23, name="Merino Wool Socks", category="Apparel", price=15.00, estimated_lifespan_days=120),
            Product(id=24, name="Fleece Pullover Hoodie", category="Apparel", price=49.99, estimated_lifespan_days=365),
            Product(id=25, name="Genuine Leather Belt", category="Apparel", price=35.00, estimated_lifespan_days=1095),
            Product(id=26, name="Ribbed Knit Beanie", category="Apparel", price=18.50, estimated_lifespan_days=365),
            Product(id=27, name="Slim-Fit Stretch Chinos", category="Apparel", price=59.99, estimated_lifespan_days=365),
            Product(id=28, name="Lightweight Running Shorts", category="Apparel", price=28.00, estimated_lifespan_days=180),
            Product(id=29, name="Waterproof Windbreaker", category="Apparel", price=75.00, estimated_lifespan_days=540),
            Product(id=30, name="Canvas Tote Bag", category="Apparel", price=12.00, estimated_lifespan_days=365),
        ]
        session.add_all(products_data)
        session.commit()
        print("Products seeded successfully.")

        print("Seeding 6 Lifecycle Campaigns...")
        campaigns_data = [
            Campaign(id=1, name="Early Soft Replenishment Ad", campaign_type="Replenishment", target_tier="Early", channel="Instagram", discount_rate=0.0),
            Campaign(id=2, name="Early Churn Feedback Survey", campaign_type="Feedback", target_tier="Early", channel="Email", discount_rate=0.0),
            Campaign(id=3, name="Early Churn Recovery Offer", campaign_type="Replenishment", target_tier="Early", channel="SMS", discount_rate=0.20),
            Campaign(id=4, name="Loyal Bulk Replenishment Offer", campaign_type="Replenishment", target_tier="Loyal", channel="WhatsApp", discount_rate=0.15),
            Campaign(id=5, name="Loyal AI Product Cross-Sell", campaign_type="Cross_Sell", target_tier="Loyal", channel="Instagram", discount_rate=0.10),
            Campaign(id=6, name="Loyal 1-Year Anniversary Milestone", campaign_type="Loyalty", target_tier="Loyal", channel="Email", discount_rate=0.25),
        ]
        session.add_all(campaigns_data)
        session.commit()
        print("Campaigns seeded successfully.")

        # Generate 5,100 unique customer email & name combinations
        print("Generating 5,100 unique customer details...")
        unique_customers = set()
        while len(unique_customers) < 5100:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email_first = first.lower()
            email_last = last.lower()
            num = random.randint(10, 99999)
            domain = random.choice(DOMAINS)
            email = f"{email_first}.{email_last}{num}@{domain}"
            unique_customers.add((email, first, last))
        
        unique_customers_list = list(unique_customers)

        # Generate unique phone numbers
        print("Generating unique phone numbers...")
        unique_phones = set()
        while len(unique_phones) < 5100:
            phone = f"+91-{random.randint(6000000000, 9999999999)}"
            unique_phones.add(phone)
        unique_phones_list = list(unique_phones)

        # Prepare customers list and decide order counts
        customers = []
        order_counts = []  # list of (customer_id, count)
        
        num_early = 3060
        num_loyal = 2040
        
        print("Preparing customers and determining target order distribution...")
        for i in range(5100):
            cust_id = i + 1
            email, first, last = unique_customers_list[i]
            phone = unique_phones_list[i]
            
            # Determine tier and order count
            if i < num_early:
                tier = "Early"
                target_orders = random.choice([1, 2])
            else:
                tier = "Loyal"
                target_orders = random.randint(3, 8)
                
            order_counts.append((cust_id, target_orders))
            
            # Generate customer registration date (up to 1.5 years ago = 540 days)
            reg_days_ago = random.randint(0, 540)
            created_at = CURRENT_TIME - timedelta(days=reg_days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
            customer = Customer(
                id=cust_id,
                name=f"{first} {last}",
                email=email,
                phone=phone,
                created_at=created_at,
                acquisition_source=random.choice(ACQUISITION_SOURCES),
                favoured_social_channel=random.choice(SOCIAL_CHANNELS),
                relationship_tier=tier,
                preferred_channel=random.choice(SOCIAL_CHANNELS),
                is_blocked_on_whatsapp=(random.random() < 0.05), # 5% WhatsApp block rate
                favoured_shopping_method=random.choice(SHOPPING_METHODS),
                region=random.choice(REGIONS)
            )
            customers.append(customer)

        print(f"Batch inserting {len(customers)} customers...")
        batch_insert(session, Customer, customers)
        print("Customers seeded successfully.")

        # Generate orders
        print("Generating relational orders based on customer tiers...")
        orders = []
        order_id_counter = 1
        
        for cust_id, count in order_counts:
            customer_obj = customers[cust_id - 1]
            reg_date = customer_obj.created_at
            
            prev_order_date = reg_date + timedelta(days=random.randint(0, 3))
            prev_product = None
            
            for o_idx in range(count):
                # Product replenishment simulation
                if o_idx > 0 and random.random() < 0.70 and prev_product is not None:
                    # 70% chance of repeat purchase of the same product
                    product = prev_product
                else:
                    product = random.choice(products_data)
                
                # Space out subsequent orders based on previous product estimated lifespan
                if o_idx == 0:
                    order_date = prev_order_date
                else:
                    days_diff = product.estimated_lifespan_days + random.randint(-10, 15)
                    days_diff = max(1, days_diff)
                    order_date = prev_order_date + timedelta(days=days_diff)
                
                # Cap order date at current time (cannot buy in the future)
                if order_date >= CURRENT_TIME:
                    time_remaining = CURRENT_TIME - prev_order_date
                    if time_remaining.total_seconds() > 60:
                        rand_secs = random.randint(1, int(time_remaining.total_seconds() - 10))
                        order_date = prev_order_date + timedelta(seconds=rand_secs)
                    else:
                        order_date = CURRENT_TIME - timedelta(seconds=10)
                
                prev_order_date = order_date
                prev_product = product
                
                quantity = random.randint(1, 3)
                total_amount = round(quantity * product.price, 2)
                
                # Attributed campaign with 15% probability
                attributed_campaign_id = None
                if random.random() < 0.15:
                    # Choose an attributed campaign based on customer tier
                    tier = customer_obj.relationship_tier
                    valid_campaigns = [c for c in campaigns_data if c.target_tier == tier]
                    if valid_campaigns:
                        attributed_campaign_id = random.choice(valid_campaigns).id
                
                order = Order(
                    id=order_id_counter,
                    customer_id=cust_id,
                    order_date=order_date,
                    product_id=product.id,
                    quantity=quantity,
                    total_amount=total_amount,
                    attributed_campaign_id=attributed_campaign_id
                )
                orders.append(order)
                order_id_counter += 1

        print(f"Batch inserting {len(orders)} orders...")
        batch_insert(session, Order, orders)
        print("Orders seeded successfully.")

        # Generate communication logs
        print("Generating at least 2,000 communication log entries with Instagram & Facebook callbacks...")
        communication_logs = []
        log_id_counter = 1
        
        for l_idx in range(2050):
            # Select random campaign and customer
            campaign = random.choice(campaigns_data)
            customer = random.choice(customers)
            
            # Instagram campaigns can also be served on Facebook
            if campaign.channel == "Instagram":
                channel_used = random.choice(["Instagram", "Facebook"])
            else:
                channel_used = campaign.channel
            
            # Sent date between customer creation and CURRENT_TIME
            reg_date = customer.created_at
            time_span_secs = int((CURRENT_TIME - reg_date).total_seconds())
            if time_span_secs > 120:
                sent_at = reg_date + timedelta(seconds=random.randint(60, time_span_secs - 10))
            else:
                sent_at = CURRENT_TIME - timedelta(seconds=5)
            
            # Generate status
            if channel_used in ["Instagram", "Facebook"]:
                # High proportion of clicked/read callbacks on social channels
                status = random.choice(["sent", "delivered", "read", "clicked"])
            else:
                status = random.choice(STATUS_OPTIONS)
                
            customer_reply = None
            reply_sentiment = None
            
            if status == "replied":
                sentiment = random.choice(["positive", "neutral", "negative"])
                reply_sentiment = sentiment
                if sentiment == "positive":
                    customer_reply = random.choice(REPLIES_POSITIVE)
                elif sentiment == "neutral":
                    customer_reply = random.choice(REPLIES_NEUTRAL)
                else:
                    customer_reply = random.choice(REPLIES_NEGATIVE)
            
            log = CommunicationLog(
                id=log_id_counter,
                campaign_id=campaign.id,
                customer_id=customer.id,
                channel_used=channel_used,
                sent_at=sent_at,
                status=status,
                customer_reply=customer_reply,
                reply_sentiment=reply_sentiment
            )
            communication_logs.append(log)
            log_id_counter += 1

        print(f"Batch inserting {len(communication_logs)} communication logs...")
        batch_insert(session, CommunicationLog, communication_logs)
        print("Communication logs seeded successfully.")

        # Sync PostgreSQL sequence counters if using PostgreSQL
        if engine.dialect.name == "postgresql":
            print("Syncing PostgreSQL sequence counters...")
            tables = ["products", "customers", "campaigns", "orders", "communication_logs"]
            for table in tables:
                session.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}"))
            session.commit()
            print("PostgreSQL sequence counters synced.")

        print(f"\nDatabase seeding complete! Summary of seeded records:")
        print(f"- Products: {len(products_data)}")
        print(f"- Campaigns: {len(campaigns_data)}")
        print(f"- Customers: {len(customers)}")
        print(f"- Orders: {len(orders)}")
        print(f"- Communication Logs: {len(communication_logs)}")

if __name__ == "__main__":
    main()
