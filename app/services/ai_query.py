import os
from dotenv import load_dotenv
load_dotenv()
import json
import logging
import re
from typing import Dict, Any
from sqlmodel import Session, select
from app.models import Product, Campaign

logger = logging.getLogger("AIQueryService")

def heuristic_extraction(query: str, session: Session) -> Dict[str, Any]:
    """
    Fallback parser using regex-like keyword extraction to identify filters in the query string,
    supporting both legacy filters and new database filters.
    """
    query_lower = query.lower()
    filters = {}
    
    # 1. Dynamic Product Name Matching & Product ID Matching (Run first to prevent keyword collisions)
    try:
        products = session.exec(select(Product)).all()
        # Sort products by length descending so longer matching names get matched first
        products_sorted = sorted(products, key=lambda x: len(x.name), reverse=True)
        for p in products_sorted:
            p_name_lower = p.name.lower()
            if p_name_lower in query_lower:
                filters["product_name"] = p.name
                filters["product_id"] = p.id
                # Strip product name from query to avoid matching its keywords (e.g. "organic") later
                query_lower = query_lower.replace(p_name_lower, "")
                break
    except Exception as e:
        logger.error(f"Failed to query products for heuristic extraction: {e}")

    # 2. Dynamic Campaign Matching & Campaign ID Matching (Run first to prevent keyword collisions)
    try:
        campaigns = session.exec(select(Campaign)).all()
        campaigns_sorted = sorted(campaigns, key=lambda x: len(x.name), reverse=True)
        for c in campaigns_sorted:
            c_name_lower = c.name.lower()
            if c_name_lower in query_lower:
                filters["campaign_id"] = c.id
                query_lower = query_lower.replace(c_name_lower, "")
                break
        camp_match = re.search(r'\bcampaign\s*(\d+)\b', query_lower)
        if camp_match:
            filters["campaign_id"] = int(camp_match.group(1))
            query_lower = re.sub(r'\bcampaign\s*\d+\b', "", query_lower)
    except Exception as e:
        logger.error(f"Failed to query campaigns for heuristic extraction: {e}")
        
    # Helper function to match whole words/phrases
    def has_word(word_pattern: str) -> bool:
        return bool(re.search(r'\b(?:' + word_pattern + r')\b', query_lower))

    # 3. Relationship Tier
    if has_word("loyal"):
        filters["relationship_tier"] = "Loyal"
    elif has_word("early|new"):
        filters["relationship_tier"] = "Early"
        
    # 4. Region / Cities (Legacy compatibility)
    region_keywords = {
        "north|delhi|noida|gurgaon|ncr": "North",
        "south|bangalore|bengaluru|chennai|hyderabad": "South",
        "east|kolkata|calcutta": "East",
        "west|mumbai|pune|goa": "West",
        "central|indore|bhopal": "Central"
    }
    for pattern, value in region_keywords.items():
        if has_word(pattern):
            filters["region"] = value
            break
            
    # 5. Shopping Method (Legacy compatibility)
    if has_word("store"):
        filters["favoured_shopping_method"] = "Store"
    elif has_word("website|web"):
        filters["favoured_shopping_method"] = "Website"
    elif has_word("app"):
        filters["favoured_shopping_method"] = "App"
        
    # 6. Replenishment Status (Legacy compatibility)
    if has_word("overdue"):
        filters["replenishment_status"] = "Overdue"
    elif has_word("due soon|soon"):
        filters["replenishment_status"] = "Due Soon"
    elif has_word("healthy|safe"):
        filters["replenishment_status"] = "Healthy"
        
    # 7. Preferred Channel / Log Channel
    if has_word("whatsapp|wa"):
        filters["channel"] = "WhatsApp"
        filters["preferred_channel"] = "WhatsApp"
    elif has_word("email|mail"):
        filters["channel"] = "Email"
        filters["preferred_channel"] = "Email"
    elif has_word("sms|text"):
        filters["channel"] = "SMS"
        filters["preferred_channel"] = "SMS"
    elif has_word("instagram|ig"):
        filters["channel"] = "Instagram"
        filters["preferred_channel"] = "Instagram"
    elif has_word("facebook|fb"):
        filters["channel"] = "Facebook"
        filters["preferred_channel"] = "Facebook"
        
    # 8. Acquisition Source (Legacy compatibility)
    acq_keywords = {
        "facebook": "Facebook Ads",
        "google": "Google Search",
        "insta": "Instagram Ads",
        "tiktok": "TikTok",
        "youtube": "YouTube",
        "referral": "Referral",
        "organic": "Organic"
    }
    for key, value in acq_keywords.items():
        if has_word(key):
            filters["acquisition_source"] = value
            break

    # 9. Timeline Overdue Gaps (heuristics legacy compatibility)
    match = re.search(r'\b(\d+)\+?\s*day', query_lower)
    if match:
        filters["overdue_days"] = int(match.group(1))

    # 10. Discount Match
    if has_word("discount|off|percent|%|coupon"):
        filters["has_discount"] = True

    # 11. Status Match
    if has_word("replied|reply|replies"):
        filters["status"] = "replied"
    elif has_word("clicked|click"):
        filters["status"] = "clicked"
    elif has_word("read"):
        filters["status"] = "read"
    elif has_word("delivered"):
        filters["status"] = "delivered"

    logger.info(f"Heuristic query parsing output: {filters}")
    return filters

def translate_natural_language_to_filters(query: str, session: Session) -> Dict[str, Any]:
    """
    Translates a natural language search query into structural filters matching SegmentQuery.
    Attempts to call Groq if GROQ_API_KEY is defined; otherwise falls back to heuristics.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.info("GROQ_API_KEY not found. Using keyword extraction fallback.")
        return heuristic_extraction(query, session)
        
    logger.info("GROQ_API_KEY found. Querying Groq API using model...")
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        # Dynamically fetch products and campaigns to build prompt details
        products = session.exec(select(Product)).all()
        campaigns = session.exec(select(Campaign)).all()
        
        product_list_str = "\n".join([f"- ID {p.id}: {p.name} ({p.category})" for p in products])
        campaign_list_str = "\n".join([f"- ID {c.id}: {c.name} (Type: {c.campaign_type}, Channel: {c.channel}, Discount: {c.discount_rate})" for c in campaigns])
        
        system_prompt = f"""
You are an expert NLP data extraction system for Xeno SmartReplenish CRM.
Parse the user's natural language query and map it to structural filter parameters.
Return ONLY a valid, raw JSON object containing these keys:
- "product_id" (int or null) - Match the product ID based on the mentioned product names below:
{product_list_str}

- "relationship_tier" (string or null) - Either "Early" or "Loyal".
- "campaign_id" (int or null) - Match the campaign ID based on the campaign names/types/channels below:
{campaign_list_str}

- "channel" (string or null) - Must be one of: "Email", "WhatsApp", "SMS", "Instagram", "Facebook".
- "status" (string or null) - Must be one of: "replied", "clicked", "read", "delivered".
- "has_discount" (boolean or null) - true if the query implies a discount or coupon code is wanted, false or null otherwise.

Rules:
1. Return ONLY the JSON object. Do not wrap it in markdown codeblocks (e.g. ```json ... ```) or add any explanation.
2. If a parameter is not mentioned or implied by the query, set its value to null.
3. Be flexible: if a query mentions 'espresso' or 'latte', map it to 'Premium Espresso Roast' (ID 1).
"""
        
        logger.info("Invoking Groq API completions for query translation...")
        
        # Try llama-3.3-70b-versatile, fallback to llama-3.1-8b-instant
        model_name = "llama-3.3-70b-versatile"
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
        except Exception as groq_err:
            logger.warning(f"Failed to use model {model_name}: {groq_err}. Trying fallback llama-3.1-8b-instant.")
            model_name = "llama-3.1-8b-instant"
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
        content_str = response.choices[0].message.content.strip()
        parsed_filters = json.loads(content_str)
        logger.info(f"Groq parsing output: {parsed_filters}")
        
        # Filter out null values so we don't pass them to SegmentQuery
        clean_filters = {k: v for k, v in parsed_filters.items() if v is not None}
        
        # Merge with heuristic extraction for legacy filters compatibility (region, method, replenishment status, etc.)
        heuristics = heuristic_extraction(query, session)
        combined_filters = {**heuristics, **clean_filters}
        
        return combined_filters
        
    except Exception as e:
        logger.error(f"Groq query parsing failed: {e}. Falling back to keyword extraction.")
        return heuristic_extraction(query, session)
