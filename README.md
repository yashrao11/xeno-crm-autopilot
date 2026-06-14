# Xeno SmartReplenish AI-Native CRM

An AI-native, predictive marketing and engagement CRM designed specifically for Direct-To-Consumer (DTC) and retail brands (e.g., coffee chains, fashion labels, beauty brands). It empowers marketers to ingest transaction history, dynamically segment shoppers (using an AI Conversational Copilot or structured segment filters), personalize multi-channel outreach, and track delivery performance through a fully decoupled, callback-driven messaging simulator.

---

## 🏗️ System Architecture

This project implements a **two-service, callback-driven loop** replicating real-world high-volume communication services (like Twilio, WhatsApp Cloud API, or SendGrid).

```mermaid
graph TD
    User["Retail Brand Manager"] -- Natural Language Query --> CRM["CRM Backend (Port 8000)"]
    CRM -- 1. Translate Query --> AI["AI Service (app/services/ai_query.py)"]
    AI -- Groq Llama 3.3 / Heuristics --> Filters["SegmentQuery + Custom Filters"]
    Filters -- 2. Query Cohort --> DB[("SQLite/PostgreSQL DB")]
    DB -- Match Cohort --> CRM
    CRM -- Python Custom Filters & Preloaded Joins --> CRM
    CRM -- Serve SPA Dashboard --> User
    
    User -- 3. Run Campaign --> CRM
    CRM -- 4. Batch Logs & Send Messages Concurrently --> Stub["Channel Stub Service (Port 8001)"]
    Stub -- 5. Async Transition States --> Webhooks["Webhook Endpoint (POST /api/webhooks/receipt)"]
    Webhooks -- 6. Update Log Status --> DB
    Webhooks -- "7. Fail/Negative WhatsApp Block" --> DB
    Webhooks -- "8. Trigger Email Fallback" --> Stub
```

### Decoupled Service Workflow
1. **Send API Dispatch**: When a campaign runs, the CRM creates local `CommunicationLog` entries in `sent` state and fires concurrent HTTP POST requests to `http://localhost:8001/channel/send`.
2. **Accept & Async Queue**: The Channel Stub accepts the payload, instantly returns `202 Accepted`, and spawns an asynchronous background task.
3. **Simulated Message Lifecycle**: The stub service introduces randomized network transmission delays and pushes state changes back to the CRM callback receiver (`POST http://localhost:8000/api/webhooks/receipt`) in sequential order:
   $$\text{Sent} \longrightarrow \text{Delivered} \longrightarrow \text{Read} \longrightarrow \text{Clicked} \longrightarrow \text{Replied / Failed}$$
4. **Ingestion & Status Mitigation**: The CRM ingests status callbacks, parses reply sentiment (Positive/Neutral/Negative), blocks users who opt-out/fail WhatsApp deliveries, and automatically fires an **Email Fallback** channel switch to recoup outreach.

---

## ✨ Key DTC & Retail Features

- **DTC-Tailored Schema & Seed Data**: Simulates a retail database containing detailed tables for `Customer`, `Product`, `Order`, `Campaign`, and `CommunicationLog`. Includes categories like *Coffee Beans & Accessories*, *Skincare*, and *Apparel*.
- **Predictive Replenishment Engine**: Calculates days elapsed since the customer's last purchase and uses product-specific lifespans to calculate `predicted_empty_date` and classify customers as `Healthy`, `Due Soon`, or `Overdue` for a restock.
- **Audience Segmentation**:
  - **AI Conversational Copilot**: Marketers write search queries in natural language (e.g., *"Find loyal app shoppers in Delhi overdue for coffee beans"*). Translated via **Groq Llama 3.3 API** (or regex keyword parser fallback) into structured segment metrics.
  - **Structured Segment Builder**: Standard filter panel targeting Category, Product, Region, Relationship Tier, Shopping Method, and Replenishment Status.
- **Marketing Performance Insights**:
  - **Live Dispatch Tracker Progress Bars**: Renders real-time visual progress indicators for each customer's message delivery status.
  - **State Counter Summary**: Counts active messages in **Sent**, **Delivered**, **Read**, **Clicked**, **Replied**, and **Failed** states in real time.
  - **Outcome Analytics**: Logs reply texts and automatically performs keyword sentiment analysis.

---

## 🛠️ Tech Stack & Dependencies

- **Backend Framework**: FastAPI (Uvicorn ASGI Server)
- **ORM / Database**: SQLModel / SQLAlchemy (SQLite local default / PostgreSQL supported)
- **AI Translation**: Groq API Python Client (Llama 3.3 / Llama 3.1)
- **UI Frontend**: HTML5, Vanilla JavaScript, CSS, and Tailwind CSS (Direct SPA Dashboard)
- **Testing Tools**: httpx, pytest, FastAPI TestClient

---

## 🚀 Installation & Local Setup

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Install Dependencies
```bash
# Clone the repository
git clone https://github.com/yashrao11/xeno-crm-autopilot.git
cd xeno-crm-autopilot

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file at the root of the project:
```env
# Optional: DATABASE_URL=postgresql://user:pass@localhost:5432/db_name
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Database Seeding & Startup
Run the seed script to compile schema migrations and populate SQLite with simulated shoppers and orders:
```bash
python scripts/seed_db.py
```

### 5. Running the Application
You can run both services locally:
```bash
# Terminal 1: Run the CRM Backend
source venv/bin/activate
uvicorn app.main:app --port 8000 --reload

# Terminal 2: Run the Mock Channel Service Stub
source venv/bin/activate
uvicorn channel_stub.main:app --port 8001 --reload
```

---

## 📡 Core API References

### 1. AI Conversational Query
* **Endpoint**: `POST /api/ai/query`
* **Request Payload**:
  ```json
  { "query": "Find 'Tea Tree Spot Treatment' customers overdue by 15+ days" }
  ```
* **Response**: Returns parsed query filters and the list of matching customer records.

### 2. Structured Segmentation
* **Endpoint**: `POST /api/analytics/segment`
* **Request Payload**:
  ```json
  {
    "category": "Skincare",
    "product_id": 18,
    "region": "South",
    "favoured_shopping_method": "Store",
    "relationship_tier": "Loyal",
    "replenishment_status": "Overdue"
  }
  ```

### 3. Dispatch Campaign
* **Endpoint**: `POST /api/campaigns/{id}/run`
* **Request Payload**:
  ```json
  {
    "customer_ids": [1, 2, 3],
    "message_template": "Hi {customer_name}, restock your {product_name}! Use code {campaign_name} for {discount_percent}% off.",
    "discount_rate": 0.15,
    "channel": "WhatsApp"
  }
  ```

### 4. Callback Webhook Receiver
* **Endpoint**: `POST /api/webhooks/receipt`
* **Request Payload**:
  ```json
  {
    "message_id": 9142,
    "status": "replied",
    "customer_reply": "Thanks for the discount!"
  }
  ```

---

## ⚙️ System Design Considerations

### Volume & Concurrency
* The CRM employs **bulk preloading** (`preload_customer_data`) to prevent `N+1` database query performance bottlenecks when retrieving segmentation.
* Communication dispatch tasks are processed concurrently using Python's `asyncio.gather` pipeline.

### Error & Out-Of-Order Callback Mitigation
* **WhatsApp Block Protection**: If a customer registers a `failed` delivery status or sends back a message with `Negative` sentiment (e.g. *"Stop"*), the CRM instantly marks `is_blocked_on_whatsapp = True` in the database and shifts their preferred channel to **Email**.
* **Automatic Fallback channel**: When a WhatsApp block triggers, the CRM launches a background fallback task (`trigger_email_fallback`) to redirect the promotional discount through the channel stub on **Email**.
* **Out-of-order callback protection**: Status updates in `pollCallbackTracker` ensure that terminal states like `replied` or `failed` are preserved and cannot be overwritten by late-arriving status callbacks.
