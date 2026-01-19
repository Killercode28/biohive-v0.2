"""
Database models for BioHIVE
Implements exact schema from Section 3 of Integration Contract
"""

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Date, 
    Boolean, CheckConstraint, ForeignKey, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    """Generate UUID as string for compatibility"""
    return str(uuid.uuid4())


class Node(Base):
    """
    Section 3.1: nodes table
    Stores information about each clinic/node
    """
    __tablename__ = 'nodes'
    
    node_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(20), default='ACTIVE')
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_report_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'node_id': self.node_id,
            'name': self.name,
            'location': {
                'lat': self.latitude,
                'lng': self.longitude
            },
            'status': self.status,
            'last_report': self.last_report_at.isoformat() + 'Z' if self.last_report_at else None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }


class DailyReport(Base):
    """
    Section 3.2: daily_reports table
    Stores daily symptom counts from each node
    """
    __tablename__ = 'daily_reports'
    
    report_id = Column(String(36), primary_key=True, default=generate_uuid)
    node_id = Column(String(50), ForeignKey('nodes.node_id'), nullable=False)
    date = Column(Date, nullable=False)
    fever_count = Column(Integer, nullable=False)
    cough_count = Column(Integer, nullable=False)
    gi_count = Column(Integer, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    anomaly_score = Column(Float, default=0.0)
    suspicion_score = Column(Integer, default=0)  # NEW: Warning-based suspicion score
    requires_review = Column(Boolean, default=False)  # NEW: Flag for manual review
    
    # Constraints - REMOVED UPPER LIMITS, only prevent negative values
    __table_args__ = (
        CheckConstraint('fever_count >= 0', name='fever_positive'),
        CheckConstraint('cough_count >= 0', name='cough_positive'),
        CheckConstraint('gi_count >= 0', name='gi_positive'),
        UniqueConstraint('node_id', 'date', name='unique_node_date'),
    )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'report_id': self.report_id,
            'node_id': self.node_id,
            'date': self.date.isoformat(),
            'symptoms': {
                'fever': self.fever_count,
                'cough': self.cough_count,
                'gi': self.gi_count
            },
            'submitted_at': self.submitted_at.isoformat() + 'Z',
            'anomaly_score': float(self.anomaly_score),
            'suspicion_score': self.suspicion_score,
            'requires_review': self.requires_review
        }


class AggregatedSignal(Base):
    """
    Section 3.3: aggregated_signals table
    Stores daily aggregated data across all nodes
    """
    __tablename__ = 'aggregated_signals'
    
    date = Column(Date, primary_key=True)
    total_fever = Column(Integer, nullable=False)
    total_cough = Column(Integer, nullable=False)
    total_gi = Column(Integer, nullable=False)
    participating_nodes = Column(Integer, nullable=False)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(20), default='LOW')
    anomaly_detected = Column(Boolean, default=False)
    computed_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'date': self.date.isoformat(),
            'total_fever': self.total_fever,
            'total_cough': self.total_cough,
            'total_gi': self.total_gi,
            'participating_nodes': self.participating_nodes,
            'risk_score': float(self.risk_score),
            'risk_level': self.risk_level,
            'anomaly_detected': self.anomaly_detected
        }


class AuditTrail(Base):
    """
    Section 3.4: audit_trail table
    Cryptographic chain for tamper detection
    """
    __tablename__ = 'audit_trail'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey('daily_reports.report_id'), nullable=False)
    current_hash = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'current_hash': self.current_hash,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp.isoformat() + 'Z'
        }


class ForecastResult(Base):
    """
    Section 3.5: forecast_results table
    Stores ML model predictions
    """
    __tablename__ = 'forecast_results'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    forecast_date = Column(Date, nullable=False)
    prediction_date = Column(Date, nullable=False)
    symptom = Column(String(20), nullable=False)
    predicted_value = Column(Integer, nullable=False)
    lower_bound = Column(Integer, nullable=False)
    upper_bound = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    model_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'forecast_date': self.forecast_date.isoformat(),
            'prediction_date': self.prediction_date.isoformat(),
            'symptom': self.symptom,
            'predicted': self.predicted_value,
            'lower_bound': self.lower_bound,
            'upper_bound': self.upper_bound,
            'confidence': float(self.confidence),
            'model_name': self.model_name
        }
