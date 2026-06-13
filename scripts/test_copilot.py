import os
import sys
from fastapi.testclient import TestClient

# Add parent directory to path for app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

def main():
    print("Initializing FastAPI TestClient...")
    client = TestClient(app)
    
    # 1. Test Dashboard Page Loading
    print("Testing GET / (Dashboard HTML)...")
    response = client.get("/")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    html_content = response.text
    assert "<title>Xeno SmartReplenish CRM</title>" in html_content, "Dashboard title not found in HTML"
    assert "AI Conversational Copilot" in html_content, "Dashboard search text not found in HTML"
    print("✓ Dashboard served at GET / successfully.")
    
    # 2. Test AI Natural Language Query Parser Heuristics (Generic Cohort Query)
    print("Testing POST /api/ai/query Heuristics...")
    query_str = "Find loyal app shoppers in Delhi overdue for coffee beans"
    payload = {"query": query_str}
    
    response = client.post("/api/ai/query", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    # Verify input echo
    assert data["query"] == query_str
    
    # Verify parsed filters
    filters = data["filters"]
    print(f"  Query: '{query_str}' -> Parsed Filters: {filters}")
    
    # Assert specific mapped keywords
    assert filters.get("relationship_tier") == "Loyal", f"Expected Loyal, got {filters.get('relationship_tier')}"
    assert filters.get("region") == "North", f"Expected North (Delhi mapping), got {filters.get('region')}"
    assert filters.get("favoured_shopping_method") == "App", f"Expected App, got {filters.get('favoured_shopping_method')}"
    assert filters.get("replenishment_status") == "Overdue", f"Expected Overdue, got {filters.get('replenishment_status')}"
    
    # Verify matching customers logic is applied
    result = data["result"]
    print(f"  Total matched customers: {result['total_matched']}")
    assert "total_matched" in result
    assert "region_breakdown" in result
    
    if len(result["customers"]) > 0:
        c = result["customers"][0]
        assert c["relationship_tier"] == "Loyal"
        assert c["region"] == "North"
        assert c["favoured_shopping_method"] == "App"
        assert c["replenishment_metrics"]["replenishment_status"] == "Overdue"
        print(f"  ✓ Verified Customer Persona matching filters: Name='{c['name']}', Tier='{c['relationship_tier']}', Region='{c['region']}', Method='{c['favoured_shopping_method']}', Replenishment='{c['replenishment_metrics']['replenishment_status']}'")
        
    print("✓ AI Conversational query translator heuristics and segmentation pipeline verified.")
    
    # 3. Test Custom Product + Overdue Days Threshold Query
    print("Testing POST /api/ai/query for Product Name and Overdue Days...")
    query_str2 = "Find 'Tea Tree Spot Treatment' customers overdue by 15+ days"
    payload2 = {"query": query_str2}
    
    response2 = client.post("/api/ai/query", json=payload2)
    assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
    data2 = response2.json()
    
    assert data2["query"] == query_str2
    filters2 = data2["filters"]
    print(f"  Query: '{query_str2}' -> Parsed Filters: {filters2}")
    
    assert filters2.get("product_name") == "Tea Tree Spot Treatment", f"Expected Tea Tree Spot Treatment, got {filters2.get('product_name')}"
    assert filters2.get("overdue_days") == 15, f"Expected 15, got {filters2.get('overdue_days')}"
    
    result2 = data2["result"]
    print(f"  Total matched customers for custom query: {result2['total_matched']}")
    
    # Validate each returned customer's filters and campaign history properties
    for c in result2["customers"]:
        assert c["replenishment_metrics"]["last_product_name"] == "Tea Tree Spot Treatment", f"Expected Tea Tree Spot Treatment, got {c['replenishment_metrics']['last_product_name']}"
        assert c["replenishment_metrics"]["days_until_empty"] <= -15, f"Expected days_until_empty <= -15, got {c['replenishment_metrics']['days_until_empty']}"
        
        # Verify campaign outcomes history is successfully returned as fields of CustomerPersona
        assert "last_campaign_name" in c
        assert "last_campaign_sent_at" in c
        assert "last_campaign_status" in c
        assert "last_campaign_reply" in c
        assert "last_campaign_reply_sentiment" in c
        
    if len(result2["customers"]) > 0:
        c = result2["customers"][0]
        print(f"  ✓ Verified Customer Persona matching custom filters: Name='{c['name']}', Product='{c['replenishment_metrics']['last_product_name']}', Days Until Empty={c['replenishment_metrics']['days_until_empty']}")
        print(f"    Campaign Info: Name='{c['last_campaign_name']}', Status='{c['last_campaign_status']}', Reply='{c['last_campaign_reply']}', Sentiment='{c['last_campaign_reply_sentiment']}'")
    
    print("✓ Custom Product and Overdue Days threshold querying verified successfully.")
    
    # 4. Test Webhooks recent list logs
    print("Testing GET /api/webhooks/recent...")
    response3 = client.get("/api/webhooks/recent?limit=5")
    assert response3.status_code == 200, f"Expected 200, got {response3.status_code}"
    logs = response3.json()
    print(f"  Recent logs count: {len(logs)}")
    if len(logs) > 0:
        log = logs[0]
        required_keys = ["id", "campaign_name", "customer_name", "channel_used", "status"]
        for key in required_keys:
            assert key in log, f"Missing key {key} in webhooks recent log response"
        print(f"  ✓ Sample Webhook Log: Msg #{log['id']} to {log['customer_name']} via {log['channel_used']} status={log['status']}")
        
    print("✓ GET /api/webhooks/recent verified.")
    
    print("\nAI Copilot and Frontend integration verification successful! All checks passed.")

if __name__ == "__main__":
    main()
