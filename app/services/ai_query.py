import os
import json
import logging
import re
from typing import Dict, Any
from sqlmodel import Session, select
from app.models import Product

logger = logging.getLogger("AIQueryService")

def heuristic_extraction(query: str, session: Session) -> Dict[str, Any]:
    """
    Fallback parser using regex-like keyword extraction to identify filters in the query string,
    including dynamic product matches and overdue day thresholds.
    """
    query_lower = query.lower()
    filters = {}
    
    # 1. Relationship Tier
    if "loyal" in query_lower:
        filters["relationship_tier"] = "Loyal"
    elif "early" in query_lower or "new" in query_lower:
        filters["relationship_tier"] = "Early"
        
    # 2. Region / Cities
    region_keywords = {
        "north": "North", "delhi": "North", "noida": "North", "gurgaon": "North", "ncr": "North",
        "south": "South", "bangalore": "South", "bengaluru": "South", "chennai": "South", "hyderabad": "South",
        "east": "East", "kolkata": "East", "calcutta": "East",
        "west": "West", "mumbai": "West", "pune": "West", "goa": "West",
        "central": "Central", "indore": "Central", "bhopal": "Central"
    }
    for key, value in region_keywords.items():
        if key in query_lower:
            filters["region"] = value
            break
            
    # 3. Shopping Method
    if "store" in query_lower:
        filters["favoured_shopping_method"] = "Store"
    elif "website" in query_lower or "web" in query_lower:
        filters["favoured_shopping_method"] = "Website"
    elif "app" in query_lower:
        filters["favoured_shopping_method"] = "App"
        
    # 4. Replenishment Status
    if "overdue" in query_lower:
        filters["replenishment_status"] = "Overdue"
    elif "due soon" in query_lower or "soon" in query_lower:
        filters["replenishment_status"] = "Due Soon"
    elif "healthy" in query_lower or "safe" in query_lower:
        filters["replenishment_status"] = "Healthy"
        
    # 5. Preferred Channel
    if "whatsapp" in query_lower or "wa" in query_lower:
        filters["preferred_channel"] = "WhatsApp"
    elif "email" in query_lower or "mail" in query_lower:
        filters["preferred_channel"] = "Email"
    elif "sms" in query_lower or "text" in query_lower:
        filters["preferred_channel"] = "SMS"
    elif "instagram" in query_lower or "ig" in query_lower:
        filters["preferred_channel"] = "Instagram"
        
    # 6. Acquisition Source
    acq_keywords = {
        "facebook": "Facebook Ads", "google": "Google Search", "insta": "Instagram Ads",
        "tiktok": "TikTok", "youtube": "YouTube", "referral": "Referral", "organic": "Organic"
    }
    for key, value in acq_keywords.items():
        if key in query_lower:
            filters["acquisition_source"] = value
            break

    # 7. Dynamic Product Name Matching (from database products list)
    try:
        products = session.exec(select(Product)).all()
        for p in products:
            if p.name.lower() in query_lower:
                filters["product_name"] = p.name
                break
    except Exception as e:
        logger.error(f"Failed to query products for heuristic extraction: {e}")

    # 8. Timeline Overdue Gaps (e.g. '15 days passed', 'overdue by 15+ days')
    match = re.search(r'(\d+)\+?\s*day', query_lower)
    if match:
        filters["overdue_days"] = int(match.group(1))

    logger.info(f"Heuristic query parsing output: {filters}")
    return filters

def translate_natural_language_to_filters(query: str, session: Session) -> Dict[str, Any]:
    """
    Translates a natural language search query into structural filters matching SegmentQuery.
    Attempts to call OpenAI if OPENAI_API_KEY is defined; otherwise falls back to heuristics.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.info("OPENAI_API_KEY not found. Using keyword extraction fallback.")
        return heuristic_extraction(query, session)
        
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Extract the filtering criteria from the user's natural language search query.
        Return a JSON object containing ONLY the matching filters from this list:
        - region (string: North, South, East, West, Central)
        - acquisition_source (string: Facebook Ads, Google Search, Instagram Ads, Referral, Organic, TikTok, YouTube)
        - relationship_tier (string: Early, Loyal)
        - favoured_shopping_method (string: Store, Website, App)
        - replenishment_status (string: Healthy, Due Soon, Overdue)
        - preferred_channel (string: WhatsApp, Email, SMS, Instagram)
        - product_name (string: exact name of product if mentioned)
        - overdue_days (integer: number of days overdue if mentioned, e.g. "15+ days" -> 15)

        Do not include any key if it is not explicitly referenced in the search query.

        Query: "{query}"
        """
        
        logger.info("Invoking OpenAI completions API for query translation...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        parsed_filters = json.loads(response.choices[0].message.content)
        logger.info(f"OpenAI parsing output: {parsed_filters}")
        return parsed_filters
        
    except Exception as e:
        logger.error(f"OpenAI query parsing failed: {e}. Falling back to keyword extraction.")
        return heuristic_extraction(query, session)
