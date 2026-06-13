import httpx
import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session, select, SQLModel
from app.database import engine
from app.models import Customer, Product, Order, Campaign, CommunicationLog
from app.ai_router import router as ai_router

app = FastAPI(title="Xeno AI-Native Mini CRM")
app.include_router(ai_router)

# Environment variables
CHANNEL_SERVICE_URL = os.getenv("CHANNEL_SERVICE_URL", "http://localhost:8001")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

class CampaignSendRequest(BaseModel):
    campaign_id: int

class WebhookReceiptRequest(BaseModel):
    communication_log_id: int
    status: str
    customer_reply: Optional[str] = None

# 1. Serving HTML SPA Directly at Root (GET /)
@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Xeno CRM Autopilot</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {
                darkMode: 'class',
            }
        </script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen">
        <div class="flex flex-col min-h-screen">
            <!-- Navbar -->
            <header class="border-b border-slate-800 bg-slate-900/50 backdrop-blur px-6 py-4 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <span class="text-blue-500 font-bold text-2xl tracking-tight">XENO</span>
                    <span class="text-slate-500 font-mono text-xs border border-slate-800 px-2 py-0.5 rounded">v1.0 Autopilot</span>
                </div>
            </header>

            <main class="flex-1 p-8 max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Metrics Left Column -->
                <div class="lg:col-span-2 space-y-8">
                    <!-- Dashboard Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="bg-slate-900 border border-slate-800 p-6 rounded-xl">
                            <p class="text-sm text-slate-400 font-medium">Unified System Revenue</p>
                            <h3 id="stat-revenue" class="text-3xl font-bold mt-2 text-emerald-400">Loading...</h3>
                        </div>
                        <div class="bg-slate-900 border border-slate-800 p-6 rounded-xl">
                            <p class="text-sm text-slate-400 font-medium">Active CRM Shoppers</p>
                            <h3 id="stat-shoppers" class="text-3xl font-bold mt-2 text-blue-400">Loading...</h3>
                        </div>
                        <div class="bg-slate-900 border border-slate-800 p-6 rounded-xl">
                            <p class="text-sm text-slate-400 font-medium">Predicted Churn Rate</p>
                            <h3 id="stat-churn" class="text-3xl font-bold mt-2 text-rose-400">Loading...</h3>
                        </div>
                    </div>

                    <!-- AI Search Interface -->
                    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
                        <h2 class="text-lg font-semibold text-slate-200 flex items-center gap-2">
                            <span>🔍</span> AI-Native Shopper Query
                        </h2>
                        <div class="flex gap-2">
                            <input id="ai-input" type="text" placeholder="e.g. Find Loyal customers with Instagram Ads" class="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500 text-slate-200">
                            <button onclick="runAiQuery()" class="bg-blue-600 hover:bg-blue-500 font-semibold px-6 py-3 rounded-lg transition">Ask Copilot</button>
                        </div>
                        
                        <!-- Customer List Results -->
                        <div class="border-t border-slate-800/80 pt-4 max-h-96 overflow-y-auto">
                            <table class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="text-slate-400 border-b border-slate-800">
                                        <th class="py-2">Name</th>
                                        <th class="py-2">Tier</th>
                                        <th class="py-2">Pref Channel</th>
                                        <th class="py-2 text-right">Total Spent</th>
                                    </tr>
                                </thead>
                                <tbody id="customer-list">
                                    <tr>
                                        <td colspan="4" class="py-4 text-center text-slate-500">Query above to segment database...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Executions Live Side Panel -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col h-full">
                    <h2 class="text-lg font-semibold text-slate-200 flex items-center gap-2 mb-4">
                        <span>⚡</span> Autopilot Execution Engine
                    </h2>
                    
                    <button onclick="triggerCampaign()" class="w-full bg-emerald-600 hover:bg-emerald-500 font-semibold py-3 px-4 rounded-lg transition mb-6">
                        Dispatch Autopilot Campaign
                    </button>

                    <p class="text-xs text-slate-400 font-mono mb-2">Live Callback Activity:</p>
                    <div id="live-console" class="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-xs text-slate-300 overflow-y-auto max-h-[30rem] space-y-2">
                        <p class="text-slate-600">// Waiting for deployment activity...</p>
                    </div>
                </div>
            </main>
        </div>

        <script>
            // 1. Fetch analytical counters on load
            async function loadStats() {
                try {
                    const response = await fetch('/api/analytics');
                    const data = await response.json();
                    document.getElementById('stat-revenue').innerText = "₹" + data.total_revenue.toLocaleString('en-IN');
                    document.getElementById('stat-shoppers').innerText = data.total_shoppers.toLocaleString();
                    document.getElementById('stat-churn').innerText = data.churn_risk_percentage.toFixed(1) + "%";
                } catch(e) { console.error(e); }
            }

            // 2. Query Database with natural language AI
            async function runAiQuery() {
                const prompt = document.getElementById('ai-input').value;
                if(!prompt) return;
                const tbody = document.getElementById('customer-list');
                tbody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-slate-500 animate-pulse">AI is parsing segments...</td></tr>`;

                try {
                    const response = await fetch('/api/ai/query', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt })
                    });
                    const data = await response.json();
                    
                    if(data.customers.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-slate-500">No matching cohorts found.</td></tr>`;
                        return;
                    }
                    
                    tbody.innerHTML = data.customers.map(c => `
                        <tr class="border-b border-slate-800/50 hover:bg-slate-800/20">
                            <td class="py-2 text-slate-200 font-medium">${c.name}</td>
                            <td class="py-2"><span class="px-2 py-0.5 rounded text-xs ${c.tier === 'Loyal' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}">${c.tier}</span></td>
                            <td class="py-2 text-slate-400">${c.preferred_channel}</td>
                            <td class="py-2 text-right text-slate-200 font-mono">₹${c.total_spent}</td>
                        </tr>
                    `).join('');
                } catch(e) { tbody.innerHTML = `<tr><td colspan="4" class="py-4 text-red-500 text-center">AI Server Communication Error</td></tr>`; }
            }

            // 3. Dispatch Mock Campaign
            async function triggerCampaign() {
                const consoleDiv = document.getElementById('live-console');
                consoleDiv.innerHTML = `<p class="text-blue-400">[Init] Initializing campaign ID #1...</p>`;
                
                try {
                    const response = await fetch('/api/campaigns/send', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ campaign_id: 1 })
                    });
                    const data = await response.json();
                    consoleDiv.innerHTML += `<p class="text-emerald-400">[Worker] Dispatched ${data.sends_triggered} jobs asynchronously to Port 8001.</p>`;
                } catch(e) { consoleDiv.innerHTML += `<p class="text-red-500">[Error] Failed to connect to server backend.</p>`; }
            }

            // 4. Poll background events every 2 seconds to make webhook events live
            setInterval(async () => {
                try {
                    const response = await fetch('/api/analytics');
                    const data = await response.json();
                    const consoleDiv = document.getElementById('live-console');
                    
                    if (data.recent_logs && data.recent_logs.length > 0) {
                        // Display the most recent webhook callback cycles
                        consoleDiv.innerHTML = data.recent_logs.map(log => {
                            let color = "text-slate-400";
                            if(log.status === 'read') color = "text-blue-400";
                            if(log.status === 'clicked') color = "text-yellow-400 font-bold";
                            if(log.status === 'replied') color = "text-purple-400 font-bold";
                            
                            let replyText = log.customer_reply ? ` -> Reply: "${log.customer_reply}" [${log.reply_sentiment}]` : '';
                            return `<p class="${color}">[Webhook] Customer #${log.customer_id} updated: ${log.status.toUpperCase()}${replyText}</p>`;
                        }).join('') + consoleDiv.innerHTML;
                    }
                } catch(e) {}
            }, 2000);

            window.onload = loadStats;
        </script>
    </body>
    </html>
    """

# 2. Existing Analytics / Campaign Endpoints
@app.get("/api/analytics")
def get_analytics():
    with Session(engine) as session:
        # Counters
        total_revenue = session.query(Order).sum(Order.total_amount) or 0.0
        total_shoppers = session.query(Customer).count()
        
        # Simulated Churn Indicator (Purchased over 45 days ago)
        threshold_date = datetime.utcnow() - timedelta(days=45)
        churn_count = session.query(Customer).join(Order).filter(Order.order_date < threshold_date).distinct().count()
        churn_risk = (churn_count / total_shoppers * 100) if total_shoppers > 0 else 0.0
        
        # Recent logs for polling dashboard console updates
        recent_logs = session.exec(select(CommunicationLog).order_by(CommunicationLog.id.desc()).limit(15)).all()
        formatted_logs = [
            {"customer_id": l.customer_id, "status": l.status, "customer_reply": l.customer_reply, "reply_sentiment": l.reply_sentiment}
            for l in recent_logs
        ]

        return {
            "total_revenue": round(total_revenue, 2),
            "total_shoppers": total_shoppers,
            "churn_risk_percentage": churn_risk,
            "recent_logs": formatted_logs
        }

@app.post("/api/campaigns/send")
def trigger_campaign(request: CampaignSendRequest, background_tasks: BackgroundTasks):
    with Session(engine) as session:
        customers = session.query(Customer).all() # Target all customers for mock scale
        
        # Setup batch triggers using background_tasks to prevent backend blocking
        background_tasks.add_task(dispatch_simulation, customers)
        return {"status": "dispatched", "sends_triggered": len(customers)}

async def dispatch_simulation(customers):
    async with httpx.AsyncClient() as client:
        for idx, cust in enumerate(customers[:25]): # Cap simulator loop at 25 concurrent streams to avoid port exhaustion
            try:
                # Log campaign send entry in database
                with Session(engine) as session:
                    log = CommunicationLog(campaign_id=1, customer_id=cust.id, channel_used=cust.preferred_channel, status="sent")
                    session.add(log)
                    session.commit()
                    log_id = log.id

                # POST async callback request to external channel stub
                await client.post(f"{CHANNEL_SERVICE_URL}/simulate", json={
                    "communication_log_id": log_id,
                    "webhook_url": f"{WEBHOOK_BASE_URL}/api/webhooks/receipt",
                    "channel": cust.preferred_channel
                })
            except Exception:
                continue

@app.post("/api/webhooks/receipt")
def receive_webhook(request: WebhookReceiptRequest):
    with Session(engine) as session:
        log = session.get(CommunicationLog, request.communication_log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Log entry not found")
        
        log.status = request.status
        if request.customer_reply:
            log.customer_reply = request.customer_reply
            # Lightweight fallback sentiment parser
            text = request.customer_reply.lower()
            if any(w in text for w in ["love", "thanks", "good", "great", "yes"]):
                log.reply_sentiment = "Positive"
            elif any(w in text for w in ["expensive", "bad", "high", "unsub", "stop"]):
                log.reply_sentiment = "Negative"
            else:
                log.reply_sentiment = "Neutral"
                
        session.commit()
        return {"status": "updated"}