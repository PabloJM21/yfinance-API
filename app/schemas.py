from datetime import date
from typing import List
from pydantic import BaseModel

class Candle(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    average: float

class HistoryRequest(BaseModel):
    ticker: str 
    start: date
    end: date


class HistoryResponse(BaseModel):
    ticker: str
    start: date
    end: date
    results: List[Candle]