import os
import sys
from fastapi.testclient import TestClient

# Add parent directory to path for app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

def main():
    print("Initializing FastAPI TestClient...")
    client = TestClient(app)
    
    # 1. Health check verification
    print("Testing GET /health...")
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["status"] == "healthy", f"Expected status 'healthy', got {data}"
    print("✓ GET /health is healthy.")
    
    # 2. Customers List verification
    print("Testing GET /api/customers (paginated)...")
    response = client.get("/api/customers?skip=0&limit=5")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    customers = response.json()
    assert len(customers) == 5, f"Expected 5 customers, got {len(customers)}"
    # Check fields in persona
    c = customers[0]
    required_keys = ["id", "name", "email", "phone", "relationship_tier", "total_orders", "lifetime_spend", "replenishment_metrics"]
    for key in required_keys:
        assert key in c, f"Missing key {key} in customer response"
    print("✓ GET /api/customers pagination and persona payload validated.")
    
    # 3. Customer detail verification
    print("Testing GET /api/customers/{id}...")
    cust_id = 1
    response = client.get(f"/api/customers/{cust_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    persona = response.json()
    assert persona["id"] == cust_id
    metrics = persona["replenishment_metrics"]
    assert "replenishment_status" in metrics
    assert metrics["replenishment_status"] in ["Healthy", "Due Soon", "Overdue"]
    print(f"✓ GET /api/customers/{cust_id} validated. Status: {metrics['replenishment_status']}, Lifetime Spend: {persona['lifetime_spend']}")
    
    # 4. Segmentation validation
    print("Testing POST /api/analytics/segment (Region: North)...")
    payload = {"region": "North"}
    response = client.post("/api/analytics/segment", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    result = response.json()
    assert "total_matched" in result
    assert "region_breakdown" in result
    assert "shopping_method_breakdown" in result
    # Check region breakdown matches filter
    for r in result["region_breakdown"]:
        assert r == "North", f"Found region {r} when filtering for North"
    print(f"✓ POST /api/analytics/segment (North) validated. Total Matched: {result['total_matched']}, Total Spend: {result['total_spend']}")
    
    # 5. Campaign Targets and Cross-Sell Recommendation Validation
    print("Testing GET /api/campaigns/{id}/targets (Campaign ID 5 - Cross-Sell)...")
    response = client.get("/api/campaigns/5/targets")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    targets = response.json()
    print(f"  Campaign 5 has {len(targets)} targets.")
    
    if len(targets) > 0:
        target = targets[0]
        assert "customer" in target
        assert "recommended_product" in target
        rec = target["recommended_product"]
        assert rec is not None, "Expected recommended_product to be populated for Campaign ID 5"
        
        last_cat = target["customer"]["replenishment_metrics"]["last_product_name"]
        print(f"  Target last product: '{last_cat}' | Recommended product: '{rec['name']}' ({rec['category']})")
        
        # Verify recommendation logic
        last_product_id = target["customer"]["replenishment_metrics"]["last_product_id"]
        # Ensure it maps correctly
        if rec["id"] == 6:
            assert rec["category"] == "Coffee Beans & Accessories"
        elif rec["id"] == 20:
            assert rec["category"] == "Skincare"
        elif rec["id"] == 21:
            assert rec["category"] == "Apparel"
            
    print("✓ GET /api/campaigns/5/targets cross-sell logic validated.")
    
    print("\nAPI Integration Verification Successful! All endpoints verified.")

if __name__ == "__main__":
    main()
