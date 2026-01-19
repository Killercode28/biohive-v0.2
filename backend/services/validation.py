"""
Validation Service - Warning-Based System
Implements soft validation with warnings instead of hard limits
All data is accepted but flagged if suspicious
"""

from typing import Dict, List
from datetime import date, timedelta
from sqlalchemy.orm import Session

from schemas import DailyReport


class ValidationError(Exception):
    """
    Custom exception for validation errors
    Now only used for critical errors (missing fields, invalid node, etc.)
    """
    
    def __init__(self, field: str, message: str, value=None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(self.message)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API error responses"""
        return {
            'field': self.field,
            'message': self.message,
            'value': self.value
        }


def validate_report(
    node_id: str,
    symptoms: Dict,
    report_date: date,
    db: Session
) -> Dict:
    """
    Validate symptom report with warning-based system.
    NO HARD LIMITS - All data accepted with appropriate warnings.
    
    Args:
        node_id: Node identifier
        symptoms: {'fever': int, 'cough': int, 'gi': int}
        report_date: Date of report
        db: Database session for checking previous reports
    
    Returns:
        {
            'valid': bool,
            'warnings': List[Dict],  # Now includes severity levels
            'errors': List[Dict]
        }
    
    Raises:
        ValidationError: Only for critical errors (duplicate, invalid node, etc.)
    """
    warnings = []
    errors = []
    
    # === BASIC VALIDATION (Critical Only) ===
    
    # Ensure symptom values exist and are integers
    try:
        fever = int(symptoms.get('fever', 0))
        cough = int(symptoms.get('cough', 0))
        gi = int(symptoms.get('gi', 0))
    except (ValueError, TypeError):
        raise ValidationError(
            'symptoms',
            'Symptom counts must be valid integers',
            symptoms
        )
    
    # === NEGATIVE VALUES (Critical Error) ===
    
    if fever < 0:
        raise ValidationError(
            'symptoms.fever',
            'Fever count cannot be negative',
            fever
        )
    
    if cough < 0:
        raise ValidationError(
            'symptoms.cough',
            'Cough count cannot be negative',
            cough
        )
    
    if gi < 0:
        raise ValidationError(
            'symptoms.gi',
            'GI count cannot be negative',
            gi
        )
    
    # === SUSPICIOUS RANGE DETECTION (Warnings Only) ===
    
    # Fever warnings
    if fever > 100:
        warnings.append({
            'severity': 'HIGH',
            'symptom': 'fever',
            'value': fever,
            'message': f'Extremely high fever count: {fever} (typical max: 50)',
            'suggestion': 'Please verify this count is accurate'
        })
    elif fever > 50:
        warnings.append({
            'severity': 'MEDIUM',
            'symptom': 'fever',
            'value': fever,
            'message': f'Unusually high fever count: {fever} (typical range: 0-50)',
            'suggestion': 'Double-check if this reflects actual cases'
        })
    elif fever > 30:
        warnings.append({
            'severity': 'LOW',
            'symptom': 'fever',
            'value': fever,
            'message': f'Higher than average fever count: {fever}',
            'suggestion': 'Monitor for potential outbreak'
        })
    
    # Cough warnings
    if cough > 100:
        warnings.append({
            'severity': 'HIGH',
            'symptom': 'cough',
            'value': cough,
            'message': f'Extremely high cough count: {cough} (typical max: 50)',
            'suggestion': 'Please verify this count is accurate'
        })
    elif cough > 50:
        warnings.append({
            'severity': 'MEDIUM',
            'symptom': 'cough',
            'value': cough,
            'message': f'Unusually high cough count: {cough} (typical range: 0-50)',
            'suggestion': 'Double-check if this reflects actual cases'
        })
    elif cough > 30:
        warnings.append({
            'severity': 'LOW',
            'symptom': 'cough',
            'value': cough,
            'message': f'Higher than average cough count: {cough}',
            'suggestion': 'Monitor for potential outbreak'
        })
    
    # GI warnings
    if gi > 60:
        warnings.append({
            'severity': 'HIGH',
            'symptom': 'gi',
            'value': gi,
            'message': f'Extremely high GI count: {gi} (typical max: 30)',
            'suggestion': 'Please verify this count is accurate'
        })
    elif gi > 30:
        warnings.append({
            'severity': 'MEDIUM',
            'symptom': 'gi',
            'value': gi,
            'message': f'Unusually high GI count: {gi} (typical range: 0-30)',
            'suggestion': 'Double-check if this reflects actual cases'
        })
    elif gi > 15:
        warnings.append({
            'severity': 'LOW',
            'symptom': 'gi',
            'value': gi,
            'message': f'Higher than average GI count: {gi}',
            'suggestion': 'Monitor for potential outbreak'
        })
    
    # === DATE VALIDATION ===
    
    # Check if date is in the future (Critical Error)
    if report_date > date.today():
        raise ValidationError(
            'date',
            'Report date cannot be in the future',
            report_date.isoformat()
        )
    
    # Check if date is too old (Warning)
    days_old = (date.today() - report_date).days
    if days_old > 60:
        warnings.append({
            'severity': 'HIGH',
            'field': 'date',
            'value': report_date.isoformat(),
            'message': f'Report is {days_old} days old',
            'suggestion': 'Very old data - verify accuracy'
        })
    elif days_old > 30:
        warnings.append({
            'severity': 'MEDIUM',
            'field': 'date',
            'value': report_date.isoformat(),
            'message': f'Report is {days_old} days old',
            'suggestion': 'Consider submitting more recent data'
        })
    elif days_old > 7:
        warnings.append({
            'severity': 'LOW',
            'field': 'date',
            'value': report_date.isoformat(),
            'message': f'Report is {days_old} days old',
            'suggestion': 'Backfilling data - ensure accuracy'
        })
    
    # === DUPLICATE CHECK (Critical Error) ===
    
    existing_report = db.query(DailyReport).filter(
        DailyReport.node_id == node_id,
        DailyReport.date == report_date
    ).first()
    
    if existing_report:
        raise ValidationError(
            'date',
            f'Report already exists for {node_id} on {report_date.isoformat()}. Use update endpoint to modify.',
            report_date.isoformat()
        )
    
    # === SPIKE DETECTION (Warnings) ===
    
    # Get previous day's report
    previous_date = report_date - timedelta(days=1)
    previous_report = db.query(DailyReport).filter(
        DailyReport.node_id == node_id,
        DailyReport.date == previous_date
    ).first()
    
    if previous_report:
        # Fever spike
        if fever > 0 and previous_report.fever_count > 0:
            multiplier = fever / previous_report.fever_count
            if multiplier > 5:
                warnings.append({
                    'severity': 'HIGH',
                    'symptom': 'fever',
                    'value': fever,
                    'previous_value': previous_report.fever_count,
                    'message': f'Extreme fever spike: {multiplier:.1f}x increase from previous day',
                    'suggestion': 'Verify data accuracy - possible outbreak or data entry error'
                })
            elif multiplier > 3:
                warnings.append({
                    'severity': 'MEDIUM',
                    'symptom': 'fever',
                    'value': fever,
                    'previous_value': previous_report.fever_count,
                    'message': f'Significant fever spike: {multiplier:.1f}x increase from previous day',
                    'suggestion': 'Monitor closely for outbreak development'
                })
            elif multiplier > 2:
                warnings.append({
                    'severity': 'LOW',
                    'symptom': 'fever',
                    'value': fever,
                    'previous_value': previous_report.fever_count,
                    'message': f'Notable fever increase: {multiplier:.1f}x from previous day',
                    'suggestion': 'Continue monitoring'
                })
        
        # Cough spike
        if cough > 0 and previous_report.cough_count > 0:
            multiplier = cough / previous_report.cough_count
            if multiplier > 5:
                warnings.append({
                    'severity': 'HIGH',
                    'symptom': 'cough',
                    'value': cough,
                    'previous_value': previous_report.cough_count,
                    'message': f'Extreme cough spike: {multiplier:.1f}x increase from previous day',
                    'suggestion': 'Verify data accuracy - possible outbreak or data entry error'
                })
            elif multiplier > 3:
                warnings.append({
                    'severity': 'MEDIUM',
                    'symptom': 'cough',
                    'value': cough,
                    'previous_value': previous_report.cough_count,
                    'message': f'Significant cough spike: {multiplier:.1f}x increase from previous day',
                    'suggestion': 'Monitor closely for outbreak development'
                })
        
        # GI spike
        if gi > 0 and previous_report.gi_count > 0:
            multiplier = gi / previous_report.gi_count
            if multiplier > 5:
                warnings.append({
                    'severity': 'HIGH',
                    'symptom': 'gi',
                    'value': gi,
                    'previous_value': previous_report.gi_count,
                    'message': f'Extreme GI spike: {multiplier:.1f}x increase from previous day',
                    'suggestion': 'Verify data accuracy - possible outbreak or data entry error'
                })
            elif multiplier > 3:
                warnings.append({
                    'severity': 'MEDIUM',
                    'symptom': 'gi',
                    'value': gi,
                    'previous_value': previous_report.gi_count,
                    'message': f'Significant GI spike: {multiplier:.1f}x increase from previous day',
                    'suggestion': 'Monitor closely for outbreak development'
                })
    
    # === WEEKEND/HOLIDAY CHECK (Warnings) ===
    
    is_weekend = report_date.weekday() in [5, 6]  # Saturday=5, Sunday=6
    
    if is_weekend:
        total_symptoms = fever + cough + gi
        if total_symptoms > 50:
            warnings.append({
                'severity': 'MEDIUM',
                'field': 'date',
                'value': report_date.isoformat(),
                'message': f'High symptom count ({total_symptoms}) on weekend',
                'suggestion': 'Unusual for clinic operations - verify accuracy'
            })
        elif total_symptoms > 20:
            warnings.append({
                'severity': 'LOW',
                'field': 'date',
                'value': report_date.isoformat(),
                'message': f'Notable activity ({total_symptoms} symptoms) on weekend',
                'suggestion': 'Confirm clinic was operational'
            })
    
    # === ALL-ZERO CHECK (Warning) ===
    
    if fever == 0 and cough == 0 and gi == 0:
        warnings.append({
            'severity': 'LOW',
            'field': 'symptoms',
            'message': 'All symptom counts are zero',
            'suggestion': 'Verify: Was clinic open? Is this intentional?'
        })
    
    # === UNUSUALLY HIGH TOTAL (Warning) ===
    
    total_symptoms = fever + cough + gi
    if total_symptoms > 200:
        warnings.append({
            'severity': 'HIGH',
            'field': 'symptoms',
            'value': total_symptoms,
            'message': f'Extremely high total symptom count: {total_symptoms}',
            'suggestion': 'Verify this is not a data entry error or aggregation mistake'
        })
    elif total_symptoms > 100:
        warnings.append({
            'severity': 'MEDIUM',
            'field': 'symptoms',
            'value': total_symptoms,
            'message': f'Very high total symptom count: {total_symptoms}',
            'suggestion': 'Confirm accuracy - potential outbreak signal'
        })
    
    # === PATTERN DETECTION (Warning) ===
    
    # Check for suspicious round numbers
    if fever > 0 and fever % 10 == 0 and fever >= 50:
        warnings.append({
            'severity': 'LOW',
            'symptom': 'fever',
            'value': fever,
            'message': f'Suspiciously round number: {fever}',
            'suggestion': 'Verify this is an actual count, not an estimate'
        })
    
    if cough > 0 and cough % 10 == 0 and cough >= 50:
        warnings.append({
            'severity': 'LOW',
            'symptom': 'cough',
            'value': cough,
            'message': f'Suspiciously round number: {cough}',
            'suggestion': 'Verify this is an actual count, not an estimate'
        })
    
    # === CALCULATE SUSPICION SCORE ===
    
    suspicion_score = 0
    for warning in warnings:
        if warning['severity'] == 'HIGH':
            suspicion_score += 10
        elif warning['severity'] == 'MEDIUM':
            suspicion_score += 5
        elif warning['severity'] == 'LOW':
            suspicion_score += 2
    
    return {
        'valid': True,  # Always valid unless critical error raised
        'warnings': warnings,
        'errors': errors,
        'suspicion_score': suspicion_score,
        'requires_review': suspicion_score >= 15  # High suspicion threshold
    }


def validate_node_exists(node_id: str, db: Session) -> bool:
    """
    Check if node exists in database
    
    Args:
        node_id: Node identifier
        db: Database session
    
    Returns:
        bool: True if node exists
    
    Raises:
        ValidationError: If node doesn't exist
    """
    from schemas import Node
    
    node = db.query(Node).filter(Node.node_id == node_id).first()
    
    if not node:
        raise ValidationError(
            'node_id',
            f'Node {node_id} does not exist',
            node_id
        )
    
    if node.status != 'ACTIVE':
        raise ValidationError(
            'node_id',
            f'Node {node_id} is not active (status: {node.status})',
            node_id
        )
    
    return True


def validate_date_format(date_string: str) -> date:
    """
    Validate and parse date string
    Follows Section 9 Pitfall 2: ALWAYS use YYYY-MM-DD
    
    Args:
        date_string: Date in YYYY-MM-DD format
    
    Returns:
        date: Parsed date object
    
    Raises:
        ValidationError: If date format is invalid
    """
    try:
        return date.fromisoformat(date_string)
    except ValueError:
        raise ValidationError(
            'date',
            'Date must be in YYYY-MM-DD format (ISO 8601)',
            date_string
        )