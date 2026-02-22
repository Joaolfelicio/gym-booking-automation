import requests
import json
import logging
from typing import List, Optional
from .models import LoginResult, GymClass, BookingResponse, UserConfig

class GymBookingService:
    def __init__(self, app_id: str, client: str, client_version: str):
        self.app_id = app_id
        self.client = client
        self.client_version = client_version
        self.base_url = "https://services.mywellness.com"
        self.calendar_url = "https://calendar.mywellness.com"
        
        self.headers_common = {
            "x-mwapps-appid": self.app_id,
            "x-mwapps-client": self.client,
            "x-mwapps-clientversion": self.client_version,
            "Content-Type": "application/json"
        }

    def login(self, user: UserConfig) -> Optional[LoginResult]:
        url = f"{self.base_url}/Application/{self.app_id}/Login?_c=en-US"
        payload = {
            "keepMeLoggedIn": True,
            "password": user.password,
            "username": user.username
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers_common, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            token = data.get("token")
            user_context = data.get("data", {}).get("userContext", {})
            user_id = user_context.get("id")
            
            if token and user_id:
                logging.info(f"Successfully logged in as {user.username} ({user_id})")
                return LoginResult(token=token, user_id=user_id)
            
            logging.error(f"Login response for {user.username} missing critical data. Response: {response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error during login for {user.username}: {e}. Response: {getattr(e.response, 'text', 'No response body')}")
            return None

    def fetch_classes(self, token: str, facility_id: str, from_date: str, to_date: str) -> List[GymClass]:
        url = f"{self.calendar_url}/v2/enduser/class/Search"
        params = {
            "eventTypes": "Class",
            "facilityId": facility_id,
            "fromDate": from_date,
            "toDate": to_date
        }
        headers = {**self.headers_common, "Authorization": f"Bearer {token}"}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return [
                GymClass(
                    id=item.get("id"),
                    name=item.get("name"),
                    partition_date=item.get("partitionDate"),
                    booking_opens_on=item.get("bookingInfo", {}).get("bookingOpensOn", "")
                ) for item in response.json()
            ]
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching classes: {e}")
            return []

    def book_class(self, token: str, user_id: str, class_id: str, partition_date: int) -> BookingResponse:
        url = f"{self.calendar_url}/v2/enduser/class/Book?_c=en-US"
        payload = {
            "partitionDate": partition_date,
            "userId": user_id,
            "classId": class_id
        }
        headers = {**self.headers_common, "Authorization": f"Bearer {token}"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict):
                return BookingResponse(result=data.get("result", "Unknown"))
            elif isinstance(data, list) and len(data) > 0:
                error_msg = data[0].get("errorMessage", "Unknown error")
                logging.error(f"Booking failed with API error: {error_msg}. Full response: {json.dumps(data)}")
                return BookingResponse(result="Error", error_message=error_msg)
            else:
                logging.error(f"Unexpected booking response format: {data}")
                return BookingResponse(result="Unknown")
        except requests.exceptions.RequestException as e:
            error_body = getattr(e.response, 'text', 'No response body')
            logging.error(f"Error during booking: {e}. Response: {error_body}")
            return BookingResponse(result="Error", error_message=str(e))
