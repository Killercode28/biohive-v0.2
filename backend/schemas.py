from pydantic import BaseModel
from datetime import date

class NodeReport(BaseModel):
    node_id: str
    zone_id: str
    date: date
    fever_count: int
    cough_count: int
    gi_count: int
