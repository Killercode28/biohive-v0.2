"""
Loads aggregated signals from DB into pandas DataFrame
"""

import pandas as pd
from datetime import date
from backend.store import get_db_session
from backend.schemas import AggregatedSignal


class AggregatedSignalLoader:
    def __init__(self):
        pass

    def load_range(self, start_date: date = None, end_date: date = None) -> pd.DataFrame:
        with get_db_session() as db:
            query = db.query(AggregatedSignal)

            if start_date:
                query = query.filter(AggregatedSignal.date >= start_date)
            if end_date:
                query = query.filter(AggregatedSignal.date <= end_date)

            rows = query.order_by(AggregatedSignal.date).all()

        data = [
            {
                "date": r.date,
                "total_fever": r.total_fever,
                "total_cough": r.total_cough,
                "total_gi": r.total_gi,
                "participating_nodes": r.participating_nodes,
                "risk_score": r.risk_score,
                "risk_level": r.risk_level,
            }
            for r in rows
        ]

        return pd.DataFrame(data)
