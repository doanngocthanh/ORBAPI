"""
Task Statistics Scheduler
Automatically updates daily statistics at scheduled times
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from service.statistics.TaskStatistics import TaskStatistics, save_daily_statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StatisticsScheduler:
    """Scheduler for automatic statistics updates"""
    
    def __init__(self):
        """Initialize the scheduler"""
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        logger.info("StatisticsScheduler initialized")
    
    def update_daily_statistics(self):
        """Update statistics for today"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"Starting daily statistics update for {today}")
            
            # Get statistics from TaskStatistics
            stats = TaskStatistics.get_statistics()
            
            # Save to database
            save_daily_statistics(today, stats)
            
            logger.info(f"✓ Daily statistics updated successfully for {today}")
            logger.info(f"  - Total tasks: {stats['total_tasks']}")
            logger.info(f"  - Completed: {stats['completed_tasks']}")
            logger.info(f"  - Failed: {stats['failed_tasks']}")
            logger.info(f"  - Cards detected: {stats['total_cards_detected']}")
            
        except Exception as e:
            logger.error(f"Error updating daily statistics: {str(e)}", exc_info=True)
    
    def update_yesterday_statistics(self):
        """Update statistics for yesterday (for end-of-day processing)"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info(f"Starting statistics update for {yesterday}")
            
            # Get statistics from TaskStatistics
            stats = TaskStatistics.get_statistics()
            
            # Save to database
            save_daily_statistics(yesterday, stats)
            
            logger.info(f"✓ Statistics updated successfully for {yesterday}")
            
        except Exception as e:
            logger.error(f"Error updating yesterday's statistics: {str(e)}", exc_info=True)
    
    def start(self):
        """Start the scheduler with configured jobs"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Schedule 1: Update daily statistics at midnight (00:00)
            self.scheduler.add_job(
                self.update_daily_statistics,
                trigger=CronTrigger(hour=0, minute=0),
                id='daily_stats_midnight',
                name='Daily Statistics Update (Midnight)',
                replace_existing=True
            )
            logger.info("✓ Scheduled: Daily statistics update at 00:00 (midnight)")
            
            # Schedule 2: Update statistics every 6 hours
            self.scheduler.add_job(
                self.update_daily_statistics,
                trigger=CronTrigger(hour='*/6'),
                id='daily_stats_6hours',
                name='Daily Statistics Update (Every 6 hours)',
                replace_existing=True
            )
            logger.info("✓ Scheduled: Daily statistics update every 6 hours")
            
            # Schedule 3: Update at end of business day (23:55)
            self.scheduler.add_job(
                self.update_daily_statistics,
                trigger=CronTrigger(hour=23, minute=55),
                id='daily_stats_eod',
                name='Daily Statistics Update (End of Day)',
                replace_existing=True
            )
            logger.info("✓ Scheduled: Daily statistics update at 23:55 (end of day)")
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            # Run initial update
            logger.info("Running initial statistics update...")
            self.update_daily_statistics()
            
            logger.info("✓ Statistics Scheduler started successfully!")
            logger.info(f"  - Next midnight update: {datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)}")
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {str(e)}", exc_info=True)
            raise
    
    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("✓ Statistics Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}", exc_info=True)
    
    def get_jobs(self):
        """Get list of scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
    
    def run_now(self):
        """Manually trigger statistics update now"""
        logger.info("Manual statistics update triggered")
        self.update_daily_statistics()


# Singleton instance
_scheduler_instance = None

def get_scheduler() -> StatisticsScheduler:
    """Get the singleton scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = StatisticsScheduler()
    return _scheduler_instance


if __name__ == "__main__":
    # Test the scheduler
    scheduler = StatisticsScheduler()
    
    print("\n=== Testing Statistics Scheduler ===\n")
    
    # Run manual update
    print("Running manual update...")
    scheduler.update_daily_statistics()
    
    print("\n=== Starting Scheduler ===\n")
    scheduler.start()
    
    print("\n=== Scheduled Jobs ===")
    for job in scheduler.get_jobs():
        print(f"  - {job['name']}")
        print(f"    ID: {job['id']}")
        print(f"    Next run: {job['next_run']}")
        print(f"    Trigger: {job['trigger']}\n")
    
    print("Scheduler is running. Press Ctrl+C to stop...")
    
    try:
        # Keep running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
        print("Done!")
