"""
Google Analytics 4 Data Fetching Service

This service uses the Google Analytics Data API v1 to fetch analytics data from GA4.
It complements the existing GA4 Measurement Protocol services by providing data retrieval capabilities.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Graceful handling of Google Analytics Data API imports
try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest,
        Dimension,
        Metric,
        DateRange,
        OrderBy,
        FilterExpression,
        Filter,
        FilterStringFilter,
    )
    from google.oauth2.service_account import Credentials
    GA4_DATA_API_AVAILABLE = True
except ImportError:
    # Mock classes when library is not available
    BetaAnalyticsDataClient = None
    RunReportRequest = None
    Dimension = None
    Metric = None
    DateRange = None
    OrderBy = None
    FilterExpression = None
    Filter = None
    FilterStringFilter = None
    Credentials = None
    GA4_DATA_API_AVAILABLE = False


class GA4DataClient:
    """Client for fetching data from Google Analytics 4."""
    
    def __init__(self):
        self._client = None
        self._property_id = None
        self._credentials_path = None
        
    @property
    def property_id(self):
        """Get GA4 property ID from environment variables or override."""
        if self._property_id is not None:
            return self._property_id
        return os.getenv("GA4_PROPERTY_ID")
    
    @property_id.setter
    def property_id(self, value):
        """Set GA4 property ID override."""
        self._property_id = value
    
    @property_id.deleter
    def property_id(self):
        """Delete GA4 property ID override."""
        self._property_id = None
    
    @property 
    def credentials_path(self):
        """Get credentials path from environment variables or override."""
        if self._credentials_path is not None:
            return self._credentials_path
        return os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
    @credentials_path.setter
    def credentials_path(self, value):
        """Set credentials path override."""
        self._credentials_path = value
        
    @credentials_path.deleter
    def credentials_path(self):
        """Delete credentials path override."""
        self._credentials_path = None
        
    def _get_client(self):
        """Initialize and return GA4 Data API client."""
        if not GA4_DATA_API_AVAILABLE:
            return None
            
        if self._client is None:
            if not self.property_id or not self.credentials_path:
                return None
            
            try:
                if self.credentials_path and os.path.exists(self.credentials_path):
                    credentials = Credentials.from_service_account_file(self.credentials_path)
                    self._client = BetaAnalyticsDataClient(credentials=credentials)
                else:
                    # Fallback to default credentials
                    self._client = BetaAnalyticsDataClient()
            except Exception:
                return None
                
        return self._client
    
    def health_check(self) -> Dict[str, Any]:
        """Check GA4 Data API configuration and connectivity."""
        if not GA4_DATA_API_AVAILABLE:
            return {
                "status": "library_not_available",
                "reason": "google_analytics_data_library_not_installed",
                "message": "Install google-analytics-data package to enable GA4 data fetching",
                "property_id_configured": bool(self.property_id),
                "credentials_configured": bool(self.credentials_path),
            }
            
        if not self.property_id:
            return {
                "status": "misconfigured",
                "reason": "missing_property_id",
                "property_id_configured": False,
                "credentials_configured": bool(self.credentials_path),
            }
        
        if not self.credentials_path:
            return {
                "status": "misconfigured", 
                "reason": "missing_credentials",
                "property_id_configured": True,
                "credentials_configured": False,
            }
        
        client = self._get_client()
        if not client:
            return {
                "status": "misconfigured",
                "reason": "client_initialization_failed",
                "property_id_configured": True,
                "credentials_configured": True,
            }
        
        # Test connectivity with a minimal request
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[Dimension(name="date")],
                metrics=[Metric(name="sessions")],
                date_ranges=[DateRange(start_date="7daysAgo", end_date="yesterday")],
                limit=1,
            )
            response = client.run_report(request=request)
            return {
                "status": "configured",
                "property_id": self.property_id,
                "test_rows_returned": len(response.rows),
            }
        except Exception as e:
            return {
                "status": "error",
                "reason": "api_request_failed",
                "error": str(e),
                "property_id_configured": True,
                "credentials_configured": True,
            }
    
    def get_sessions_and_users(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "yesterday",
    ) -> Dict[str, Any]:
        """Get sessions and users metrics from GA4."""
        client = self._get_client()
        if not client or not self.property_id:
            return {"status": "skipped", "reason": "not_configured"}
        
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[Dimension(name="date")],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="totalUsers"),
                    Metric(name="newUsers"),
                    Metric(name="screenPageViews"),
                ],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
            )
            
            response = client.run_report(request=request)
            
            # Process response data
            daily_data = []
            totals = {"sessions": 0, "total_users": 0, "new_users": 0, "page_views": 0}
            
            for row in response.rows:
                date_str = row.dimension_values[0].value
                sessions = int(row.metric_values[0].value)
                total_users = int(row.metric_values[1].value)
                new_users = int(row.metric_values[2].value)
                page_views = int(row.metric_values[3].value)
                
                daily_data.append({
                    "date": date_str,
                    "sessions": sessions,
                    "total_users": total_users,
                    "new_users": new_users,
                    "page_views": page_views,
                })
                
                totals["sessions"] += sessions
                totals["total_users"] = max(totals["total_users"], total_users)  # Users are unique
                totals["new_users"] += new_users
                totals["page_views"] += page_views
            
            return {
                "status": "success",
                "data": {
                    "daily": daily_data,
                    "totals": totals,
                    "period": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "days": len(daily_data),
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "reason": "api_request_failed",
                "error": str(e)
            }
    
    def get_traffic_sources(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "yesterday",
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get traffic sources data from GA4."""
        client = self._get_client()
        if not client or not self.property_id:
            return {"status": "skipped", "reason": "not_configured"}
        
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[
                    Dimension(name="sessionSource"),
                    Dimension(name="sessionMedium"),
                    Dimension(name="sessionCampaignName"),
                ],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="totalUsers"),
                    Metric(name="conversions"),
                ],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
                limit=limit,
            )
            
            response = client.run_report(request=request)
            
            # Process response data
            sources_data = []
            totals = {"sessions": 0, "users": 0, "conversions": 0}
            
            for row in response.rows:
                source = row.dimension_values[0].value
                medium = row.dimension_values[1].value
                campaign = row.dimension_values[2].value
                sessions = int(row.metric_values[0].value)
                users = int(row.metric_values[1].value)
                conversions = int(row.metric_values[2].value)
                
                sources_data.append({
                    "source": source,
                    "medium": medium,
                    "campaign": campaign if campaign != "(not set)" else None,
                    "sessions": sessions,
                    "users": users,
                    "conversions": conversions,
                })
                
                totals["sessions"] += sessions
                totals["users"] += users
                totals["conversions"] += conversions
            
            return {
                "status": "success",
                "data": {
                    "sources": sources_data,
                    "totals": totals,
                    "period": {
                        "start_date": start_date,
                        "end_date": end_date,
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "reason": "api_request_failed",
                "error": str(e)
            }
    
    def get_events_data(
        self,
        start_date: str = "30daysAgo", 
        end_date: str = "yesterday",
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get events data from GA4."""
        client = self._get_client()
        if not client or not self.property_id:
            return {"status": "skipped", "reason": "not_configured"}
        
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[Dimension(name="eventName")],
                metrics=[
                    Metric(name="eventCount"),
                    Metric(name="eventCountPerUser"),
                ],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)],
                limit=limit,
            )
            
            response = client.run_report(request=request)
            
            # Process response data
            events_data = []
            total_events = 0
            
            for row in response.rows:
                event_name = row.dimension_values[0].value
                event_count = int(row.metric_values[0].value)
                events_per_user = float(row.metric_values[1].value)
                
                events_data.append({
                    "event_name": event_name,
                    "event_count": event_count,
                    "events_per_user": round(events_per_user, 2),
                })
                
                total_events += event_count
            
            return {
                "status": "success",
                "data": {
                    "events": events_data,
                    "total_events": total_events,
                    "period": {
                        "start_date": start_date,
                        "end_date": end_date,
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "reason": "api_request_failed",
                "error": str(e)
            }
    
    def get_device_analytics(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "yesterday",
    ) -> Dict[str, Any]:
        """Get device and platform analytics from GA4."""
        client = self._get_client()
        if not client or not self.property_id:
            return {"status": "skipped", "reason": "not_configured"}
        
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[
                    Dimension(name="deviceCategory"),
                    Dimension(name="operatingSystem"),
                ],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="totalUsers"),
                    Metric(name="screenPageViews"),
                ],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            )
            
            response = client.run_report(request=request)
            
            # Process response data
            devices_data = []
            totals = {"sessions": 0, "users": 0, "page_views": 0}
            
            for row in response.rows:
                device_category = row.dimension_values[0].value
                operating_system = row.dimension_values[1].value
                sessions = int(row.metric_values[0].value)
                users = int(row.metric_values[1].value)
                page_views = int(row.metric_values[2].value)
                
                devices_data.append({
                    "device_category": device_category,
                    "operating_system": operating_system,
                    "sessions": sessions,
                    "users": users,
                    "page_views": page_views,
                })
                
                totals["sessions"] += sessions
                totals["users"] += users
                totals["page_views"] += page_views
            
            return {
                "status": "success",
                "data": {
                    "devices": devices_data,
                    "totals": totals,
                    "period": {
                        "start_date": start_date,
                        "end_date": end_date,
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "reason": "api_request_failed",
                "error": str(e)
            }


# Global instance
ga4_data_client = GA4DataClient()


def health_check() -> Dict[str, Any]:
    """Check GA4 Data API health."""
    return ga4_data_client.health_check()


def get_sessions_and_users(start_date: str = "30daysAgo", end_date: str = "yesterday") -> Dict[str, Any]:
    """Get sessions and users data from GA4."""
    return ga4_data_client.get_sessions_and_users(start_date, end_date)


def get_traffic_sources(start_date: str = "30daysAgo", end_date: str = "yesterday", limit: int = 10) -> Dict[str, Any]:
    """Get traffic sources data from GA4."""
    return ga4_data_client.get_traffic_sources(start_date, end_date, limit)


def get_events_data(start_date: str = "30daysAgo", end_date: str = "yesterday", limit: int = 20) -> Dict[str, Any]:
    """Get events data from GA4."""
    return ga4_data_client.get_events_data(start_date, end_date, limit)


def get_device_analytics(start_date: str = "30daysAgo", end_date: str = "yesterday") -> Dict[str, Any]:
    """Get device and platform analytics from GA4."""
    return ga4_data_client.get_device_analytics(start_date, end_date)