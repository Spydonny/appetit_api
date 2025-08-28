import os
import time
from typing import Optional, Dict, Any, List
from functools import lru_cache

import httpx

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY_SERVER")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# cache for geocoding results
_geocode_cache: Dict[str, Dict[str, Any]] = {}
_reverse_cache: Dict[str, Dict[str, Any]] = {}


def _disabled() -> Dict[str, Any]:
    return {"status": "disabled", "reason": "no_api_key"}


def health_check() -> Dict[str, str]:
    """check Google Maps integration health and config status."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY_SERVER")
    
    if not api_key:
        return {"status": "misconfigured", "reason": "missing_api_key"}
    
    # basic validation - check if key looks valid (starts with AIza)
    if not api_key.startswith("AIza"):
        return {"status": "misconfigured", "reason": "invalid_api_key_format"}
    
    return {"status": "configured", "api_key_prefix": api_key[:10] + "..."}


def _get_cached_result(cache: Dict[str, Dict[str, Any]], key: str, max_age_seconds: int) -> Optional[Dict[str, Any]]:
    """get cached result if it's still valid."""
    if key in cache:
        cached_data = cache[key]
        if time.time() - cached_data.get("_cached_at", 0) < max_age_seconds:
            result = cached_data.copy()
            result.pop("_cached_at", None)  # Remove cache metadata
            return result
    return None


def _cache_result(cache: Dict[str, Dict[str, Any]], key: str, result: Dict[str, Any]) -> None:
    """cache result with timestamp."""
    result_with_timestamp = result.copy()
    result_with_timestamp["_cached_at"] = time.time()
    cache[key] = result_with_timestamp


def forward_geocode(
    address: str,
    language: str = "ru",
    region: str = "KZ",
    components: Optional[str] = None,
    bounds: Optional[str] = None
) -> Dict[str, Any]:
    """
    Forward geocoding: convert address text to coordinates.
    Always biases to Kazakhstan with proper language settings.
    
    Args:
        address: Free text address or plus code
        language: Language for results (ru, kk, en)
        region: Region bias (default: KZ)
        components: Pipe-separated filters like "country:KZ|locality:Kostanay"
        bounds: Viewport bias as "sw_lat,sw_lng|ne_lat,ne_lng"
    """
    if not API_KEY:
        return _disabled()
    
    # create cache key
    cache_key = f"forward:{address}:{language}:{region}:{components}:{bounds}"
    
    # check cache first (longer cache for forward geocoding - days)
    cached = _get_cached_result(_geocode_cache, cache_key, 86400 * 7)  # 7 days
    if cached:
        return cached
    
    # build params with Kazakhstan biasing
    params: Dict[str, Any] = {
        "address": address,
        "key": API_KEY,
        "language": language,
        "region": region
    }
    
    # always add country:KZ component if not already specified
    if components:
        if "country:KZ" not in components:
            params["components"] = f"country:KZ|{components}"
        else:
            params["components"] = components
    else:
        params["components"] = "country:KZ"
    
    if bounds:
        params["bounds"] = bounds
    
    try:
        r = httpx.get(GEOCODE_URL, params=params, timeout=10.0)
        result = r.json()
        
        # cache successful results
        if result.get("status") == "OK":
            _cache_result(_geocode_cache, cache_key, result)
        
        return result
    except Exception as e:
        return {"status": "ERROR", "error_message": f"Request failed: {str(e)}"}


def reverse_geocode(
    lat: float,
    lng: float,
    language: str = "ru",
    region: str = "KZ",
    result_type: Optional[str] = None,
    location_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reverse geocoding: convert coordinates to address text.
    Filters results for precision and biases to Kazakhstan.
    
    Args:
        lat: Latitude
        lng: Longitude
        language: Language for results (ru, kk, en)
        region: Region bias (default: KZ)
        result_type: Filter by result types (e.g., "street_address|premise|subpremise")
        location_type: Filter by geometry type (e.g., "ROOFTOP|RANGE_INTERPOLATED")
    """
    if not API_KEY:
        return _disabled()
    
    # create cache key
    cache_key = f"reverse:{lat}:{lng}:{language}:{region}:{result_type}:{location_type}"
    
    # check cache first (shorter cache for reverse geocoding - hours)
    cached = _get_cached_result(_reverse_cache, cache_key, 3600 * 6)  # 6 hours
    if cached:
        return cached
    
    # build params
    params: Dict[str, Any] = {
        "latlng": f"{lat},{lng}",
        "key": API_KEY,
        "language": language,
        "region": region
    }
    
    # add filtering params for precise results
    if result_type:
        params["result_type"] = result_type
    
    if location_type:
        params["location_type"] = location_type
    
    try:
        r = httpx.get(GEOCODE_URL, params=params, timeout=10.0)
        result = r.json()
        
        # cache successful results
        if result.get("status") == "OK":
            _cache_result(_reverse_cache, cache_key, result)
        
        return result
    except Exception as e:
        return {"status": "ERROR", "error_message": f"Request failed: {str(e)}"}


def extract_address_components(geocode_result: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract structured address components from geocoding result.
    Returns components suitable for the order data structure.
    """
    components = {
        "city": "",
        "street": "",
        "house": "",
        "entrance": "",
        "apartment": "",
        "floor": "",
        "comment": ""
    }
    
    if not geocode_result.get("results"):
        return components
    
    result = geocode_result["results"][0]
    address_components = result.get("address_components", [])
    
    for component in address_components:
        types = component.get("types", [])
        long_name = component.get("long_name", "")
        
        if "locality" in types or "administrative_area_level_2" in types:
            components["city"] = long_name
        elif "route" in types:
            components["street"] = long_name
        elif "street_number" in types:
            components["house"] = long_name
    
    return components


def is_valid_fallback_address(typed_address: str, components: Dict[str, str]) -> bool:
    """
    Check if address is valid for fallback when geocoding fails.
    Must have minimum required fields or sufficient text length.
    """
    # check if we have minimum structured components
    has_minimum_components = bool(
        components.get("city") and 
        components.get("street") and 
        components.get("house")
    )
    
    # check if typed address is sufficiently detailed
    has_sufficient_text = len(typed_address.strip()) >= 8
    
    return has_minimum_components or has_sufficient_text


# legacy function for backward compatibility - will be deprecated
def geocode(address: str, lang: Optional[str] = None) -> Dict[str, Any]:
    """legacy geocode function. Use forward_geocode instead."""
    return forward_geocode(address, language=lang or "ru")
