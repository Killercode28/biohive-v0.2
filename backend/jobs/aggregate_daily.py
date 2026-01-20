# backend/jobs/aggregate_daily.py
"""
Daily Aggregation Job for BioHIVE Disease Surveillance System

Standalone script to aggregate daily symptom reports into system-wide metrics.
Can be run manually or scheduled via cron for automated daily aggregation.

Usage:
    python aggregate_daily.py                    # Aggregate today
    python aggregate_daily.py --date 2026-01-18  # Aggregate specific date
    python aggregate_daily.py --start 2026-01-10 --end 2026-01-18  # Date range
    python aggregate_daily.py --yesterday        # Aggregate yesterday
"""

import sys
import argparse
from datetime import date, datetime, timedelta
from typing import Optional
import logging

# Add parent directory to path for imports
sys.path.append('.')

from backend.store import SessionLocal
from backend.services.aggregation import AggregationService
from backend.store import SessionLocal


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class AggregationRunner:
    """
    Runner class for executing daily aggregation jobs.
    
    Handles database session management, error handling, and progress logging.
    """
    
    def __init__(self):
        """Initialize aggregation runner."""
        self.db = None
        self.service = None
    
    def setup(self):
        """
        Set up database session and service.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            self.db = SessionLocal()
            self.service = AggregationService(self.db)
            logger.info("Database connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to setup database connection: {e}")
            return False
    
    def teardown(self):
        """Clean up database session."""
        if self.db:
            try:
                self.db.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")
    
    def aggregate_single_date(self, target_date: date) -> bool:
        """
        Aggregate data for a single date.
        
        Args:
            target_date: Date to aggregate
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Aggregating data for {target_date}...")
            
            result = self.service.aggregate_date(target_date)
            
            logger.info(f"✓ Aggregation complete for {target_date}")
            logger.info(f"  Total Fever: {result['total_fever']}")
            logger.info(f"  Total Cough: {result['total_cough']}")
            logger.info(f"  Total GI: {result['total_gi']}")
            logger.info(f"  Participating Nodes: {result['participating_nodes']}")
            logger.info(f"  Risk Score: {result['risk_score']:.2f}")
            logger.info(f"  Risk Level: {result['risk_level']}")
            
            return True
            
        except ValueError as e:
            logger.error(f"✗ Validation error for {target_date}: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Failed to aggregate {target_date}: {e}")
            return False
    
    def aggregate_date_range(self, start_date: date, end_date: date) -> tuple[int, int]:
        """
        Aggregate data for a range of dates.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            tuple: (successful_count, failed_count)
        """
        if start_date > end_date:
            logger.error(f"Invalid date range: {start_date} to {end_date}")
            return 0, 0
        
        logger.info(f"Aggregating date range: {start_date} to {end_date}")
        
        successful = 0
        failed = 0
        current_date = start_date
        
        while current_date <= end_date:
            if self.aggregate_single_date(current_date):
                successful += 1
            else:
                failed += 1
            
            current_date += timedelta(days=1)
        
        logger.info(f"\nRange aggregation complete:")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Total: {successful + failed}")
        
        return successful, failed


def parse_date(date_string: str) -> date:
    """
    Parse date string in YYYY-MM-DD format.
    
    Args:
        date_string: Date string to parse
    
    Returns:
        date: Parsed date object
    
    Raises:
        ValueError: If date string is invalid
    """
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format '{date_string}'. Use YYYY-MM-DD format.")


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Aggregate daily symptom reports for BioHIVE surveillance system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python aggregate_daily.py                          # Aggregate today
  python aggregate_daily.py --yesterday              # Aggregate yesterday
  python aggregate_daily.py --date 2026-01-18        # Specific date
  python aggregate_daily.py --start 2026-01-10 --end 2026-01-18  # Date range
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    
    group.add_argument(
        '--date',
        type=str,
        metavar='YYYY-MM-DD',
        help='Aggregate specific date (format: YYYY-MM-DD)'
    )
    
    group.add_argument(
        '--yesterday',
        action='store_true',
        help='Aggregate yesterday\'s data'
    )
    
    parser.add_argument(
        '--start',
        type=str,
        metavar='YYYY-MM-DD',
        help='Start date for range aggregation (requires --end)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        metavar='YYYY-MM-DD',
        help='End date for range aggregation (requires --start)'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='Suppress non-error output'
    )
    
    return parser.parse_args()


def main():
    """
    Main entry point for aggregation job.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    args = parse_arguments()
    
    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.ERROR)
    
    # Initialize runner
    runner = AggregationRunner()
    
    if not runner.setup():
        logger.error("Failed to initialize aggregation runner")
        return 1
    
    try:
        # Determine what to aggregate
        if args.start and args.end:
            # Date range mode
            try:
                start_date = parse_date(args.start)
                end_date = parse_date(args.end)
            except ValueError as e:
                logger.error(str(e))
                return 1
            
            successful, failed = runner.aggregate_date_range(start_date, end_date)
            
            # Exit with error if any aggregation failed
            return 0 if failed == 0 else 1
            
        elif args.start or args.end:
            # Invalid: only one of start/end provided
            logger.error("Both --start and --end must be provided for range aggregation")
            return 1
            
        elif args.date:
            # Specific date mode
            try:
                target_date = parse_date(args.date)
            except ValueError as e:
                logger.error(str(e))
                return 1
            
            success = runner.aggregate_single_date(target_date)
            return 0 if success else 1
            
        elif args.yesterday:
            # Yesterday mode
            target_date = date.today() - timedelta(days=1)
            logger.info(f"Aggregating yesterday's data ({target_date})")
            
            success = runner.aggregate_single_date(target_date)
            return 0 if success else 1
            
        else:
            # Default: today
            target_date = date.today()
            logger.info(f"Aggregating today's data ({target_date})")
            
            success = runner.aggregate_single_date(target_date)
            return 0 if success else 1
    
    except KeyboardInterrupt:
        logger.warning("\nAggregation interrupted by user")
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    
    finally:
        runner.teardown()


if __name__ == '__main__':
    sys.exit(main())