from fastapi import FastAPI, HTTPException, Query, Response, Request
from fastapi.responses import StreamingResponse, PlainTextResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
import logging
import io
import time
import uuid
from contextvars import ContextVar

# Import the scraper function (adjust path if necessary)
try:
    from gmaps_scraper_server.scraper import scrape_google_maps
except ImportError:
    # Handle case where scraper might be in a different structure later
    logging.error("Could not import scrape_google_maps from scraper.py")
    # Define a dummy function to allow API to start, but fail on call
    def scrape_google_maps(*args, **kwargs):
        raise ImportError("Scraper function not available.")

# Import job manager
from gmaps_scraper_server.job_manager import (
    job_manager,
    JobStatus,
    ExportFormat
)

# Import configuration and logging
try:
    from gmaps_scraper_server.config import settings
    from gmaps_scraper_server.logging_config import (
        setup_logging,
        get_logger,
        log_request_start,
        log_request_end,
        log_exception,
    )
    HAS_CONFIG = True
except ImportError:
    # Fallback to basic logging if config not available
    HAS_CONFIG = False
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    get_logger = lambda name: logging.getLogger(name)

# Initialize structured logging if available
if HAS_CONFIG:
    setup_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file if settings.log_file_enabled else None,
        log_max_bytes=settings.log_max_bytes,
        log_backup_count=settings.log_backup_count,
    )

# Context variable for request ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

app = FastAPI(
    title="Google Maps Scraper API",
    description="API to trigger Google Maps scraping based on a query.",
    version="0.1.0",
)

# Configure CORS if enabled
if HAS_CONFIG and settings.cors_enabled:
    from fastapi.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    )

# Add security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Add request size limit info
    if HAS_CONFIG:
        response.headers["X-Max-Request-Size"] = str(settings.max_request_size)
    
    return response

# Include health check router
try:
    from gmaps_scraper_server.health import router as health_router
    app.include_router(health_router)
except ImportError:
    logger = get_logger("startup")
    logger.warning("Health check endpoints not available (missing dependencies)")


# Logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all incoming requests and responses with timing"""
    # Generate request ID
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Log request start
    start_time = time.time()
    if HAS_CONFIG:
        log_request_start(
            method=request.method,
            path=request.url.path,
            request_id=request_id,
            client_ip=client_ip,
            query_params=dict(request.query_params),
        )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log request end
        if HAS_CONFIG:
            log_request_end(
                method=request.method,
                path=request.url.path,
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        
        # Add request ID header to response
        response.headers["X-Request-ID"] = request_id
        return response
        
    except Exception as e:
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log exception
        if HAS_CONFIG:
            log_exception(
                e,
                context={
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                }
            )
        else:
            logging.exception(f"Request failed: {request.method} {request.url.path}")
        
        # Re-raise exception to let FastAPI handle it
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    request_id = request_id_var.get("")
    
    if HAS_CONFIG:
        log_exception(
            exc,
            context={
                "method": request.method,
                "path": request.url.path,
                "request_id": request_id,
            }
        )
    else:
        logging.exception(f"Unhandled exception: {exc}")
    
    return Response(
        content={"detail": "Internal server error", "request_id": request_id},
        status_code=500,
        headers={"X-Request-ID": request_id}
    )


# Pydantic models for async endpoints
class AsyncScrapeRequest(BaseModel):
    """Request model for async scraping"""
    query: str = Field(..., description="The search query for Google Maps", min_length=1, max_length=200)
    max_places: int = Field(20, description="Maximum number of places to scrape", ge=1, le=500)
    lang: str = Field("en", description="Language code for results")
    webhook_url: Optional[HttpUrl] = Field(None, description="URL to receive results via webhook")


class BatchScrapeRequest(BaseModel):
    """Request model for batch scraping"""
    queries: List[Dict[str, Any]] = Field(..., description="Array of query configurations", min_items=1, max_items=50)


class JobResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    query: str
    progress: int
    estimated_completion: Optional[str] = None
    error: Optional[str] = None


# Helper function for async scraping
async def async_scrape_wrapper(query: str, max_places: int, progress_callback=None):
    """Wrapper for scraping function to work with job manager"""
    results = await scrape_google_maps(
        query=query,
        max_places=max_places,
        lang="en",
        headless=True
    )
    return results


@app.post("/api/v1/scrape/async")
async def create_async_scrape(request: AsyncScrapeRequest):
    """
    Create an async scraping job.
    Returns job_id immediately, processes in background, sends results to webhook when complete.
    """
    try:
        # Create job
        job = await job_manager.create_job(
            query=request.query,
            max_places=request.max_places,
            webhook_url=str(request.webhook_url) if request.webhook_url else None
        )
        
        # Submit job for background execution
        job_manager.submit_job(job.job_id, async_scrape_wrapper)
        
        logging.info(f"Created async job {job.job_id} for query: {request.query}")
        
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "query": job.query,
            "message": "Job created successfully. Use GET /api/v1/jobs/{job_id} to check status."
        }
    except Exception as e:
        logging.error(f"Error creating async job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get status of a scraping job.
    Returns status, progress, and results if completed.
    """
    job = await job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    response = job.to_dict()
    
    # Don't return full results in status endpoint (use export endpoint instead)
    if response.get("results"):
        response["results_count"] = len(response["results"])
        response["results"] = None
    
    return response


@app.post("/api/v1/scrape/batch")
async def create_batch_scrape(request: BatchScrapeRequest):
    """
    Create a batch of scraping jobs.
    Returns batch_id and all job_ids.
    """
    try:
        # Validate queries
        if not request.queries:
            raise HTTPException(status_code=400, detail="No queries provided")
        
        if len(request.queries) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 queries per batch")
        
        # Create batch
        batch = await job_manager.create_batch(request.queries)
        
        # Submit all jobs for background execution
        for job_id in batch.job_ids:
            job_manager.submit_job(job_id, async_scrape_wrapper)
        
        logging.info(f"Created batch {batch.batch_id} with {len(batch.job_ids)} jobs")
        
        return {
            "batch_id": batch.batch_id,
            "job_ids": batch.job_ids,
            "total_jobs": len(batch.job_ids),
            "message": f"Batch created with {len(batch.job_ids)} jobs. Use GET /api/v1/batches/{{batch_id}} to check status."
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/batches/{batch_id}")
async def get_batch_status(batch_id: str):
    """
    Get status of all jobs in a batch.
    Returns aggregated statistics and individual job statuses.
    """
    batch_status = await job_manager.get_batch_status(batch_id)
    
    if not batch_status:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    return batch_status


@app.get("/api/v1/jobs/{job_id}/export")
async def export_job_results(
    job_id: str,
    format: str = Query("json", description="Export format: json, csv, or emails")
):
    """
    Export job results in specified format.
    Supports: json, csv (for Google Sheets), emails (plain text list).
    """
    job = await job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job.status.value}"
        )
    
    if not job.results:
        raise HTTPException(status_code=404, detail="No results available for this job")
    
    # Validate format
    try:
        export_format = ExportFormat(format.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Supported formats: json, csv, emails"
        )
    
    # Generate export
    content = await job_manager.export_job_results(job_id, export_format)
    
    if not content:
        raise HTTPException(status_code=500, detail="Failed to generate export")
    
    # Set appropriate headers and return
    if export_format == ExportFormat.JSON:
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=job_{job_id}.json"
            }
        )
    elif export_format == ExportFormat.CSV:
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=job_{job_id}.csv"
            }
        )
    elif export_format == ExportFormat.EMAILS:
        return PlainTextResponse(
            content=content,
            headers={
                "Content-Disposition": f"attachment; filename=job_{job_id}_emails.txt"
            }
        )


@app.post("/scrape", response_model=List[Dict[str, Any]])
async def run_scrape(
    query: str = Query(..., description="The search query for Google Maps (e.g., 'restaurants in New York')"),
    max_places: Optional[int] = Query(None, description="Maximum number of places to scrape. Scrapes all found if None."),
    lang: str = Query("en", description="Language code for Google Maps results (e.g., 'en', 'es')."),
    headless: bool = Query(True, description="Run the browser in headless mode (no UI). Set to false for debugging locally.")
):
    """
    Triggers the Google Maps scraping process for the given query.
    """
    logging.info(f"Received scrape request for query: '{query}', max_places: {max_places}, lang: {lang}, headless: {headless}")
    try:
        # Run the potentially long-running scraping task
        # Note: For production, consider running this in a background task queue (e.g., Celery)
        # to avoid blocking the API server for long durations.
        results = await scrape_google_maps( # Added await
            query=query,
            max_places=max_places,
            lang=lang,
            headless=headless # Pass headless option from API
        )
        logging.info(f"Scraping finished for query: '{query}'. Found {len(results)} results.")
        return results
    except ImportError as e:
         logging.error(f"ImportError during scraping for query '{query}': {e}")
         raise HTTPException(status_code=500, detail="Server configuration error: Scraper not available.")
    except Exception as e:
        logging.error(f"An error occurred during scraping for query '{query}': {e}", exc_info=True)
        # Consider more specific error handling based on scraper exceptions
        raise HTTPException(status_code=500, detail=f"An internal error occurred during scraping: {str(e)}")

@app.get("/scrape-get", response_model=List[Dict[str, Any]])
async def run_scrape_get(
    query: str = Query(..., description="The search query for Google Maps (e.g., 'restaurants in New York')"),
    max_places: Optional[int] = Query(None, description="Maximum number of places to scrape. Scrapes all found if None."),
    lang: str = Query("en", description="Language code for Google Maps results (e.g., 'en', 'es')."),
    headless: bool = Query(True, description="Run the browser in headless mode (no UI). Set to false for debugging locally.")
):
    """
    Triggers the Google Maps scraping process for the given query via GET request.
    """
    logging.info(f"Received GET scrape request for query: '{query}', max_places: {max_places}, lang: {lang}, headless: {headless}")
    try:
        # Run the potentially long-running scraping task
        # Note: For production, consider running this in a background task queue (e.g., Celery)
        # to avoid blocking the API server for long durations.
        results = await scrape_google_maps( # Added await
            query=query,
            max_places=max_places,
            lang=lang,
            headless=headless # Pass headless option from API
        )
        logging.info(f"Scraping finished for query: '{query}'. Found {len(results)} results.")
        return results
    except ImportError as e:
         logging.error(f"ImportError during scraping for query '{query}': {e}")
         raise HTTPException(status_code=500, detail="Server configuration error: Scraper not available.")
    except Exception as e:
        logging.error(f"An error occurred during scraping for query '{query}': {e}", exc_info=True)
        # Consider more specific error handling based on scraper exceptions
        raise HTTPException(status_code=500, detail=f"An internal error occurred during scraping: {str(e)}")


# Basic root endpoint for health check or info
@app.get("/")
async def read_root():
    return {"message": "Google Maps Scraper API is running."}

# Example for running locally (uvicorn main_api:app --reload)
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)