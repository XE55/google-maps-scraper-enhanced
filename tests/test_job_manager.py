"""
Comprehensive tests for Job Manager

Tests job creation, status tracking, webhook callbacks, batch processing,
exports, error handling, and edge cases.

Coverage target: 95%+
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from gmaps_scraper_server.job_manager import (
    JobManager,
    Job,
    Batch,
    JobStatus,
    ExportFormat,
    job_manager
)


@pytest.fixture
def manager():
    """Create fresh job manager for each test"""
    return JobManager()


@pytest.fixture
def sample_results():
    """Sample scraping results"""
    return [
        {
            "name": "Test Restaurant",
            "address": "123 Main St",
            "phone": "+15551234567",
            "email": "test@restaurant.com",
            "website": "https://test-restaurant.com",
            "rating": 4.5,
            "reviews_count": 100
        },
        {
            "name": "Another Place",
            "address": "456 Oak Ave",
            "phone": "+15559876543",
            "email": "info@anotherplace.com",
            "rating": 4.0,
            "reviews_count": 50
        }
    ]


class TestJobCreation:
    """Test job creation and ID generation"""
    
    @pytest.mark.asyncio
    async def test_create_job_basic(self, manager):
        """Test basic job creation"""
        job = await manager.create_job("restaurants in NYC", 20)
        
        assert job is not None
        assert job.job_id
        assert job.query == "restaurants in NYC"
        assert job.max_places == 20
        assert job.status == JobStatus.PENDING
        assert job.webhook_url is None
        assert job.batch_id is None
        assert job.progress == 0
        assert job.total_items == 20
        assert job.processed_items == 0
    
    @pytest.mark.asyncio
    async def test_create_job_with_webhook(self, manager):
        """Test job creation with webhook URL"""
        webhook_url = "https://webhook.site/test"
        job = await manager.create_job("hotels in Paris", 10, webhook_url=webhook_url)
        
        assert job.webhook_url == webhook_url
    
    @pytest.mark.asyncio
    async def test_create_job_with_batch_id(self, manager):
        """Test job creation with batch ID"""
        batch_id = "batch_123"
        job = await manager.create_job("cafes in London", 15, batch_id=batch_id)
        
        assert job.batch_id == batch_id
    
    @pytest.mark.asyncio
    async def test_generate_unique_job_ids(self, manager):
        """Test that job IDs are unique"""
        job1 = await manager.create_job("query1", 10)
        job2 = await manager.create_job("query2", 10)
        
        assert job1.job_id != job2.job_id
    
    @pytest.mark.asyncio
    async def test_job_stored_in_manager(self, manager):
        """Test that created job is stored in manager"""
        job = await manager.create_job("test query", 5)
        
        retrieved_job = await manager.get_job(job.job_id)
        assert retrieved_job is not None
        assert retrieved_job.job_id == job.job_id
        assert retrieved_job.query == job.query


class TestJobStatusUpdates:
    """Test job status management"""
    
    @pytest.mark.asyncio
    async def test_update_to_processing(self, manager):
        """Test updating job to processing status"""
        job = await manager.create_job("test", 10)
        
        await manager.update_job_status(job.job_id, JobStatus.PROCESSING)
        
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.PROCESSING
        assert updated_job.started_at is not None
    
    @pytest.mark.asyncio
    async def test_update_to_completed(self, manager):
        """Test updating job to completed status"""
        job = await manager.create_job("test", 10)
        
        await manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.completed_at is not None
        assert updated_job.progress == 100
    
    @pytest.mark.asyncio
    async def test_update_to_failed_with_error(self, manager):
        """Test updating job to failed status with error message"""
        job = await manager.create_job("test", 10)
        error_msg = "Network timeout"
        
        await manager.update_job_status(job.job_id, JobStatus.FAILED, error=error_msg)
        
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.FAILED
        assert updated_job.error == error_msg
        assert updated_job.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_job(self, manager):
        """Test updating job that doesn't exist"""
        # Should not raise error, just do nothing
        await manager.update_job_status("nonexistent_id", JobStatus.COMPLETED)


class TestJobProgress:
    """Test job progress tracking"""
    
    @pytest.mark.asyncio
    async def test_update_progress(self, manager):
        """Test updating job progress"""
        job = await manager.create_job("test", 100)
        
        await manager.update_job_progress(job.job_id, 50)
        
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.processed_items == 50
        assert updated_job.progress == 50
    
    @pytest.mark.asyncio
    async def test_progress_calculation(self, manager):
        """Test progress percentage calculation"""
        job = await manager.create_job("test", 100)
        
        await manager.update_job_progress(job.job_id, 25)
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.progress == 25
        
        await manager.update_job_progress(job.job_id, 75)
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.progress == 75
    
    @pytest.mark.asyncio
    async def test_progress_caps_at_100(self, manager):
        """Test that progress doesn't exceed 100%"""
        job = await manager.create_job("test", 10)
        
        await manager.update_job_progress(job.job_id, 15)  # More than total
        
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.progress <= 100


class TestJobResults:
    """Test job results storage"""
    
    @pytest.mark.asyncio
    async def test_set_results(self, manager, sample_results):
        """Test setting job results"""
        job = await manager.create_job("test", 10)
        
        await manager.set_job_results(job.job_id, sample_results)
        
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.results == sample_results
        assert len(updated_job.results) == 2
    
    @pytest.mark.asyncio
    async def test_set_empty_results(self, manager):
        """Test setting empty results"""
        job = await manager.create_job("test", 10)
        
        await manager.set_job_results(job.job_id, [])
        
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.results == []


class TestBatchManagement:
    """Test batch job management"""
    
    @pytest.mark.asyncio
    async def test_create_batch(self, manager):
        """Test batch creation"""
        queries = [
            {"query": "restaurants in NYC", "max_places": 20},
            {"query": "hotels in Paris", "max_places": 15},
            {"query": "cafes in London", "max_places": 10}
        ]
        
        batch = await manager.create_batch(queries)
        
        assert batch is not None
        assert batch.batch_id
        assert len(batch.job_ids) == 3
    
    @pytest.mark.asyncio
    async def test_batch_jobs_created(self, manager):
        """Test that batch creates individual jobs"""
        queries = [
            {"query": "test1", "max_places": 5},
            {"query": "test2", "max_places": 10}
        ]
        
        batch = await manager.create_batch(queries)
        
        # Check that jobs were created
        for job_id in batch.job_ids:
            job = await manager.get_job(job_id)
            assert job is not None
            assert job.batch_id == batch.batch_id
    
    @pytest.mark.asyncio
    async def test_get_batch(self, manager):
        """Test retrieving batch by ID"""
        queries = [{"query": "test", "max_places": 5}]
        batch = await manager.create_batch(queries)
        
        retrieved_batch = await manager.get_batch(batch.batch_id)
        
        assert retrieved_batch is not None
        assert retrieved_batch.batch_id == batch.batch_id
        assert retrieved_batch.job_ids == batch.job_ids
    
    @pytest.mark.asyncio
    async def test_get_batch_status(self, manager):
        """Test getting batch status"""
        queries = [
            {"query": "test1", "max_places": 5},
            {"query": "test2", "max_places": 10}
        ]
        
        batch = await manager.create_batch(queries)
        
        # Update one job to completed
        await manager.update_job_status(batch.job_ids[0], JobStatus.COMPLETED)
        
        status = await manager.get_batch_status(batch.batch_id)
        
        assert status is not None
        assert status["batch_id"] == batch.batch_id
        assert status["total_jobs"] == 2
        assert status["completed"] == 1
        assert status["pending"] == 1
        assert "jobs" in status
    
    @pytest.mark.asyncio
    async def test_batch_status_with_webhook(self, manager):
        """Test batch with webhook URLs"""
        queries = [
            {"query": "test", "max_places": 5, "webhook_url": "https://webhook.site/test"}
        ]
        
        batch = await manager.create_batch(queries)
        job = await manager.get_job(batch.job_ids[0])
        
        assert job.webhook_url == "https://webhook.site/test"


class TestWebhookCallbacks:
    """Test webhook functionality"""
    
    @pytest.mark.asyncio
    async def test_send_webhook_success(self, manager, sample_results):
        """Test successful webhook delivery"""
        webhook_url = "https://webhook.site/test"
        job = await manager.create_job("test", 10, webhook_url=webhook_url)
        
        await manager.set_job_results(job.job_id, sample_results)
        await manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            await manager.send_webhook(job.job_id)
            
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_webhook_no_url(self, manager):
        """Test webhook send when no URL configured"""
        job = await manager.create_job("test", 10)
        
        # Should not raise error
        await manager.send_webhook(job.job_id)
    
    @pytest.mark.asyncio
    async def test_send_webhook_failure(self, manager, sample_results):
        """Test webhook delivery failure handling"""
        webhook_url = "https://webhook.site/test"
        job = await manager.create_job("test", 10, webhook_url=webhook_url)
        
        await manager.set_job_results(job.job_id, sample_results)
        await manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Network error")
            
            # Should not raise error, just log
            await manager.send_webhook(job.job_id)


class TestJobExecution:
    """Test job execution flow"""
    
    @pytest.mark.asyncio
    async def test_execute_job_success(self, manager, sample_results):
        """Test successful job execution"""
        async def mock_scraper(query, max_places, progress_callback=None):
            return sample_results
        
        job = await manager.create_job("test", 10)
        
        await manager.execute_job(job.job_id, mock_scraper)
        
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.results == sample_results
    
    @pytest.mark.asyncio
    async def test_execute_job_failure(self, manager):
        """Test job execution with error"""
        async def failing_scraper(query, max_places, progress_callback=None):
            raise Exception("Scraping failed")
        
        job = await manager.create_job("test", 10)
        
        await manager.execute_job(job.job_id, failing_scraper)
        
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.FAILED
        assert "Scraping failed" in updated_job.error
    
    @pytest.mark.asyncio
    async def test_submit_job(self, manager):
        """Test job submission for background execution"""
        async def mock_scraper(query, max_places, progress_callback=None):
            await asyncio.sleep(0.1)
            return []
        
        job = await manager.create_job("test", 10)
        
        manager.submit_job(job.job_id, mock_scraper)
        
        # Give task time to start
        await asyncio.sleep(0.05)
        
        # Job should be in background tasks
        assert len(manager._background_tasks) > 0


class TestExportFormats:
    """Test result export in different formats"""
    
    @pytest.mark.asyncio
    async def test_export_json(self, manager, sample_results):
        """Test JSON export"""
        job = await manager.create_job("test", 10)
        await manager.set_job_results(job.job_id, sample_results)
        
        export = await manager.export_job_results(job.job_id, ExportFormat.JSON)
        
        assert export is not None
        assert "Test Restaurant" in export
        assert "Another Place" in export
        
        # Should be valid JSON
        import json
        parsed = json.loads(export)
        assert len(parsed) == 2
    
    @pytest.mark.asyncio
    async def test_export_csv(self, manager, sample_results):
        """Test CSV export"""
        job = await manager.create_job("test", 10)
        await manager.set_job_results(job.job_id, sample_results)
        
        export = await manager.export_job_results(job.job_id, ExportFormat.CSV)
        
        assert export is not None
        # CSV fields are sorted alphabetically
        assert "address" in export.lower()
        assert "email" in export.lower()
        assert "name" in export.lower()
        assert "test restaurant" in export.lower()
        assert "123 main st" in export.lower()
    
    @pytest.mark.asyncio
    async def test_export_emails(self, manager, sample_results):
        """Test email list export"""
        job = await manager.create_job("test", 10)
        await manager.set_job_results(job.job_id, sample_results)
        
        export = await manager.export_job_results(job.job_id, ExportFormat.EMAILS)
        
        assert export is not None
        assert "test@restaurant.com" in export
        assert "info@anotherplace.com" in export
        assert export.count("\n") >= 1  # At least one newline
    
    @pytest.mark.asyncio
    async def test_export_no_results(self, manager):
        """Test export when no results available"""
        job = await manager.create_job("test", 10)
        
        export = await manager.export_job_results(job.job_id, ExportFormat.JSON)
        
        assert export is None
    
    @pytest.mark.asyncio
    async def test_export_emails_no_emails(self, manager):
        """Test email export when results have no emails"""
        results = [
            {"name": "Place 1", "address": "Address 1"},
            {"name": "Place 2", "address": "Address 2"}
        ]
        
        job = await manager.create_job("test", 10)
        await manager.set_job_results(job.job_id, results)
        
        export = await manager.export_job_results(job.job_id, ExportFormat.EMAILS)
        
        assert export == ""


class TestJobModel:
    """Test Job model methods"""
    
    def test_job_to_dict(self):
        """Test job serialization to dict"""
        job = Job(
            job_id="test_123",
            query="test query",
            max_places=20,
            status=JobStatus.COMPLETED,
            total_items=20,
            processed_items=20
        )
        
        # Manually set progress since it's not auto-calculated in constructor
        job.progress = 100
        
        job_dict = job.to_dict()
        
        assert job_dict["job_id"] == "test_123"
        assert job_dict["query"] == "test query"
        assert job_dict["status"] == "completed"
        assert job_dict["progress"] == 100
    
    def test_estimated_completion_not_started(self):
        """Test ETA when job not started"""
        job = Job(
            job_id="test",
            query="test",
            max_places=10,
            total_items=10
        )
        
        eta = job.get_estimated_completion()
        assert eta is None
    
    def test_estimated_completion_no_progress(self):
        """Test ETA when no progress made"""
        job = Job(
            job_id="test",
            query="test",
            max_places=10,
            status=JobStatus.PROCESSING,
            started_at=datetime.utcnow(),
            total_items=10,
            processed_items=0
        )
        
        eta = job.get_estimated_completion()
        assert eta is None
    
    def test_estimated_completion_with_progress(self):
        """Test ETA calculation with progress"""
        job = Job(
            job_id="test",
            query="test",
            max_places=100,
            status=JobStatus.PROCESSING,
            started_at=datetime.utcnow() - timedelta(seconds=10),
            total_items=100,
            processed_items=50
        )
        
        eta = job.get_estimated_completion()
        assert eta is not None
        assert isinstance(eta, str)


class TestCleanup:
    """Test job cleanup functionality"""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_jobs(self, manager):
        """Test cleanup of old completed jobs"""
        # Create old completed job
        job = await manager.create_job("old test", 10)
        await manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        # Manually set completed_at to 25 hours ago
        manager._jobs[job.job_id].completed_at = datetime.utcnow() - timedelta(hours=25)
        
        # Create recent job
        recent_job = await manager.create_job("recent test", 10)
        await manager.update_job_status(recent_job.job_id, JobStatus.COMPLETED)
        
        await manager.cleanup_old_jobs(max_age_hours=24)
        
        # Old job should be deleted
        assert await manager.get_job(job.job_id) is None
        
        # Recent job should still exist
        assert await manager.get_job(recent_job.job_id) is not None
    
    @pytest.mark.asyncio
    async def test_cleanup_keeps_active_jobs(self, manager):
        """Test that cleanup doesn't delete active jobs"""
        job = await manager.create_job("active test", 10)
        await manager.update_job_status(job.job_id, JobStatus.PROCESSING)
        
        await manager.cleanup_old_jobs(max_age_hours=1)
        
        # Active job should not be deleted
        assert await manager.get_job(job.job_id) is not None


class TestBatchModel:
    """Test Batch model methods"""
    
    def test_batch_to_dict(self):
        """Test batch serialization"""
        batch = Batch(
            batch_id="batch_123",
            job_ids=["job1", "job2", "job3"]
        )
        
        batch_dict = batch.to_dict()
        
        assert batch_dict["batch_id"] == "batch_123"
        assert len(batch_dict["job_ids"]) == 3
        assert batch_dict["total_jobs"] == 3


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, manager):
        """Test getting job that doesn't exist"""
        job = await manager.get_job("nonexistent_id")
        assert job is None
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_batch(self, manager):
        """Test getting batch that doesn't exist"""
        batch = await manager.get_batch("nonexistent_id")
        assert batch is None
    
    @pytest.mark.asyncio
    async def test_batch_status_nonexistent(self, manager):
        """Test getting status of nonexistent batch"""
        status = await manager.get_batch_status("nonexistent_id")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_empty_batch(self, manager):
        """Test creating batch with empty queries"""
        batch = await manager.create_batch([])
        
        assert len(batch.job_ids) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_job_updates(self, manager):
        """Test concurrent updates to same job"""
        job = await manager.create_job("test", 100)
        
        # Simulate concurrent progress updates
        tasks = [
            manager.update_job_progress(job.job_id, i)
            for i in range(0, 100, 10)
        ]
        
        await asyncio.gather(*tasks)
        
        # Should not crash, final state should be valid
        updated_job = await manager.get_job(job.job_id)
        assert updated_job.processed_items <= 100
        assert updated_job.progress <= 100
