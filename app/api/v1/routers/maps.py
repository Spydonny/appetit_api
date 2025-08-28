from fastapi import APIRouter, HTTPException, Query
from app.schemas.maps import (
    ForwardGeocodeRequest, 
    ReverseGeocodeRequest, 
    OrderAddressData,
    GeocodeResponse,
    AddressValidationResponse,
    AutocompleteRequest,
    AddressComponents,
    GeocodedData,
    GeocodeRequest
)
from app.services.maps.google import (
    forward_geocode as svc_forward_geocode,
    reverse_geocode as svc_reverse_geocode,
    extract_address_components,
    is_valid_fallback_address,
    geocode as svc_geocode_legacy  # Legacy support
)

router = APIRouter(prefix="/maps", tags=["maps"])


@router.post("/forward-geocode")
def forward_geocode(req: ForwardGeocodeRequest) -> GeocodeResponse:
    """
    Forward geocoding: convert address text to coordinates.
    Biased to Kazakhstan with proper language settings.
    
    Used when user picks a suggestion or submits free text.
    If results are empty, UI should switch to Manual mode.
    """
    try:
        result = svc_forward_geocode(
            address=req.address,
            language=req.language,
            region=req.region,
            components=req.components,
            bounds=req.bounds
        )
        
        return GeocodeResponse(
            status=result.get("status", "ERROR"),
            results=result.get("results", []),
            error_message=result.get("error_message")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forward geocoding failed: {str(e)}")


@router.post("/reverse-geocode")
def reverse_geocode(req: ReverseGeocodeRequest) -> GeocodeResponse:
    """
    Reverse geocoding: convert coordinates to address text.
    Filters results for precision and biases to Kazakhstan.
    
    Used after 'Use my location' or when user drags the pin.
    If response is low quality or empty, keep user's typed address.
    """
    try:
        result = svc_reverse_geocode(
            lat=req.lat,
            lng=req.lng,
            language=req.language,
            region=req.region,
            result_type=req.result_type,
            location_type=req.location_type
        )
        
        return GeocodeResponse(
            status=result.get("status", "ERROR"),
            results=result.get("results", []),
            error_message=result.get("error_message")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reverse geocoding failed: {str(e)}")


@router.post("/validate-address")
def validate_address(address_data: OrderAddressData) -> AddressValidationResponse:
    """
    Validate address for order submission with fallback support.
    
    Checks if address is suitable for submission when geocoding fails.
    Must have minimum fields (city, street, house) or typed_address >= 8 chars.
    """
    try:
        # extract components from geocoded data if available
        components = address_data.components
        
        if address_data.geocoded:
            # if we have geocoded data, extract components from it
            geocode_result = {
                "status": "OK",
                "results": [{
                    "formatted_address": address_data.geocoded.formatted_address,
                    "geometry": {
                        "location": {
                            "lat": address_data.geocoded.lat,
                            "lng": address_data.geocoded.lng
                        }
                    },
                    "address_components": [],  # Would need full geocode result for this
                    "types": address_data.geocoded.result_types
                }]
            }
            extracted_components = extract_address_components(geocode_result)
            
            # merge extracted with provided components
            for key, value in extracted_components.items():
                if value and not getattr(components, key):
                    setattr(components, key, value)
        
        is_valid = is_valid_fallback_address(
            typed_address=address_data.typed_address,
            components=components.dict()
        )
        
        return AddressValidationResponse(
            is_valid=is_valid,
            components=components,
            geocoded=address_data.geocoded
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Address validation failed: {str(e)}")


@router.get("/quick-reverse")
def quick_reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    language: str = Query(default="ru", description="Language (ru, kk, en)"),
    precise: bool = Query(default=True, description="Use precise result filtering")
) -> GeocodeResponse:
    """
    Quick reverse geocoding endpoint for common use cases.
    Automatically applies best practices for precise results.
    """
    try:
        result_type = "street_address|premise|subpremise" if precise else None
        
        result = svc_reverse_geocode(
            lat=lat,
            lng=lng,
            language=language,
            region="KZ",
            result_type=result_type
        )
        
        return GeocodeResponse(
            status=result.get("status", "ERROR"),
            results=result.get("results", []),
            error_message=result.get("error_message")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick reverse geocoding failed: {str(e)}")


# legacy endpoints for backward compatibility
@router.post("/autocomplete")
def autocomplete_legacy(req: AutocompleteRequest):
    """legacy autocomplete endpoint. Consider using forward-geocode instead."""
    # this would need to be implemented if the old autocomplete functionality is still needed
    return {"status": "deprecated", "message": "Use /forward-geocode for new implementations"}


@router.get("/place")
def place_legacy(place_id: str = Query(...), fields: str | None = Query(None), lang: str | None = Query(None)):
    """legacy place details endpoint."""
    return {"status": "deprecated", "message": "Use /forward-geocode and /reverse-geocode for new implementations"}


@router.get("/geocode")
def geocode_legacy(address: str = Query(...), lang: str | None = Query(None)):
    """legacy geocode endpoint. Use /forward-geocode instead."""
    return svc_geocode_legacy(address=address, lang=lang)


@router.post("/geocode")
def geocode_legacy_post(req: GeocodeRequest):
    """legacy geocode endpoint supporting POST requests. Use /forward-geocode instead."""
    return svc_geocode_legacy(address=req.address, lang=req.lang)
