"""
Task scheduler for ETL operations and data pipeline triggers.
Handles scheduled data synchronization with Azure Synapse.
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.core.config import settings
from app.core.synapse_integration import ETLOrchestrator
from app.services.analytics import AnalyticsService
from app.db.database import get_db

logger = logging.getLogger(__name__)


class ETLScheduler:
    """Scheduler for ETL operations and data pipeline triggers."""
    
    def __init__(self):
        # Configure scheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1,
            'misfire_grace_time': 300  # 5 minutes
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        self.etl_orchestrator = ETLOrchestrator()
        self.job_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
    async def start(self):
        """Start the scheduler and add default jobs."""
        try:
            self.scheduler.start()
            await self._add_default_jobs()
            logger.info("ETL Scheduler started successfully")
        except Exception as e:
            logger.error(f"Error starting ETL Scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler."""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("ETL Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping ETL Scheduler: {e}")
    
    async def _add_default_jobs(self):
        """Add default scheduled jobs."""
        try:
            # Daily full ETL at 2 AM UTC
            self.scheduler.add_job(
                func=self._run_daily_full_etl,
                trigger=CronTrigger(hour=2, minute=0),
                id='daily_full_etl',
                name='Daily Full ETL',
                replace_existing=True
            )
            
            # Hourly incremental ETL for appointments
            self.scheduler.add_job(
                func=self._run_hourly_appointments_etl,
                trigger=CronTrigger(minute=0),
                id='hourly_appointments_etl',
                name='Hourly Appointments ETL',
                replace_existing=True
            )
            
            # Every 4 hours resource utilization ETL
            self.scheduler.add_job(
                func=self._run_resource_utilization_etl,
                trigger=IntervalTrigger(hours=4),
                id='resource_utilization_etl',
                name='Resource Utilization ETL',
                replace_existing=True
            )
            
            # Weekly doctor performance ETL on Sundays at 3 AM
            self.scheduler.add_job(
                func=self._run_weekly_doctor_performance_etl,
                trigger=CronTrigger(day_of_week=6, hour=3, minute=0),  # Sunday
                id='weekly_doctor_performance_etl',
                name='Weekly Doctor Performance ETL',
                replace_existing=True
            )
            
            # Cleanup old job history daily at 1 AM
            self.scheduler.add_job(
                func=self._cleanup_job_history,
                trigger=CronTrigger(hour=1, minute=0),
                id='cleanup_job_history',
                name='Cleanup Job History',
                replace_existing=True
            )
            
            logger.info("Default ETL jobs added to scheduler")
            
        except Exception as e:
            logger.error(f"Error adding default jobs: {e}")
            raise
    
    async def _run_daily_full_etl(self):
        """Run daily full ETL for all data types."""
        job_id = f"daily_full_etl_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info("Starting daily full ETL")
            
            # Get date range (yesterday's data)
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=1)
            
            # Get database session
            async with self._get_db_session() as db:
                analytics_service = AnalyticsService(db)
                
                # Run full ETL
                result = await self.etl_orchestrator.run_full_etl(
                    analytics_service=analytics_service,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Log result
                self._add_job_to_history({
                    "job_id": job_id,
                    "job_type": "daily_full_etl",
                    "start_time": result.get("start_time"),
                    "end_time": result.get("end_time"),
                    "status": result.get("status"),
                    "data_exports": result.get("data_exports", {}),
                    "pipeline_runs": result.get("pipeline_runs", {}),
                    "error": result.get("error")
                })
                
                logger.info(f"Daily full ETL completed with status: {result.get('status')}")
                
        except Exception as e:
            logger.error(f"Error in daily full ETL: {e}")
            self._add_job_to_history({
                "job_id": job_id,
                "job_type": "daily_full_etl",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": str(e)
            })
    
    async def _run_hourly_appointments_etl(self):
        """Run hourly incremental ETL for appointments."""
        job_id = f"hourly_appointments_etl_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info("Starting hourly appointments ETL")
            
            # Get date range (last hour)
            end_date = date.today()
            start_date = end_date  # Same day for hourly updates
            
            # Get database session
            async with self._get_db_session() as db:
                analytics_service = AnalyticsService(db)
                
                # Run incremental ETL for appointments
                result = await self.etl_orchestrator.run_incremental_etl(
                    analytics_service=analytics_service,
                    data_type="appointments",
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Log result
                self._add_job_to_history({
                    "job_id": job_id,
                    "job_type": "hourly_appointments_etl",
                    "start_time": result.get("start_time"),
                    "end_time": result.get("end_time"),
                    "status": result.get("status"),
                    "data_exports": result.get("data_exports", {}),
                    "pipeline_run": result.get("pipeline_run", {}),
                    "error": result.get("error")
                })
                
                logger.info(f"Hourly appointments ETL completed with status: {result.get('status')}")
                
        except Exception as e:
            logger.error(f"Error in hourly appointments ETL: {e}")
            self._add_job_to_history({
                "job_id": job_id,
                "job_type": "hourly_appointments_etl",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": str(e)
            })
    
    async def _run_resource_utilization_etl(self):
        """Run resource utilization ETL every 4 hours."""
        job_id = f"resource_utilization_etl_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info("Starting resource utilization ETL")
            
            # Get date range (last 4 hours of data)
            end_date = date.today()
            start_date = end_date  # Same day
            
            # Get database session
            async with self._get_db_session() as db:
                analytics_service = AnalyticsService(db)
                
                # Run incremental ETL for resources
                result = await self.etl_orchestrator.run_incremental_etl(
                    analytics_service=analytics_service,
                    data_type="resources",
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Log result
                self._add_job_to_history({
                    "job_id": job_id,
                    "job_type": "resource_utilization_etl",
                    "start_time": result.get("start_time"),
                    "end_time": result.get("end_time"),
                    "status": result.get("status"),
                    "data_exports": result.get("data_exports", {}),
                    "pipeline_run": result.get("pipeline_run", {}),
                    "error": result.get("error")
                })
                
                logger.info(f"Resource utilization ETL completed with status: {result.get('status')}")
                
        except Exception as e:
            logger.error(f"Error in resource utilization ETL: {e}")
            self._add_job_to_history({
                "job_id": job_id,
                "job_type": "resource_utilization_etl",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": str(e)
            })
    
    async def _run_weekly_doctor_performance_etl(self):
        """Run weekly doctor performance ETL."""
        job_id = f"weekly_doctor_performance_etl_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info("Starting weekly doctor performance ETL")
            
            # Get date range (last week)
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=7)
            
            # Get database session
            async with self._get_db_session() as db:
                analytics_service = AnalyticsService(db)
                
                # Run incremental ETL for doctors
                result = await self.etl_orchestrator.run_incremental_etl(
                    analytics_service=analytics_service,
                    data_type="doctors",
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Log result
                self._add_job_to_history({
                    "job_id": job_id,
                    "job_type": "weekly_doctor_performance_etl",
                    "start_time": result.get("start_time"),
                    "end_time": result.get("end_time"),
                    "status": result.get("status"),
                    "data_exports": result.get("data_exports", {}),
                    "pipeline_run": result.get("pipeline_run", {}),
                    "error": result.get("error")
                })
                
                logger.info(f"Weekly doctor performance ETL completed with status: {result.get('status')}")
                
        except Exception as e:
            logger.error(f"Error in weekly doctor performance ETL: {e}")
            self._add_job_to_history({
                "job_id": job_id,
                "job_type": "weekly_doctor_performance_etl",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": str(e)
            })
    
    async def _cleanup_job_history(self):
        """Clean up old job history entries."""
        try:
            if len(self.job_history) > self.max_history_size:
                # Keep only the most recent entries
                self.job_history = self.job_history[-self.max_history_size:]
                logger.info(f"Cleaned up job history, kept {len(self.job_history)} entries")
        except Exception as e:
            logger.error(f"Error cleaning up job history: {e}")
    
    def _add_job_to_history(self, job_info: Dict[str, Any]):
        """Add job information to history."""
        job_info["timestamp"] = datetime.utcnow().isoformat()
        self.job_history.append(job_info)
        
        # Keep history size manageable
        if len(self.job_history) > self.max_history_size * 1.2:
            self.job_history = self.job_history[-self.max_history_size:]
    
    @asynccontextmanager
    async def _get_db_session(self):
        """Get database session for ETL operations."""
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()
    
    # Manual job trigger methods
    
    async def trigger_manual_etl(
        self, 
        data_type: str, 
        start_date: date, 
        end_date: date,
        job_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Manually trigger ETL for specific data type and date range."""
        job_id = f"manual_etl_{data_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info(f"Starting manual ETL for {data_type}")
            
            # Get database session
            async with self._get_db_session() as db:
                analytics_service = AnalyticsService(db)
                
                if data_type == "all":
                    # Run full ETL
                    result = await self.etl_orchestrator.run_full_etl(
                        analytics_service=analytics_service,
                        start_date=start_date,
                        end_date=end_date
                    )
                else:
                    # Run incremental ETL for specific data type
                    result = await self.etl_orchestrator.run_incremental_etl(
                        analytics_service=analytics_service,
                        data_type=data_type,
                        start_date=start_date,
                        end_date=end_date
                    )
                
                # Log result
                job_info = {
                    "job_id": job_id,
                    "job_type": f"manual_etl_{data_type}",
                    "job_name": job_name or f"Manual ETL - {data_type}",
                    "start_time": result.get("start_time"),
                    "end_time": result.get("end_time"),
                    "status": result.get("status"),
                    "data_exports": result.get("data_exports", {}),
                    "error": result.get("error")
                }
                
                if data_type == "all":
                    job_info["pipeline_runs"] = result.get("pipeline_runs", {})
                else:
                    job_info["pipeline_run"] = result.get("pipeline_run", {})
                
                self._add_job_to_history(job_info)
                
                logger.info(f"Manual ETL for {data_type} completed with status: {result.get('status')}")
                return result
                
        except Exception as e:
            logger.error(f"Error in manual ETL for {data_type}: {e}")
            error_result = {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat()
            }
            
            self._add_job_to_history({
                **error_result,
                "job_type": f"manual_etl_{data_type}",
                "job_name": job_name or f"Manual ETL - {data_type}"
            })
            
            return error_result
    
    def get_job_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get job execution history."""
        if limit:
            return self.job_history[-limit:]
        return self.job_history.copy()
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get list of scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "func": job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
            })
        return jobs
    
    async def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job {job_id} paused")
            return True
        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {e}")
            return False
    
    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job {job_id} resumed")
            return True
        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {e}")
            return False
    
    async def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job {job_id} removed")
            return True
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
            return False


# Global scheduler instance
etl_scheduler = ETLScheduler()