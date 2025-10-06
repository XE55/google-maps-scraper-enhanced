"""
Comprehensive tests for Async API Endpoints

Tests async scraping, job status polling, batch processing, webhooks,
multi-format exports, error handling, and edge cases.

Coverage target: 95%+
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from gmaps_scraper_server.main_api import app
from gmaps_scraper_server.job_manager import JobStatus, job_manager


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_results():
    """Sample scraping results"""
    return [
        {
            "name": "Test Place",
            "address": "123 Test St",
            "phone": "+15551234567",
            "email": "test@place.com",
            "rating": 4.5
        }
    ]


@pytest.fixture(autouse=True)
def cleanup_jobs():
    """Clean up jobs after each test"""
    yield
    # Clear all jobs from manager
    job_manager._jobs.clear()
    job_manager._batches.clear()


class TestAsyncScrapeEndpoint:
    """Test POST /api/v1/scrape/async endpoint"""
    
    def test_create_async_job(self, client):
        """Test creating async scraping job"""
        response = client.post(
            "/api/v1/scrape/async",
            json={
                "query": "restaurants in NYC",
                "max_places": 20,
                "lang": "en"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert "status" in data
        assert data["query"] == "restaurants in NYC"
        assert data["status"] == "pending"
    
    def test_create_async_job_with_webhook(self, client):
        """Test creating job with webhook URL"""
        response = client.post(
            "/api/v1/scrape/async",
            json={
                "query": "hotels in Paris",
                "max_places": 10,
                "webhook_url": "https://webhook.site/test"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
    
    def test_create_async_job_invalid_query(self, client):
        """Test validation error for empty query"""
        response = client.post(
            "/api/v1/scrape/async",
            json={
                "query": "",
                "max_places": 10
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_async_job_invalid_max_places(self, client):
        """Test validation error for invalid max_places"""
        response = client.post(
            "/api/v1/scrape/async",
            json={
                "query": "test",
                "max_places": 0
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_async_job_max_places_too_high(self, client):
        """Test validation error for max_places > 500"""
        response = client.post(
            "/api/v1/scrape/async",
            json={
                "query": "test",
                "max_places": 501
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_async_job_invalid_webhook_url(self, client):
        """Test validation error for invalid webhook URL"""
        response = client.post(
            "/api/v1/scrape/async",
            json={
                "query": "test",
                "max_places": 10,
                "webhook_url": "not-a-url"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestJobStatusEndpoint:
    """Test GET /api/v1/jobs/{job_id} endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_job_status_pending(self, client):
        """Test getting status of pending job"""
        # Create job directly
        job = await job_manager.create_job("test query", 20)
        
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == job.job_id
        assert data["status"] == "pending"
        assert data["query"] == "test query"
        assert data["progress"] == 0
    
    @pytest.mark.asyncio
    async def test_get_job_status_processing(self, client):
        """Test getting status of processing job"""
        job = await job_manager.create_job("test query", 100)
        await job_manager.update_job_status(job.job_id, JobStatus.PROCESSING)
        await job_manager.update_job_progress(job.job_id, 50)
        
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "processing"
        assert data["progress"] == 50
    
    @pytest.mark.asyncio
    async def test_get_job_status_completed(self, client):
        """Test getting status of completed job"""
        job = await job_manager.create_job("test query", 10)
        await job_manager.set_job_results(job.job_id, [{"name": "test"}])
        await job_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert "results_count" in data
        assert data["results_count"] == 1
    
    @pytest.mark.asyncio
    async def test_get_job_status_failed(self, client):
        """Test getting status of failed job"""
        job = await job_manager.create_job("test query", 10)
        await job_manager.update_job_status(
            job.job_id,
            JobStatus.FAILED,
            error="Network timeout"
        )
        
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        assert data["error"] == "Network timeout"
    
    def test_get_job_status_not_found(self, client):
        """Test getting status of nonexistent job"""
        response = client.get("/api/v1/jobs/nonexistent_id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestBatchScrapeEndpoint:
    """Test POST /api/v1/scrape/batch endpoint"""
    
    def test_create_batch(self, client):
        """Test creating batch of jobs"""
        response = client.post(
            "/api/v1/scrape/batch",
            json={
                "queries": [
                    {"query": "restaurants in NYC", "max_places": 20},
                    {"query": "hotels in Paris", "max_places": 15},
                    {"query": "cafes in London", "max_places": 10}
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "batch_id" in data
        assert "job_ids" in data
        assert len(data["job_ids"]) == 3
        assert data["total_jobs"] == 3
    
    def test_create_batch_with_webhooks(self, client):
        """Test creating batch with webhook URLs"""
        response = client.post(
            "/api/v1/scrape/batch",
            json={
                "queries": [
                    {
                        "query": "test1",
                        "max_places": 10,
                        "webhook_url": "https://webhook.site/test1"
                    },
                    {
                        "query": "test2",
                        "max_places": 10,
                        "webhook_url": "https://webhook.site/test2"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["job_ids"]) == 2
    
    def test_create_batch_empty(self, client):
        """Test validation error for empty batch"""
        response = client.post(
            "/api/v1/scrape/batch",
            json={
                "queries": []
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_batch_too_many(self, client):
        """Test validation error for too many queries"""
        queries = [{"query": f"test{i}", "max_places": 5} for i in range(51)]
        
        response = client.post(
            "/api/v1/scrape/batch",
            json={"queries": queries}
        )
        
        # Pydantic validation returns 422, not 400
        assert response.status_code == 422
        # Check error message contains validation info
        assert "queries" in str(response.json()).lower()


class TestBatchStatusEndpoint:
    """Test GET /api/v1/batches/{batch_id} endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_batch_status(self, client):
        """Test getting batch status"""
        queries = [
            {"query": "test1", "max_places": 10},
            {"query": "test2", "max_places": 10}
        ]
        batch = await job_manager.create_batch(queries)
        
        response = client.get(f"/api/v1/batches/{batch.batch_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["batch_id"] == batch.batch_id
        assert data["total_jobs"] == 2
        assert "jobs" in data
    
    @pytest.mark.asyncio
    async def test_get_batch_status_with_progress(self, client):
        """Test batch status with mixed job statuses"""
        queries = [
            {"query": "test1", "max_places": 10},
            {"query": "test2", "max_places": 10},
            {"query": "test3", "max_places": 10}
        ]
        batch = await job_manager.create_batch(queries)
        
        # Update jobs to different statuses
        await job_manager.update_job_status(batch.job_ids[0], JobStatus.COMPLETED)
        await job_manager.update_job_status(batch.job_ids[1], JobStatus.PROCESSING)
        # Leave job 2 as pending
        
        response = client.get(f"/api/v1/batches/{batch.batch_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["completed"] == 1
        assert data["processing"] == 1
        assert data["pending"] == 1
    
    def test_get_batch_status_not_found(self, client):
        """Test getting status of nonexistent batch"""
        response = client.get("/api/v1/batches/nonexistent_id")
        
        assert response.status_code == 404


class TestExportEndpoint:
    """Test GET /api/v1/jobs/{job_id}/export endpoint"""
    
    @pytest.mark.asyncio
    async def test_export_json(self, client, sample_results):
        """Test JSON export"""
        job = await job_manager.create_job("test", 10)
        await job_manager.set_job_results(job.job_id, sample_results)
        await job_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        response = client.get(f"/api/v1/jobs/{job.job_id}/export?format=json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers.get("content-disposition", "")
        
        import json
        data = json.loads(response.text)
        assert len(data) == 1
        assert data[0]["name"] == "Test Place"
    
    @pytest.mark.asyncio
    async def test_export_csv(self, client, sample_results):
        """Test CSV export"""
        job = await job_manager.create_job("test", 10)
        await job_manager.set_job_results(job.job_id, sample_results)
        await job_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        response = client.get(f"/api/v1/jobs/{job.job_id}/export?format=csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Test Place" in response.text
        assert "123 Test St" in response.text
    
    @pytest.mark.asyncio
    async def test_export_emails(self, client, sample_results):
        """Test emails export"""
        job = await job_manager.create_job("test", 10)
        await job_manager.set_job_results(job.job_id, sample_results)
        await job_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        response = client.get(f"/api/v1/jobs/{job.job_id}/export?format=emails")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "test@place.com" in response.text
    
    def test_export_job_not_found(self, client):
        """Test export of nonexistent job"""
        response = client.get("/api/v1/jobs/nonexistent/export")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_export_job_not_completed(self, client):
        """Test export of incomplete job"""
        job = await job_manager.create_job("test", 10)
        await job_manager.update_job_status(job.job_id, JobStatus.PROCESSING)
        
        response = client.get(f"/api/v1/jobs/{job.job_id}/export")
        
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_export_invalid_format(self, client):
        """Test export with invalid format"""
        job = await job_manager.create_job("test", 10)
        await job_manager.set_job_results(job.job_id, [{"test": "data"}])
        await job_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        response = client.get(f"/api/v1/jobs/{job.job_id}/export?format=invalid")
        
        assert response.status_code == 400
        assert "Invalid format" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_export_no_results(self, client):
        """Test export when job has no results"""
        job = await job_manager.create_job("test", 10)
        await job_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        response = client.get(f"/api/v1/jobs/{job.job_id}/export")
        
        assert response.status_code == 404
        assert "No results" in response.json()["detail"]


class TestExistingEndpoints:
    """Test that existing endpoints still work"""
    
    @patch('gmaps_scraper_server.main_api.scrape_google_maps')
    def test_sync_scrape_endpoint(self, mock_scrape, client, sample_results):
        """Test original POST /scrape endpoint"""
        mock_scrape.return_value = sample_results
        
        response = client.post(
            "/scrape",
            params={
                "query": "restaurants in NYC",
                "max_places": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    @patch('gmaps_scraper_server.main_api.scrape_google_maps')
    def test_sync_scrape_get_endpoint(self, mock_scrape, client, sample_results):
        """Test original GET /scrape-get endpoint"""
        mock_scrape.return_value = sample_results
        
        response = client.get(
            "/scrape-get",
            params={
                "query": "hotels in Paris",
                "max_places": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    def test_root_endpoint(self, client):
        """Test root health check endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "running" in response.json()["message"].lower()


class TestConcurrency:
    """Test concurrent operations"""
    
    def test_multiple_async_jobs(self, client):
        """Test creating multiple async jobs simultaneously"""
        responses = []
        
        for i in range(5):
            response = client.post(
                "/api/v1/scrape/async",
                json={
                    "query": f"test query {i}",
                    "max_places": 10
                }
            )
            responses.append(response)
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        
        # All should have unique job IDs
        job_ids = [r.json()["job_id"] for r in responses]
        assert len(set(job_ids)) == 5
    
    def test_multiple_batches(self, client):
        """Test creating multiple batches"""
        responses = []
        
        for i in range(3):
            response = client.post(
                "/api/v1/scrape/batch",
                json={
                    "queries": [
                        {"query": f"test {i}-1", "max_places": 5},
                        {"query": f"test {i}-2", "max_places": 5}
                    ]
                }
            )
            responses.append(response)
        
        assert all(r.status_code == 200 for r in responses)
        
        # All should have unique batch IDs
        batch_ids = [r.json()["batch_id"] for r in responses]
        assert len(set(batch_ids)) == 3


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_malformed_json(self, client):
        """Test handling of malformed JSON"""
        response = client.post(
            "/api/v1/scrape/async",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_job_status_after_failure(self, client):
        """Test job status reflects failure correctly"""
        job = await job_manager.create_job("test", 10)
        await job_manager.update_job_status(
            job.job_id,
            JobStatus.FAILED,
            error="Test error"
        )
        
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "Test error" in data["error"]


class TestIntegrationFlow:
    """Test complete workflow integration"""
    
    @pytest.mark.asyncio
    async def test_complete_async_workflow(self, client, sample_results):
        """Test complete async job workflow"""
        # 1. Create async job
        create_response = client.post(
            "/api/v1/scrape/async",
            json={
                "query": "test workflow",
                "max_places": 10
            }
        )
        
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]
        
        # 2. Check initial status (might be pending or processing due to async submission)
        status_response = client.get(f"/api/v1/jobs/{job_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] in ["pending", "processing"]
        
        # 3. Simulate job completion
        await job_manager.set_job_results(job_id, sample_results)
        await job_manager.update_job_status(job_id, JobStatus.COMPLETED)
        
        # 4. Check completed status
        status_response = client.get(f"/api/v1/jobs/{job_id}")
        assert status_response.json()["status"] == "completed"
        
        # 5. Export results as JSON
        export_response = client.get(f"/api/v1/jobs/{job_id}/export?format=json")
        assert export_response.status_code == 200
        
        # 6. Export results as CSV
        csv_response = client.get(f"/api/v1/jobs/{job_id}/export?format=csv")
        assert csv_response.status_code == 200
        
        # 7. Export emails
        email_response = client.get(f"/api/v1/jobs/{job_id}/export?format=emails")
        assert email_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_complete_batch_workflow(self, client):
        """Test complete batch workflow"""
        # 1. Create batch
        create_response = client.post(
            "/api/v1/scrape/batch",
            json={
                "queries": [
                    {"query": "test1", "max_places": 5},
                    {"query": "test2", "max_places": 5}
                ]
            }
        )
        
        assert create_response.status_code == 200
        batch_id = create_response.json()["batch_id"]
        job_ids = create_response.json()["job_ids"]
        
        # 2. Check batch status (jobs might start processing immediately)
        status_response = client.get(f"/api/v1/batches/{batch_id}")
        assert status_response.status_code == 200
        # Jobs are submitted for background execution, so status varies
        data = status_response.json()
        assert data["total_jobs"] == 2
        
        # 3. Complete one job
        await job_manager.set_job_results(job_ids[0], [])
        await job_manager.update_job_status(job_ids[0], JobStatus.COMPLETED)
        
        # 4. Check updated batch status
        status_response = client.get(f"/api/v1/batches/{batch_id}")
        data = status_response.json()
        assert data["completed"] >= 1  # At least one completed
        assert data["total_jobs"] == 2
        
        # 5. Complete second job
        await job_manager.set_job_results(job_ids[1], [])
        await job_manager.update_job_status(job_ids[1], JobStatus.COMPLETED)
        
        # 6. Check final batch status
        status_response = client.get(f"/api/v1/batches/{batch_id}")
        data = status_response.json()
        assert data["completed"] == 2
        assert data["pending"] == 0
