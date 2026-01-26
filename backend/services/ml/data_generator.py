"""
Synthetic Data Generator for BioHIVE Testing
Generates realistic disease surveillance data for model training and testing

Features:
- Seasonal patterns (winter peaks)
- Weekly cycles (weekend dips)
- Outbreak simulations
- Correlated symptoms (fever + cough)
- Noise and variability
"""

import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
import math

from sqlalchemy.orm import Session
from backend.schemas import AggregatedSignal


class SyntheticDataGenerator:
    """
    Generates synthetic disease surveillance data with realistic patterns.
    
    Data characteristics:
    - Base levels: fever=50, cough=40, gi=30 cases/day
    - Seasonal variation: ±30% (higher in winter)
    - Weekly pattern: 30% lower on weekends
    - Outbreaks: 5% chance per day, lasting 7 days
    - Correlation: cough correlates with fever (0.3 coefficient)
    """
    
    def __init__(self, db: Session):
        """
        Initialize generator with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        
        # Base symptom levels (daily counts across all nodes)
        self.base_fever = 50
        self.base_cough = 40
        self.base_gi = 30
        
        # Seasonality parameters
        self.seasonal_amplitude = 0.3  # 30% variation
        
        # Noise parameters
        self.noise_level = 0.15  # 15% random variation
        
        # Outbreak parameters
        self.outbreak_probability = 0.05  # 5% chance per day
        self.outbreak_duration = 7  # 7 days
        
    def generate_historical_data(
        self,
        days: int = 90,
        start_date: Optional[date] = None,
        participating_nodes: int = 8,
        seed: Optional[int] = None
    ) -> List[AggregatedSignal]:
        """
        Generate historical aggregated signal data.
        
        Args:
            days: Number of days to generate (default: 90)
            start_date: Starting date (default: 90 days before today)
            participating_nodes: Number of clinics reporting (default: 8)
            seed: Random seed for reproducibility (default: None)
        
        Returns:
            List of AggregatedSignal objects ready to be added to database
        """
        if seed is not None:
            random.seed(seed)
        
        if start_date is None:
            start_date = date.today() - timedelta(days=days)
        
        generated_data = []
        outbreak_end = None
        outbreak_multiplier = 1.0
        
        print(f"📅 Generating data from {start_date} for {days} days...")
        
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            
            # Progress indicator
            if (day_offset + 1) % 30 == 0:
                print(f"   Generated {day_offset + 1}/{days} days...")
            
            # Calculate day of year for seasonality (0-365)
            day_of_year = current_date.timetuple().tm_yday
            
            # Seasonal factor (higher in winter: Dec-Feb in Northern Hemisphere)
            # Peak around day 15 (mid-January) and day 350 (mid-December)
            # Using cosine wave: peaks at Jan 15, troughs at Jul 15
            seasonal_factor = 1.0 + self.seasonal_amplitude * math.cos(
                2 * math.pi * (day_of_year - 15) / 365
            )
            
            # Weekly pattern (lower on weekends)
            day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
            weekly_factor = 0.7 if day_of_week >= 5 else 1.0
            
            # Check for outbreak
            if outbreak_end and current_date <= outbreak_end:
                # Continue existing outbreak (exponential decay)
                days_into_outbreak = (outbreak_end - current_date).days
                outbreak_multiplier = 1.5 + (days_into_outbreak / self.outbreak_duration) * 0.5
            elif random.random() < self.outbreak_probability:
                # Start new outbreak
                outbreak_end = current_date + timedelta(days=self.outbreak_duration)
                outbreak_multiplier = 2.0
                print(f"   🦠 Outbreak started on {current_date}")
            else:
                outbreak_multiplier = 1.0
            
            # Generate symptom counts
            fever = self._generate_symptom_count(
                base=self.base_fever,
                seasonal=seasonal_factor,
                weekly=weekly_factor,
                outbreak=outbreak_multiplier
            )
            
            # Cough correlates with fever
            cough = self._generate_symptom_count(
                base=self.base_cough,
                seasonal=seasonal_factor,
                weekly=weekly_factor,
                outbreak=outbreak_multiplier,
                correlation_with_fever=fever
            )
            
            # GI symptoms less seasonal and less affected by respiratory outbreaks
            gi = self._generate_symptom_count(
                base=self.base_gi,
                seasonal=seasonal_factor * 0.8,  # Less seasonal
                weekly=weekly_factor,
                outbreak=outbreak_multiplier * 0.7  # Less affected by outbreak
            )
            
            # Calculate risk score and level
            risk_score, risk_level, anomaly_detected = self._calculate_risk(
                fever, cough, gi, outbreak_multiplier
            )
            
            # Create aggregated signal entry
            signal = AggregatedSignal(
                date=current_date,
                total_fever=fever,
                total_cough=cough,
                total_gi=gi,
                participating_nodes=participating_nodes,
                risk_score=risk_score,
                risk_level=risk_level,
                anomaly_detected=anomaly_detected,
                computed_at=datetime.utcnow()
            )
            
            generated_data.append(signal)
        
        print(f"✅ Generated {len(generated_data)} data points")
        return generated_data
    
    def _generate_symptom_count(
        self,
        base: int,
        seasonal: float,
        weekly: float,
        outbreak: float,
        correlation_with_fever: Optional[int] = None
    ) -> int:
        """
        Generate a single symptom count with various factors.
        
        Args:
            base: Base symptom count
            seasonal: Seasonal multiplier (0.7 - 1.3)
            weekly: Weekly multiplier (0.7 or 1.0)
            outbreak: Outbreak multiplier (1.0 - 2.0)
            correlation_with_fever: If provided, correlate with fever count
        
        Returns:
            Integer symptom count (non-negative)
        """
        # Start with base count
        count = base
        
        # Apply seasonal and weekly patterns
        count *= seasonal * weekly * outbreak
        
        # Add random noise (Gaussian)
        noise = random.gauss(0, self.noise_level)
        count *= (1 + noise)
        
        # If correlating with fever, add some of fever's signal
        if correlation_with_fever is not None:
            fever_influence = 0.3  # 30% correlation coefficient
            fever_component = (correlation_with_fever / self.base_fever - 1) * base
            count += fever_component * fever_influence
        
        # Ensure non-negative and return as integer
        return max(0, int(round(count)))
    
    def _calculate_risk(
        self,
        fever: int,
        cough: int,
        gi: int,
        outbreak_multiplier: float
    ) -> tuple:
        """
        Calculate risk score, risk level, and anomaly detection.
        
        Risk scoring:
        - Baseline: fever=50, cough=40, gi=30 (total=120)
        - Score = (actual/baseline) * 50, capped at 100
        - LOW: <40, MODERATE: 40-70, HIGH: >70
        
        Args:
            fever: Fever count
            cough: Cough count
            gi: GI symptom count
            outbreak_multiplier: Current outbreak multiplier
        
        Returns:
            Tuple of (risk_score: float, risk_level: str, anomaly_detected: bool)
        """
        # Total symptom load
        total_symptoms = fever + cough + gi
        
        # Expected baseline
        expected_baseline = self.base_fever + self.base_cough + self.base_gi
        
        # Normalize to 0-100 scale
        risk_score = min(100.0, (total_symptoms / expected_baseline) * 50)
        
        # Determine risk level
        if risk_score < 40:
            risk_level = "LOW"
        elif risk_score < 70:
            risk_level = "MODERATE"
        else:
            risk_level = "HIGH"
        
        # Anomaly detection (if outbreak active or extreme values)
        anomaly_detected = (
            outbreak_multiplier > 1.3 or 
            risk_score > 80
        )
        
        return round(risk_score, 2), risk_level, anomaly_detected
    
    def save_to_database(self, signals: List[AggregatedSignal]) -> int:
        """
        Save generated signals to database.
        
        Checks for duplicates and only saves new records.
        
        Args:
            signals: List of AggregatedSignal objects
        
        Returns:
            Number of records saved
        
        Raises:
            Exception: If database operation fails
        """
        try:
            # Check for existing data and avoid duplicates
            existing_dates = set(
                row[0] for row in self.db.query(AggregatedSignal.date).all()
            )
            
            new_signals = [s for s in signals if s.date not in existing_dates]
            
            if not new_signals:
                print("⚠️  All dates already exist in database. No new data added.")
                return 0
            
            if len(new_signals) < len(signals):
                skipped = len(signals) - len(new_signals)
                print(f"⚠️  Skipped {skipped} duplicate records")
            
            # Add and commit new signals
            self.db.add_all(new_signals)
            self.db.commit()
            
            print(f"✅ Successfully saved {len(new_signals)} records to database")
            return len(new_signals)
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error saving to database: {str(e)}")
            raise
    
    def generate_and_save(
        self,
        days: int = 90,
        participating_nodes: int = 8,
        seed: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Convenience method: Generate and save data in one call.
        
        Args:
            days: Number of days to generate
            participating_nodes: Number of reporting clinics
            seed: Random seed for reproducibility
        
        Returns:
            Dictionary with generation statistics
        """
        print(f"\n🔬 Generating {days} days of synthetic surveillance data...")
        print(f"   Participating nodes: {participating_nodes}")
        if seed:
            print(f"   Random seed: {seed} (reproducible)")
        
        # Generate signals
        signals = self.generate_historical_data(
            days=days,
            participating_nodes=participating_nodes,
            seed=seed
        )
        
        print(f"\n📊 Data Summary:")
        print(f"   Date range: {signals[0].date} to {signals[-1].date}")
        
        # Calculate statistics
        total_fever = sum(s.total_fever for s in signals)
        total_cough = sum(s.total_cough for s in signals)
        total_gi = sum(s.total_gi for s in signals)
        
        avg_fever = total_fever // len(signals)
        avg_cough = total_cough // len(signals)
        avg_gi = total_gi // len(signals)
        
        high_risk_days = sum(1 for s in signals if s.risk_level == "HIGH")
        moderate_risk_days = sum(1 for s in signals if s.risk_level == "MODERATE")
        low_risk_days = sum(1 for s in signals if s.risk_level == "LOW")
        anomalies = sum(1 for s in signals if s.anomaly_detected)
        
        print(f"\n📈 Statistics:")
        print(f"   Total cases - Fever: {total_fever}, Cough: {total_cough}, GI: {total_gi}")
        print(f"   Daily average - Fever: {avg_fever}, Cough: {avg_cough}, GI: {avg_gi}")
        print(f"   Risk levels - LOW: {low_risk_days}, MODERATE: {moderate_risk_days}, HIGH: {high_risk_days}")
        print(f"   Anomalies detected: {anomalies}")
        
        # Save to database
        print(f"\n💾 Saving to database...")
        saved_count = self.save_to_database(signals)
        
        return {
            "days_generated": len(signals),
            "days_saved": saved_count,
            "date_range": {
                "start": signals[0].date.isoformat(),
                "end": signals[-1].date.isoformat()
            },
            "statistics": {
                "total_fever": total_fever,
                "total_cough": total_cough,
                "total_gi": total_gi,
                "daily_average": {
                    "fever": avg_fever,
                    "cough": avg_cough,
                    "gi": avg_gi
                },
                "risk_distribution": {
                    "low": low_risk_days,
                    "moderate": moderate_risk_days,
                    "high": high_risk_days
                },
                "anomalies": anomalies
            }
        }