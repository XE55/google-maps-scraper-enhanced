"""
Job Management System for Async Scraping Operations

This module provides job queue management, status tracking, and webhook callbacks
for asynchronous scraping operations in n8n workflows.

Features:
- Job creation and status tracking
- Background task execution with asyncio
- Webhook callbacks on completion
- Batch job management
- In-memory job store (can be replaced with Redis/PostgreSQL)
- Progress tracking and ETAs
"""

import uuid
import asyncio
import httpx
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormat(str, Enum):
    """Supported export formats"""
    JSON = "json"
    CSV = "csv"
    EMAILS = "emails"


@dataclass
class Job:
    """Represents an async scraping job"""
    job_id: str
    query: str
    max_places: int
    status: JobStatus = JobStatus.PENDING
    webhook_url: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0  # 0-100
    total_items: int = 0
    processed_items: int = 0
    batch_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "job_id": self.job_id,
            "query": self.query,
            "max_places": self.max_places,
            "status": self.status.value,
            "webhook_url": self.webhook_url,
            "results": self.results,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "batch_id": self.batch_id,
            "estimated_completion": self.get_estimated_completion()
        }
    
    def get_estimated_completion(self) -> Optional[str]:
        """Calculate estimated completion time"""
        if self.status != JobStatus.PROCESSING or not self.started_at:
            return None
        
        if self.processed_items == 0:
            return None
        
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        rate = self.processed_items / elapsed  # items per second
        
        if rate == 0:
            return None
        
        remaining_items = self.total_items - self.processed_items
        remaining_seconds = remaining_items / rate
        eta = datetime.utcnow() + timedelta(seconds=remaining_seconds)
        
        return eta.isoformat()


@dataclass
class Batch:
    """Represents a batch of jobs"""
    batch_id: str
    job_ids: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert batch to dictionary"""
        return {
            "batch_id": self.batch_id,
            "job_ids": self.job_ids,
            "created_at": self.created_at.isoformat(),
            "total_jobs": len(self.job_ids)
        }


class JobManager:
    """Manages async scraping jobs and batches"""
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._batches: Dict[str, Batch] = {}
        self._background_tasks: set = set()
        self._lock = asyncio.Lock()
        
    def generate_job_id(self) -> str:
        """Generate unique job ID"""
        return str(uuid.uuid4())
    
    def generate_batch_id(self) -> str:
        """Generate unique batch ID"""
        return f"batch_{uuid.uuid4()}"
    
    async def create_job(
        self,
        query: str,
        max_places: int,
        webhook_url: Optional[str] = None,
        batch_id: Optional[str] = None
    ) -> Job:
        """Create a new job"""
        async with self._lock:
            job = Job(
                job_id=self.generate_job_id(),
                query=query,
                max_places=max_places,
                webhook_url=webhook_url,
                batch_id=batch_id,
                total_items=max_places
            )
            self._jobs[job.job_id] = job
            logger.info(f"Created job {job.job_id} for query: {query}")
            return job
    
    async def create_batch(self, queries: List[Dict[str, Any]]) -> Batch:
        """Create a batch of jobs"""
        batch_id = self.generate_batch_id()
        job_ids = []
        
        for query_config in queries:
            job = await self.create_job(
                query=query_config["query"],
                max_places=query_config.get("max_places", 20),
                webhook_url=query_config.get("webhook_url"),
                batch_id=batch_id
            )
            job_ids.append(job.job_id)
        
        batch = Batch(batch_id=batch_id, job_ids=job_ids)
        self._batches[batch_id] = batch
        logger.info(f"Created batch {batch_id} with {len(job_ids)} jobs")
        return batch
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self._jobs.get(job_id)
    
    async def get_batch(self, batch_id: str) -> Optional[Batch]:
        """Get batch by ID"""
        return self._batches.get(batch_id)
    
    async def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of all jobs in a batch"""
        batch = await self.get_batch(batch_id)
        if not batch:
            return None
        
        jobs = [await self.get_job(job_id) for job_id in batch.job_ids]
        
        status_counts = defaultdict(int)
        total_progress = 0
        
        for job in jobs:
            if job:
                status_counts[job.status.value] += 1
                total_progress += job.progress
        
        avg_progress = total_progress // len(jobs) if jobs else 0
        
        return {
            "batch_id": batch_id,
            "total_jobs": len(batch.job_ids),
            "pending": status_counts["pending"],
            "processing": status_counts["processing"],
            "completed": status_counts["completed"],
            "failed": status_counts["failed"],
            "cancelled": status_counts["cancelled"],
            "average_progress": avg_progress,
            "jobs": [job.to_dict() for job in jobs if job]
        }
    
    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None
    ):
        """Update job status"""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            
            job.status = status
            
            if status == JobStatus.PROCESSING and not job.started_at:
                job.started_at = datetime.utcnow()
            
            if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                job.completed_at = datetime.utcnow()
                job.progress = 100 if status == JobStatus.COMPLETED else job.progress
            
            if error:
                job.error = error
            
            logger.info(f"Job {job_id} status updated to {status.value}")
    
    async def update_job_progress(self, job_id: str, processed_items: int):
        """Update job progress"""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            
            job.processed_items = processed_items
            job.progress = min(100, int((processed_items / job.total_items) * 100))
            logger.debug(f"Job {job_id} progress: {job.progress}%")
    
    async def set_job_results(self, job_id: str, results: List[Dict[str, Any]]):
        """Set job results"""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            
            job.results = results
            logger.info(f"Job {job_id} results set: {len(results)} places")
    
    async def send_webhook(self, job_id: str):
        """Send webhook callback with job results"""
        job = await self.get_job(job_id)
        if not job or not job.webhook_url:
            return
        
        payload = {
            "job_id": job.job_id,
            "status": job.status.value,
            "query": job.query,
            "results": job.results,
            "error": job.error,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "total_results": len(job.results) if job.results else 0
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    job.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                logger.info(f"Webhook sent successfully for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to send webhook for job {job_id}: {str(e)}")
    
    async def execute_job(self, job_id: str, scraper_func):
        """Execute a scraping job in the background"""
        try:
            await self.update_job_status(job_id, JobStatus.PROCESSING)
            
            job = await self.get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            # Execute the actual scraping
            results = await scraper_func(
                query=job.query,
                max_places=job.max_places,
                progress_callback=lambda processed: asyncio.create_task(
                    self.update_job_progress(job_id, processed)
                )
            )
            
            # Store results
            await self.set_job_results(job_id, results)
            await self.update_job_status(job_id, JobStatus.COMPLETED)
            
            # Send webhook if configured
            if job.webhook_url:
                await self.send_webhook(job_id)
                
        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}")
            await self.update_job_status(job_id, JobStatus.FAILED, error=str(e))
            
            # Send webhook with error
            job = await self.get_job(job_id)
            if job and job.webhook_url:
                await self.send_webhook(job_id)
    
    def submit_job(self, job_id: str, scraper_func):
        """Submit a job for background execution"""
        task = asyncio.create_task(self.execute_job(job_id, scraper_func))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        logger.info(f"Job {job_id} submitted for background execution")
    
    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed jobs"""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        async with self._lock:
            jobs_to_delete = [
                job_id for job_id, job in self._jobs.items()
                if job.completed_at and job.completed_at < cutoff
            ]
            
            for job_id in jobs_to_delete:
                del self._jobs[job_id]
                logger.info(f"Deleted old job {job_id}")
    
    async def export_job_results(
        self,
        job_id: str,
        format: ExportFormat
    ) -> Optional[str]:
        """Export job results in specified format"""
        job = await self.get_job(job_id)
        if not job or not job.results:
            return None
        
        if format == ExportFormat.JSON:
            import json
            return json.dumps(job.results, indent=2)
        
        elif format == ExportFormat.CSV:
            import csv
            import io
            
            output = io.StringIO()
            if not job.results:
                return ""
            
            # Get all unique keys from results
            fieldnames = set()
            for result in job.results:
                fieldnames.update(result.keys())
            fieldnames = sorted(list(fieldnames))
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(job.results)
            
            return output.getvalue()
        
        elif format == ExportFormat.EMAILS:
            # Extract emails only
            emails = []
            for result in job.results:
                if result.get("email"):
                    emails.append(result["email"])
            return "\n".join(emails)
        
        return None


# Global job manager instance
job_manager = JobManager()
