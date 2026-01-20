# backend/services/aggregation.py
"""
Aggregation Service for BioHIVE Disease Surveillance System

Aggregates daily symptom reports across all nodes to compute system-wide metrics,
risk scores, and risk levels for disease outbreak detection.
"""
from backend.store import get_db_session
from datetime import date, datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.schemas import DailyReport, AggregatedSignal, Node



class AggregationService:
    """
    Service for aggregating daily symptom reports across all healthcare nodes.
    
    Provides deterministic, idempotent aggregation with rule-based risk scoring.
    """
    
    # Risk scoring thresholds (per-symptom daily totals across all nodes)
    FEVER_LOW_THRESHOLD = 50
    FEVER_MODERATE_THRESHOLD = 150
    FEVER_HIGH_THRESHOLD = 300
    
    COUGH_LOW_THRESHOLD = 75
    COUGH_MODERATE_THRESHOLD = 200
    COUGH_HIGH_THRESHOLD = 400
    
    GI_LOW_THRESHOLD = 30
    GI_MODERATE_THRESHOLD = 100
    GI_HIGH_THRESHOLD = 200
    
    # Combined total thresholds
    TOTAL_LOW_THRESHOLD = 150
    TOTAL_MODERATE_THRESHOLD = 450
    TOTAL_HIGH_THRESHOLD = 900
    
    def __init__(self, db: Session):
        """
        Initialize aggregation service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def aggregate_date(self, target_date: date) -> Dict:
        """
        Aggregate all daily reports for a specific date.
        
        Computes total symptom counts, participating nodes, risk score,
        and risk level. Upserts result into aggregated_signals table.
        
        Args:
            target_date: Date to aggregate (datetime.date object)
        
        Returns:
            Dictionary containing aggregated data:
            {
                'date': date,
                'total_fever': int,
                'total_cough': int,
                'total_gi': int,
                'participating_nodes': int,
                'risk_score': float,
                'risk_level': str,
                'anomaly_detected': bool,
                'computed_at': datetime
            }
        
        Raises:
            ValueError: If target_date is invalid or in the future
            RuntimeError: If database operation fails
        """
        # Validate input date
        if not isinstance(target_date, date):
            raise ValueError(f"target_date must be datetime.date object, got {type(target_date)}")
        
        if target_date > date.today():
            raise ValueError(f"Cannot aggregate future date: {target_date}")
        
        try:
            # Fetch all reports for the target date
            reports = self.db.query(DailyReport).filter(
                DailyReport.date == target_date
            ).all()
            
            # Compute aggregated metrics
            total_fever = sum(r.fever_count for r in reports)
            total_cough = sum(r.cough_count for r in reports)
            total_gi = sum(r.gi_count for r in reports)
            participating_nodes = len(set(r.node_id for r in reports))
            
            # Compute risk score and level
            risk_score = self._compute_risk_score(
                total_fever, total_cough, total_gi, participating_nodes
            )
            risk_level = self._compute_risk_level(risk_score)
            
            # Placeholder for ML anomaly detection (to be implemented by ML team)
            anomaly_detected = False
            
            # Current timestamp
            computed_at = datetime.utcnow()
            
            # Upsert into aggregated_signals table
            existing = self.db.query(AggregatedSignal).filter(
                AggregatedSignal.date == target_date
            ).first()
            
            if existing:
                # Update existing record
                existing.total_fever = total_fever
                existing.total_cough = total_cough
                existing.total_gi = total_gi
                existing.participating_nodes = participating_nodes
                existing.risk_score = risk_score
                existing.risk_level = risk_level
                existing.anomaly_detected = anomaly_detected
                existing.computed_at = computed_at
                
                aggregated = existing
            else:
                # Create new record
                aggregated = AggregatedSignal(
                    date=target_date,
                    total_fever=total_fever,
                    total_cough=total_cough,
                    total_gi=total_gi,
                    participating_nodes=participating_nodes,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    anomaly_detected=anomaly_detected,
                    computed_at=computed_at
                )
                self.db.add(aggregated)
            
            # Commit transaction
            self.db.commit()
            self.db.refresh(aggregated)
            
            # Return as dictionary
            return {
                'date': aggregated.date,
                'total_fever': aggregated.total_fever,
                'total_cough': aggregated.total_cough,
                'total_gi': aggregated.total_gi,
                'participating_nodes': aggregated.participating_nodes,
                'risk_score': float(aggregated.risk_score),
                'risk_level': aggregated.risk_level,
                'anomaly_detected': aggregated.anomaly_detected,
                'computed_at': aggregated.computed_at
            }
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            # Rollback on any database error
            self.db.rollback()
            raise RuntimeError(f"Failed to aggregate date {target_date}: {str(e)}")
    
    def _compute_risk_score(
        self,
        total_fever: int,
        total_cough: int,
        total_gi: int,
        participating_nodes: int
    ) -> float:
        """
        Compute rule-based risk score from aggregated symptom counts.
        
        Risk score is a weighted sum based on symptom severity thresholds:
        - Each symptom contributes 0-40 points based on threshold levels
        - Combined total contributes 0-20 points
        - Final score is 0-100
        
        Args:
            total_fever: Total fever cases across all nodes
            total_cough: Total cough cases across all nodes
            total_gi: Total GI cases across all nodes
            participating_nodes: Number of nodes that submitted reports
        
        Returns:
            Risk score as float (0.0 - 100.0)
        """
        score = 0.0
        
        # Fever contribution (0-35 points)
        if total_fever >= self.FEVER_HIGH_THRESHOLD:
            score += 35.0
        elif total_fever >= self.FEVER_MODERATE_THRESHOLD:
            score += 20.0
        elif total_fever >= self.FEVER_LOW_THRESHOLD:
            score += 10.0
        
        # Cough contribution (0-30 points)
        if total_cough >= self.COUGH_HIGH_THRESHOLD:
            score += 30.0
        elif total_cough >= self.COUGH_MODERATE_THRESHOLD:
            score += 18.0
        elif total_cough >= self.COUGH_LOW_THRESHOLD:
            score += 8.0
        
        # GI contribution (0-20 points)
        if total_gi >= self.GI_HIGH_THRESHOLD:
            score += 20.0
        elif total_gi >= self.GI_MODERATE_THRESHOLD:
            score += 12.0
        elif total_gi >= self.GI_LOW_THRESHOLD:
            score += 5.0
        
        # Combined total contribution (0-15 points)
        total_symptoms = total_fever + total_cough + total_gi
        if total_symptoms >= self.TOTAL_HIGH_THRESHOLD:
            score += 15.0
        elif total_symptoms >= self.TOTAL_MODERATE_THRESHOLD:
            score += 8.0
        elif total_symptoms >= self.TOTAL_LOW_THRESHOLD:
            score += 3.0
        
        # Ensure score is in valid range
        return min(100.0, max(0.0, score))
    
    def _compute_risk_level(self, risk_score: float) -> str:
        """
        Convert numeric risk score to categorical risk level.
        
        Risk Levels:
        - LOW: score < 30
        - MODERATE: 30 <= score < 60
        - HIGH: score >= 60
        
        Args:
            risk_score: Numeric risk score (0-100)
        
        Returns:
            Risk level string: 'LOW', 'MODERATE', or 'HIGH'
        """
        if risk_score >= 60.0:
            return 'HIGH'
        elif risk_score >= 30.0:
            return 'MODERATE'
        else:
            return 'LOW'
    
    def aggregate_date_range(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Dict]:
        """
        Aggregate multiple dates in a range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            Dictionary mapping date strings to aggregation results
        
        Raises:
            ValueError: If date range is invalid
        """
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")
        
        results = {}
        current_date = start_date
        
        while current_date <= end_date:
            try:
                result = self.aggregate_date(current_date)
                results[str(current_date)] = result
            except Exception as e:
                # Log error but continue with other dates
                results[str(current_date)] = {
                    'error': str(e),
                    'date': current_date
                }
            
            # Move to next day
            from datetime import timedelta
            current_date += timedelta(days=1)
        
        return results
    
    def get_aggregated_data(
        self,
        target_date: date
    ) -> Optional[Dict]:
        """
        Retrieve existing aggregated data for a date without recomputing.
        
        Args:
            target_date: Date to retrieve
        
        Returns:
            Dictionary with aggregated data or None if not found
        """
        try:
            aggregated = self.db.query(AggregatedSignal).filter(
                AggregatedSignal.date == target_date
            ).first()
            
            if not aggregated:
                return None
            
            return {
                'date': aggregated.date,
                'total_fever': aggregated.total_fever,
                'total_cough': aggregated.total_cough,
                'total_gi': aggregated.total_gi,
                'participating_nodes': aggregated.participating_nodes,
                'risk_score': float(aggregated.risk_score),
                'risk_level': aggregated.risk_level,
                'anomaly_detected': aggregated.anomaly_detected,
                'computed_at': aggregated.computed_at
            }
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve aggregated data for {target_date}: {str(e)}")