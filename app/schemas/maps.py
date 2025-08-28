from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# request schemas for geocoding APIs
class ForwardGeocodeRequest(BaseModel):
    address: str = Field(..., description="Free text address or plus code")
    language: str = Field(default="ru", description="Language for results (ru, kk, en)")
    region: str = Field(default="KZ", description="Region bias")
    components: Optional[str] = Field(None, description="Pipe-separated filters like 'country:KZ|locality:Kostanay'")
    bounds: Optional[str] = Field(None, description="Viewport bias as 'sw_lat,sw_lng|ne_lat,ne_lng'")


class ReverseGeocodeRequest(BaseModel):
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")
    language: str = Field(default="ru", description="Language for results (ru, kk, en)")
    region: str = Field(default="KZ", description="Region bias")
    result_type: Optional[str] = Field(None, description="Filter by result types (e.g., 'street_address|premise|subpremise')")
    location_type: Optional[str] = Field(None, description="Filter by geometry type (e.g., 'ROOFTOP|RANGE_INTERPOLATED')")


# data structure schemas for order persistence (as per geo.md spec)
class AddressComponents(BaseModel):
    city: str = Field(default="", description="City name")
    street: str = Field(default="", description="Street name")
    house: str = Field(default="", description="House number")
    entrance: str = Field(default="", description="Entrance number")
    apartment: str = Field(default="", description="Apartment number")
    floor: str = Field(default="", description="Floor number")
    comment: str = Field(default="", description="Additional delivery instructions")


class GeocodedData(BaseModel):
    formatted_address: str = Field(..., description="Google's formatted address")
    lat: float = Field(..., description="Latitude from geocoding")
    lng: float = Field(..., description="Longitude from geocoding")
    method: str = Field(..., description="Method used: 'geocode' or 'reverse'")
    result_types: List[str] = Field(default_factory=list, description="Types of the geocoding result")


class Coordinates(BaseModel):
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")


class DeviceLocation(BaseModel):
    accuracy_m: Optional[float] = Field(None, description="GPS accuracy in meters")
    source: str = Field(default="html5", description="Source of location (html5, gps, etc.)")


class OrderAddressData(BaseModel):
    """complete address data structure for order persistence as per geo.md spec."""
    typed_address: str = Field(..., description="User's original typed address")
    components: AddressComponents = Field(default_factory=AddressComponents, description="Structured address components")
    geocoded: Optional[GeocodedData] = Field(None, description="Geocoding result data")
    final_pin: Optional[Coordinates] = Field(None, description="Final pin position after user adjustment")
    device_loc: Optional[DeviceLocation] = Field(None, description="Device location data")


# response schemas
class GeocodeResponse(BaseModel):
    status: str = Field(..., description="Response status")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Geocoding results")
    error_message: Optional[str] = Field(None, description="Error message if any")


class AddressValidationResponse(BaseModel):
    is_valid: bool = Field(..., description="Whether the address is valid for fallback")
    components: AddressComponents = Field(..., description="Extracted address components")
    geocoded: Optional[GeocodedData] = Field(None, description="Geocoding result if successful")


# legacy schema for backward compatibility
class AutocompleteRequest(BaseModel):
    input: str
    session_token: Optional[str] = None
    locationBias: Optional[Dict[str, Any]] = None
    regionCode: Optional[str] = None
    lang: Optional[str] = None


class GeocodeRequest(BaseModel):
    """Legacy geocode request schema for POST /geocode endpoint"""
    address: str = Field(..., description="Address to geocode")
    lang: Optional[str] = Field(None, description="Language for results (ru, kk, en)")
