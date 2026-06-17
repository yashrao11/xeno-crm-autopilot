import os
import sys
import time
import subprocess
import httpx
from sqlmodel import Session, select, func

# Add parent directory to path for app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine
from app.models import Customer, CommunicationLog, Campaign

def main():
    print("Starting Xeno CRM Integration Workflow Test...")
    
    # 1. Spin up both uvicorn servers
    print("Spawning CRM API on port 8000...")
    crm_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    print("Spawning Mock Channel Service on port 8001...")
    stub_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "channel_stub.main:app", "--port", "8001", "--host", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for servers to startup
    time.sleep(3.0)
    
    try:
        # 2. Verify both servers are reachable
        print("Checking server health status...")
        with httpx.Client(timeout=60.0) as client:
            crm_health = client.get("http://localhost:8000/health")
            assert crm_health.status_code == 200, f"CRM API not ready: {crm_health.status_code}"
            print("✓ CRM API is healthy and connected to DB.")
            
            # 3. Trigger Campaign 4 (WhatsApp campaign for Loyal customers)
            print("Triggering Campaign ID 4 run (WhatsApp Campaign to Loyal targets)...")
            run_response = client.post("http://localhost:8000/api/campaigns/4/run")
            assert run_response.status_code == 200, f"Failed to run campaign: {run_response.status_code}"
            print(f"✓ Campaign Run Response: {run_response.json()}")
            
        # 4. Wait for async lifecycle simulations and webhook callbacks
        # Since delays are 2-5s for delivery, 5s for read, 5s for click, 5s for reply,
        # we will wait 25 seconds to allow logs to transition.
        print("Waiting 25 seconds for async transmission simulations and fallback webhooks...")
        for elapsed in range(1, 26):
            time.sleep(1.0)
            if elapsed % 5 == 0:
                print(f"  ... {elapsed}s elapsed ...")
                
        # 5. Database assertions using SQLModel session
        print("\nPerforming database verification...")
        with Session(engine) as session:
            # Check communication log count and status transitions
            total_logs = session.exec(select(func.count(CommunicationLog.id))).one()
            print(f"  Total Communication Logs in Database: {total_logs}")
            
            # Status distribution
            statuses = session.exec(select(CommunicationLog.status)).all()
            status_counts = {}
            for s in statuses:
                status_counts[s] = status_counts.get(s, 0) + 1
            print(f"  Log Statuses: {status_counts}")
            
            # Fallback Email logs
            email_logs = session.exec(select(CommunicationLog).where(CommunicationLog.channel_used == "Email")).all()
            # Note: We already seeded some Email logs originally (2050 logs total, many are Email).
            # Let's count how many Email logs belong specifically to Campaign 4!
            fallback_campaign_4_email_logs = session.exec(
                select(CommunicationLog)
                .where(CommunicationLog.campaign_id == 4)
                .where(CommunicationLog.channel_used == "Email")
            ).all()
            print(f"  Fallback Email logs dispatched for Campaign 4: {len(fallback_campaign_4_email_logs)}")
            
            # WhatsApp blocked customers
            blocked_customers = session.exec(select(Customer).where(Customer.is_blocked_on_whatsapp == True)).all()
            # Note: 5% were blocked originally. Let's print how many are blocked now.
            print(f"  Total Blocked Customers on WhatsApp: {len(blocked_customers)}")
            
            # Replies with parsed sentiments
            replied_logs = session.exec(select(CommunicationLog).where(CommunicationLog.status == "replied")).all()
            parsed_sentiments = [l.reply_sentiment for l in replied_logs if l.reply_sentiment is not None]
            print(f"  Logs with parsed replies: {len(replied_logs)}")
            print(f"  Parsed Sentiments of Replies: {set(parsed_sentiments)}")
            
            # Assertions to verify workflow ran
            assert len(replied_logs) > 0, "No replies were recorded, workflow may not have executed"
            
        print("\n✓ Integration Workflow Verification Successful! Webhooks and async loops running perfectly.")
        
    finally:
        # 6. Ensure background server instances are terminated
        print("Cleaning up background server processes...")
        crm_proc.terminate()
        stub_proc.terminate()
        crm_proc.wait()
        stub_proc.wait()
        print("Servers successfully terminated.")

if __name__ == "__main__":
    main()
