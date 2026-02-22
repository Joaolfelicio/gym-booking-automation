from pydantic import BaseModel
from typing import List, Optional

class UserConfig(BaseModel):
    username: str
    password: str

class ClassConfig(BaseModel):
    name: str
    weekday: str
    opening_hour: str
    user_names: List[str]

class AppConfig(BaseModel):
    app_id: str
    client: str
    client_version: str
    facility_id: str
    users: List[UserConfig]
    classes: List[ClassConfig]

class LoginResult(BaseModel):
    token: str
    user_id: str

class GymClass(BaseModel):
    id: str
    name: str
    partition_date: int
    booking_opens_on: str

class BookingResponse(BaseModel):
    result: str
    error_message: Optional[str] = None
