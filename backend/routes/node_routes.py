"""
Node Routes
Implements Section 2.3 node endpoints with database integration
"""

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict

from store import get_db
from schemas import DailyReport, Node
from services.validation import (
    validate_report, validate_node_exists, 
    validate_date_format, ValidationError
)
from services.audit import AuditTrail
from services.response import (
    success_response, validation_error_response,
    not_found_response, internal_error_response
)

router = APIRouter(prefix="/node", tags=["node"])


@router.post("/report")
async def submit_report(
    report_data: Dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Submit daily symptom report
    Implements Section 2.3: POST /api/v1/node/report
    
    Request Body:
    {
        "node_id": "clinic_5",
        "token": "abc123def456",
        "date": "2026-01-16",
        "symptoms": {
            "fever": 7,
            "cough": 12,
            "gi": 3
        }
    }
    
    Returns:
        Success response with report details and audit hash
    """
    try:
        # Extract fields
        node_id = report_data.get('node_id')
        token = report_data.get('token')  # TODO: Validate token in auth implementation
        date_string = report_data.get('date')
        symptoms = report_data.get('symptoms', {})
        
        # Validate required fields
        if not node_id:
            return validation_error_response('node_id', 'Node ID is required')
        
        if not date_string:
            return validation_error_response('date', 'Date is required')
        
        if not symptoms:
            return validation_error_response('symptoms', 'Symptoms data is required')
        
        # Parse date (follows Section 9 Pitfall 2: YYYY-MM-DD)
        report_date = validate_date_format(date_string)
        
        # Validate node exists
        validate_node_exists(node_id, db)
        
        # Validate report data
        validation_result = validate_report(
            node_id=node_id,
            symptoms=symptoms,
            report_date=report_date,
            db=db
        )
        
        # Create report in database
        new_report = DailyReport(
            node_id=node_id,
            date=report_date,
            fever_count=symptoms.get('fever', 0),
            cough_count=symptoms.get('cough', 0),
            gi_count=symptoms.get('gi', 0),
            submitted_at=datetime.utcnow(),
            anomaly_score=0.0,  # TODO: Calculate anomaly score
            suspicion_score=validation_result['suspicion_score'],
            requires_review=validation_result['requires_review']
        )
        
        db.add(new_report)
        db.flush()  # Get report_id without committing
        
        # Create audit trail hash
        audit_service = AuditTrail(db)
        
        report_hash_data = {
            'report_id': new_report.report_id,
            'node_id': new_report.node_id,
            'date': new_report.date.isoformat(),
            'symptoms': {
                'fever': new_report.fever_count,
                'cough': new_report.cough_count,
                'gi': new_report.gi_count
            }
        }
        
        report_hash = audit_service.create_hash(report_hash_data)
        audit_result = audit_service.add_to_chain(new_report.report_id, report_hash)
        
        # Update node's last_report_at
        node = db.query(Node).filter(Node.node_id == node_id).first()
        node.last_report_at = datetime.utcnow()
        
        # Commit all changes
        db.commit()
        db.refresh(new_report)
        
        # Build response following Section 2.3
        response_data = {
            'report_id': new_report.report_id,
            'node_id': new_report.node_id,
            'date': new_report.date.isoformat(),
            'submitted_at': new_report.submitted_at.isoformat() + 'Z',
            'validation_status': 'ACCEPTED_WITH_WARNINGS' if validation_result['warnings'] else 'VALID',
            'warnings': validation_result['warnings'],
            'suspicion_score': validation_result['suspicion_score'],
            'requires_review': validation_result['requires_review'],
            'hash': report_hash
        }
        
        # Determine appropriate message based on warnings
        if validation_result['requires_review']:
            message = "Report submitted but flagged for review due to suspicious data"
        elif validation_result['warnings']:
            message = "Report submitted successfully with warnings"
        else:
            message = "Report submitted successfully"
        
        return success_response(
            data=response_data,
            message=message
        )
        
    except ValidationError as e:
        db.rollback()
        return validation_error_response(
            field=e.field,
            message=e.message,
            value=e.value
        )
    
    except Exception as e:
        db.rollback()
        print(f"❌ Error submitting report: {e}")
        return internal_error_response(
            message="Failed to submit report",
            details={'error': str(e)}
        )


@router.get("/{node_id}/history")
async def get_node_history(
    node_id: str,
    start_date: str = None,
    end_date: str = None,
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get node's submission history
    Implements Section 2.3: GET /api/v1/node/{node_id}/history
    
    Query Parameters:
        - start_date: YYYY-MM-DD (optional)
        - end_date: YYYY-MM-DD (optional)
        - limit: integer, default 30
    
    Returns:
        Success response with list of reports
    """
    try:
        # Validate node exists
        node = db.query(Node).filter(Node.node_id == node_id).first()
        if not node:
            return not_found_response('node', node_id)
        
        # Build query
        query = db.query(DailyReport).filter(DailyReport.node_id == node_id)
        
        # Apply date filters if provided
        if start_date:
            start = validate_date_format(start_date)
            query = query.filter(DailyReport.date >= start)
        
        if end_date:
            end = validate_date_format(end_date)
            query = query.filter(DailyReport.date <= end)
        
        # Order by date descending (most recent first)
        query = query.order_by(DailyReport.date.desc())
        
        # Apply limit
        query = query.limit(limit)
        
        reports = query.all()
        
        # Get total count for this node
        total_count = db.query(DailyReport).filter(
            DailyReport.node_id == node_id
        ).count()
        
        # Format response following Section 2.3
        reports_data = [
            {
                'report_id': report.report_id,
                'date': report.date.isoformat(),
                'symptoms': {
                    'fever': report.fever_count,
                    'cough': report.cough_count,
                    'gi': report.gi_count
                },
                'submitted_at': report.submitted_at.isoformat() + 'Z',
                'anomaly_score': float(report.anomaly_score),
                'suspicion_score': report.suspicion_score,
                'requires_review': report.requires_review
            }
            for report in reports
        ]
        
        response_data = {
            'node_id': node_id,
            'reports': reports_data,
            'total_count': total_count,
            'node_name': node.name
        }
        
        return success_response(
            data=response_data,
            message="History retrieved"
        )
        
    except ValidationError as e:
        return validation_error_response(
            field=e.field,
            message=e.message,
            value=e.value
        )
    
    except Exception as e:
        print(f"❌ Error getting history: {e}")
        return internal_error_response(
            message="Failed to retrieve history",
            details={'error': str(e)}
        )


@router.get("/status")
async def get_all_nodes_status(db: Session = Depends(get_db)):
    """
    Get status of all nodes
    Implements Section 2.3: GET /api/v1/nodes/status
    
    Returns:
        Success response with list of all nodes and their status
    """
    try:
        # Get all nodes
        nodes = db.query(Node).all()
        
        nodes_data = []
        active_count = 0
        
        for node in nodes:
            # Get total reports for this node
            total_reports = db.query(DailyReport).filter(
                DailyReport.node_id == node.node_id
            ).count()
            
            # Get flagged reports count
            flagged_reports = db.query(DailyReport).filter(
                DailyReport.node_id == node.node_id,
                DailyReport.requires_review == True
            ).count()
            
            # Get most recent report for risk level
            latest_report = db.query(DailyReport).filter(
                DailyReport.node_id == node.node_id
            ).order_by(DailyReport.date.desc()).first()
            
            # Simple risk calculation
            risk_level = 'LOW'
            if latest_report:
                total_symptoms = (
                    latest_report.fever_count + 
                    latest_report.cough_count + 
                    latest_report.gi_count
                )
                if total_symptoms > 100 or latest_report.suspicion_score >= 20:
                    risk_level = 'HIGH'
                elif total_symptoms > 50 or latest_report.suspicion_score >= 10:
                    risk_level = 'MODERATE'
            
            if node.status == 'ACTIVE':
                active_count += 1
            
            node_data = {
                'node_id': node.node_id,
                'name': node.name,
                'location': {
                    'lat': node.latitude,
                    'lng': node.longitude
                },
                'status': node.status,
                'last_report': node.last_report_at.isoformat() + 'Z' if node.last_report_at else None,
                'total_reports': total_reports,
                'flagged_reports': flagged_reports,
                'risk_level': risk_level
            }
            
            nodes_data.append(node_data)
        
        response_data = {
            'nodes': nodes_data,
            'total_nodes': len(nodes),
            'active_nodes': active_count,
            'inactive_nodes': len(nodes) - active_count
        }
        
        return success_response(
            data=response_data,
            message="Node statuses retrieved"
        )
        
    except Exception as e:
        print(f"❌ Error getting node status: {e}")
        return internal_error_response(
            message="Failed to retrieve node statuses",
            details={'error': str(e)}
        )


@router.get("/flagged")
async def get_flagged_reports(
    severity: str = None,
    min_score: int = None,
    db: Session = Depends(get_db)
):
    """
    Get reports flagged for review
    NEW ENDPOINT: Returns all suspicious reports
    
    Query Parameters:
        - severity: Filter by warning severity (HIGH, MEDIUM, LOW)
        - min_score: Minimum suspicion score (default: 10)
    
    Returns:
        List of flagged reports with warnings
    """
    try:
        # Build query
        query = db.query(DailyReport).filter(
            DailyReport.requires_review == True
        )
        
        # Apply suspicion score filter
        if min_score:
            query = query.filter(DailyReport.suspicion_score >= min_score)
        else:
            query = query.filter(DailyReport.suspicion_score >= 10)
        
        # Order by suspicion score (highest first)
        query = query.order_by(DailyReport.suspicion_score.desc())
        
        flagged_reports = query.all()
        
        # Format reports with node info
        reports_data = []
        for report in flagged_reports:
            # Get node info
            node = db.query(Node).filter(Node.node_id == report.node_id).first()
            
            report_data = {
                'report_id': report.report_id,
                'node_id': report.node_id,
                'node_name': node.name if node else 'Unknown',
                'date': report.date.isoformat(),
                'symptoms': {
                    'fever': report.fever_count,
                    'cough': report.cough_count,
                    'gi': report.gi_count,
                    'total': report.fever_count + report.cough_count + report.gi_count
                },
                'submitted_at': report.submitted_at.isoformat() + 'Z',
                'suspicion_score': report.suspicion_score,
                'requires_review': report.requires_review
            }
            
            reports_data.append(report_data)
        
        response_data = {
            'flagged_reports': reports_data,
            'total_flagged': len(reports_data),
            'filter': {
                'min_score': min_score or 10
            }
        }
        
        return success_response(
            data=response_data,
            message=f"Found {len(reports_data)} flagged reports"
        )
        
    except Exception as e:
        print(f"❌ Error getting flagged reports: {e}")
        return internal_error_response(
            message="Failed to retrieve flagged reports",
            details={'error': str(e)}
        )


@router.get("/audit/verify/{report_id}")
async def verify_report_audit(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Verify individual report integrity (Report-Level Verification)
    
    Checks:
    - Report data hasn't been tampered with
    - Stored hash matches recomputed hash
    
    Returns:
        Verification result with hash comparison
    """
    try:
        audit_service = AuditTrail(db)
        verification = audit_service.verify_report(report_id)
        
        if verification['valid']:
            message = "Report integrity verified - no tampering detected"
        else:
            message = "Report integrity check failed - possible tampering"
        
        return success_response(
            data=verification,
            message=message
        )
        
    except Exception as e:
        print(f"❌ Error verifying report: {e}")
        return internal_error_response(
            message="Failed to verify report",
            details={'error': str(e)}
        )


@router.get("/audit/verify-chain")
async def verify_audit_chain(db: Session = Depends(get_db)):
    """
    Verify entire audit chain integrity (Full Chain Verification)
    
    Checks:
    - All hash links are valid
    - No entries have been inserted, deleted, or reordered
    - First entry has no previous_hash
    - Each entry's previous_hash matches prior entry's current_hash
    
    Returns:
        Chain verification result with broken links (if any)
    """
    try:
        audit_service = AuditTrail(db)
        verification = audit_service.verify_chain()
        
        if verification['valid']:
            message = f"Audit chain verified - {verification['total_entries']} entries intact"
        else:
            message = f"Audit chain compromised - {len(verification['broken_links'])} broken link(s)"
        
        return success_response(
            data=verification,
            message=message
        )
        
    except Exception as e:
        print(f"❌ Error verifying chain: {e}")
        return internal_error_response(
            message="Failed to verify audit chain",
            details={'error': str(e)}
        )


@router.get("/audit/history/{report_id}")
async def get_report_audit_history(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Get complete audit history for a specific report
    
    Returns:
    - Audit entry details
    - Verification status
    - Chain context (position, etc.)
    """
    try:
        audit_service = AuditTrail(db)
        history = audit_service.get_audit_history(report_id)
        
        if history['audit_entry']:
            message = "Audit history retrieved"
        else:
            message = "No audit history found for this report"
        
        return success_response(
            data=history,
            message=message
        )
        
    except Exception as e:
        print(f"❌ Error getting audit history: {e}")
        return internal_error_response(
            message="Failed to retrieve audit history",
            details={'error': str(e)}
        )


@router.get("/audit/statistics")
async def get_audit_statistics(db: Session = Depends(get_db)):
    """
    Get overall audit chain statistics
    
    Returns:
    - Total entries
    - Oldest/newest entries
    - Chain health status
    - Chain integrity score
    """
    try:
        audit_service = AuditTrail(db)
        stats = audit_service.get_chain_statistics()
        
        return success_response(
            data=stats,
            message="Audit statistics retrieved"
        )
        
    except Exception as e:
        print(f"❌ Error getting audit statistics: {e}")
        return internal_error_response(
            message="Failed to retrieve audit statistics",
            details={'error': str(e)}
        )