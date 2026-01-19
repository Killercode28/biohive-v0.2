"""
Audit Trail Service - Tamper-Evident Cryptographic Integrity
Implements SHA-256 hashing with hash chaining for tamper detection

Final Design Characteristics:
- Detects tampering AFTER data is stored (not truth validation)
- Ensures cryptographic integrity via hash chaining
- Provides report-level and full-chain verification
- Append-only, transactional persistence
- Separate from validation/warning system
"""

import hashlib
import json
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from schemas import AuditTrail as AuditTrailModel, DailyReport


class AuditTrail:
    """
    Cryptographic audit trail for tamper detection.
    
    Core Features:
    1. SHA-256 hashing of report data
    2. Deterministic hashing (sorted JSON keys)
    3. Hash chaining (current_hash + previous_hash)
    4. Persistent storage with timestamps
    5. Report-level verification
    6. Full-chain verification
    
    Design Principle:
    - Audit trail detects tampering AFTER storage
    - Validation system detects suspicious input BEFORE acceptance
    - These are separate concerns
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize with database session
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def create_hash(self, report_data: Dict) -> str:
        """
        Create SHA-256 hash of report using deterministic JSON serialization.
        
        Implementation Notes:
        - Uses sorted keys for deterministic output
        - Ensures same data always produces same hash
        - Critical for verification operations
        
        Args:
            report_data: {
                'report_id': str,
                'node_id': str,
                'date': str,
                'symptoms': {'fever': int, 'cough': int, 'gi': int}
            }
        
        Returns:
            64-character hex string (SHA-256 hash)
        """
        # Sort keys for deterministic hashing
        report_string = json.dumps(report_data, sort_keys=True)
        
        # Create SHA-256 hash
        hash_object = hashlib.sha256(report_string.encode('utf-8'))
        return hash_object.hexdigest()
    
    def add_to_chain(self, report_id: str, current_hash: str) -> Dict:
        """
        Add report to audit chain with hash linking.
        
        Implementation:
        - Gets most recent audit entry's current_hash
        - Uses it as this entry's previous_hash
        - Creates cryptographic chain
        - Atomic transaction ensures consistency
        
        Args:
            report_id: UUID of report
            current_hash: Hash of current report
        
        Returns:
            {
                'audit_id': str,
                'current_hash': str,
                'previous_hash': str or None,
                'chain_valid': bool,
                'chain_position': int
            }
        """
        # Get the most recent audit entry to link to
        previous_audit = self.db.query(AuditTrailModel)\
            .order_by(AuditTrailModel.timestamp.desc())\
            .first()
        
        previous_hash = previous_audit.current_hash if previous_audit else None
        
        # Calculate chain position
        chain_position = self.db.query(AuditTrailModel).count() + 1
        
        # Create new audit entry
        audit_entry = AuditTrailModel(
            report_id=report_id,
            current_hash=current_hash,
            previous_hash=previous_hash,
            timestamp=datetime.utcnow()
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return {
            'audit_id': audit_entry.id,
            'current_hash': audit_entry.current_hash,
            'previous_hash': audit_entry.previous_hash,
            'chain_valid': True,  # New entries are valid by definition
            'chain_position': chain_position
        }
    
    def verify_report(self, report_id: str) -> Dict:
        """
        Verify individual report integrity (Report-Level Verification).
        
        Process:
        1. Retrieve stored audit hash
        2. Retrieve stored report data
        3. Recompute hash from report data
        4. Compare stored vs computed hash
        
        Use Case: Verify specific report hasn't been tampered with
        
        Args:
            report_id: UUID of report to verify
        
        Returns:
            {
                'valid': bool,
                'report_id': str,
                'stored_hash': str,
                'computed_hash': str,
                'match': bool,
                'timestamp': str,
                'error': str or None
            }
        """
        # Get the audit entry for this report
        audit_entry = self.db.query(AuditTrailModel)\
            .filter(AuditTrailModel.report_id == report_id)\
            .first()
        
        if not audit_entry:
            return {
                'valid': False,
                'report_id': report_id,
                'stored_hash': None,
                'computed_hash': None,
                'match': False,
                'timestamp': None,
                'error': 'No audit entry found for this report'
            }
        
        # Get the actual report data
        report = self.db.query(DailyReport)\
            .filter(DailyReport.report_id == report_id)\
            .first()
        
        if not report:
            return {
                'valid': False,
                'report_id': report_id,
                'stored_hash': audit_entry.current_hash,
                'computed_hash': None,
                'match': False,
                'timestamp': audit_entry.timestamp.isoformat() + 'Z',
                'error': 'Report not found in database (possible deletion)'
            }
        
        # Recompute hash from current report data
        report_data = {
            'report_id': report.report_id,
            'node_id': report.node_id,
            'date': report.date.isoformat(),
            'symptoms': {
                'fever': report.fever_count,
                'cough': report.cough_count,
                'gi': report.gi_count
            }
        }
        
        computed_hash = self.create_hash(report_data)
        
        # Compare hashes
        is_valid = (audit_entry.current_hash == computed_hash)
        
        return {
            'valid': is_valid,
            'report_id': report_id,
            'stored_hash': audit_entry.current_hash,
            'computed_hash': computed_hash,
            'match': is_valid,
            'timestamp': audit_entry.timestamp.isoformat() + 'Z',
            'error': None if is_valid else 'Hash mismatch - report data has been tampered with'
        }
    
    def verify_chain(self) -> Dict:
        """
        Verify entire audit chain integrity (Full Chain Verification).
        
        Process:
        1. Retrieve all audit entries in chronological order
        2. Verify first entry has no previous_hash
        3. For each subsequent entry, verify previous_hash matches
           the prior entry's current_hash
        4. Detect any broken links or reordered entries
        
        Use Case: Ensure entire audit history hasn't been tampered with
        
        Returns:
            {
                'valid': bool,
                'total_entries': int,
                'verified_entries': int,
                'broken_links': List[Dict],
                'chain_integrity': float (0.0 to 1.0),
                'error': str or None
            }
        """
        all_audits = self.db.query(AuditTrailModel)\
            .order_by(AuditTrailModel.timestamp.asc())\
            .all()
        
        if not all_audits:
            return {
                'valid': True,
                'total_entries': 0,
                'verified_entries': 0,
                'broken_links': [],
                'chain_integrity': 1.0,
                'error': None
            }
        
        broken_links = []
        verified_count = 0
        
        for i, audit in enumerate(all_audits):
            # First entry verification
            if i == 0:
                if audit.previous_hash is None:
                    verified_count += 1
                else:
                    broken_links.append({
                        'position': i,
                        'audit_id': audit.id,
                        'report_id': audit.report_id,
                        'timestamp': audit.timestamp.isoformat() + 'Z',
                        'error': 'First entry should have null previous_hash',
                        'expected_previous': None,
                        'actual_previous': audit.previous_hash
                    })
                continue
            
            # Subsequent entries verification
            previous_audit = all_audits[i - 1]
            
            if audit.previous_hash == previous_audit.current_hash:
                verified_count += 1
            else:
                broken_links.append({
                    'position': i,
                    'audit_id': audit.id,
                    'report_id': audit.report_id,
                    'timestamp': audit.timestamp.isoformat() + 'Z',
                    'error': 'Chain link broken - previous_hash mismatch',
                    'expected_previous': previous_audit.current_hash,
                    'actual_previous': audit.previous_hash,
                    'gap': 'possible insertion or deletion'
                })
        
        is_valid = len(broken_links) == 0
        chain_integrity = verified_count / len(all_audits) if all_audits else 1.0
        
        return {
            'valid': is_valid,
            'total_entries': len(all_audits),
            'verified_entries': verified_count,
            'broken_links': broken_links,
            'chain_integrity': round(chain_integrity, 4),
            'error': None if is_valid else f'Chain compromised: {len(broken_links)} broken link(s) detected'
        }
    
    def get_audit_history(self, report_id: str) -> Dict:
        """
        Get complete audit history for a report.
        
        Returns:
            {
                'report_id': str,
                'audit_entry': Dict,
                'verification': Dict,
                'chain_context': Dict
            }
        """
        audit_entry = self.db.query(AuditTrailModel)\
            .filter(AuditTrailModel.report_id == report_id)\
            .first()
        
        if not audit_entry:
            return {
                'report_id': report_id,
                'audit_entry': None,
                'verification': {'valid': False, 'error': 'No audit entry found'},
                'chain_context': None
            }
        
        # Get verification status
        verification = self.verify_report(report_id)
        
        # Get chain context (position in chain)
        total_entries = self.db.query(AuditTrailModel).count()
        entries_before = self.db.query(AuditTrailModel)\
            .filter(AuditTrailModel.timestamp < audit_entry.timestamp)\
            .count()
        
        return {
            'report_id': report_id,
            'audit_entry': {
                'id': audit_entry.id,
                'current_hash': audit_entry.current_hash,
                'previous_hash': audit_entry.previous_hash,
                'timestamp': audit_entry.timestamp.isoformat() + 'Z',
                'chain_position': entries_before + 1
            },
            'verification': verification,
            'chain_context': {
                'total_chain_length': total_entries,
                'position_in_chain': entries_before + 1,
                'entries_after': total_entries - entries_before - 1
            }
        }
    
    def get_chain_statistics(self) -> Dict:
        """
        Get overall audit chain statistics.
        
        Returns:
            {
                'total_entries': int,
                'oldest_entry': str,
                'newest_entry': str,
                'chain_health': str,
                'last_verification': str or None
            }
        """
        total = self.db.query(AuditTrailModel).count()
        
        if total == 0:
            return {
                'total_entries': 0,
                'oldest_entry': None,
                'newest_entry': None,
                'chain_health': 'EMPTY',
                'last_verification': None
            }
        
        oldest = self.db.query(AuditTrailModel)\
            .order_by(AuditTrailModel.timestamp.asc())\
            .first()
        
        newest = self.db.query(AuditTrailModel)\
            .order_by(AuditTrailModel.timestamp.desc())\
            .first()
        
        # Quick chain health check
        chain_verification = self.verify_chain()
        
        health_status = 'HEALTHY' if chain_verification['valid'] else 'COMPROMISED'
        
        return {
            'total_entries': total,
            'oldest_entry': oldest.timestamp.isoformat() + 'Z' if oldest else None,
            'newest_entry': newest.timestamp.isoformat() + 'Z' if newest else None,
            'chain_health': health_status,
            'chain_integrity': chain_verification['chain_integrity'],
            'last_verification': datetime.utcnow().isoformat() + 'Z'
        }