from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# Car schemas
class CarBase(BaseModel):
    number: str
    class_name: str
    model: str


class CarResponse(CarBase):
    id: int

    class Config:
        from_attributes = True


# Run schemas
class RunBase(BaseModel):
    car_id: int


class RunStartRequest(BaseModel):
    car_id: int
    # photo will be uploaded as file


class RunStartResponse(BaseModel):
    id: int
    car_id: int
    start_time: datetime
    start_photo_url: Optional[str]
    penalties: int
    is_dnf: bool
    is_aborted: bool
    is_missed_trip: bool
    finish_confirmed: bool

    class Config:
        from_attributes = True


class RunFinishRequest(BaseModel):
    run_id: int
    # photo will be uploaded as file


class RunFinishResponse(BaseModel):
    id: int
    car_id: int
    start_time: datetime
    finish_time: Optional[datetime]
    raw_time: Optional[float]
    start_photo_url: Optional[str]
    finish_photo_url: Optional[str]
    penalties: int
    adjusted_time: Optional[float]
    is_dnf: bool
    is_aborted: bool
    is_missed_trip: bool
    finish_confirmed: bool

    class Config:
        from_attributes = True


class RunUpdateRequest(BaseModel):
    penalties: Optional[int] = None
    is_dnf: Optional[bool] = None
    is_aborted: Optional[bool] = None
    is_missed_trip: Optional[bool] = None


class RunResponse(BaseModel):
    id: int
    car_id: int
    start_time: datetime
    finish_time: Optional[datetime]
    raw_time: Optional[float]
    start_photo_url: Optional[str]
    finish_photo_url: Optional[str]
    penalties: int
    adjusted_time: Optional[float]
    is_dnf: bool
    is_aborted: bool
    is_missed_trip: bool
    finish_confirmed: bool
    car: Optional[CarResponse] = None

    class Config:
        from_attributes = True


class RunDetailedResponse(RunResponse):
    created_at: datetime
    updated_at: datetime


class ListRunsResponse(BaseModel):
    runs: List[RunResponse]


# Generic response envelope
class APIResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None
