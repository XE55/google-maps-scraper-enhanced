# Base image with system dependencies
FROM python:3.10-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies required by Playwright's browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    curl \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

# Development stage (includes test dependencies)
FROM base AS development

# Copy requirements and setup
COPY requirements.txt setup.py ./

# Install all dependencies including test tools
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e . --no-deps
RUN pip install --no-cache-dir pytest pytest-cov pytest-asyncio pytest-mock faker

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy the rest of the application code
COPY . .

# Expose port
EXPOSE 8001

# Default command
CMD ["uvicorn", "gmaps_scraper_server.main_api:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

# Testing stage (for running tests)
FROM development AS testing

# Run tests
CMD ["pytest", "tests/", "-v", "--cov=gmaps_scraper_server", "--cov-report=term-missing"]

# Production stage (minimal image)
FROM base AS production

# Copy requirements and setup
COPY requirements.txt setup.py ./

# Install production dependencies only
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e . --no-deps

# Install Playwright browsers (production minimal)
RUN playwright install --with-deps chromium

# Copy the rest of the application code
COPY . .

# Expose port
EXPOSE 8001

# Run as non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Production command
CMD ["uvicorn", "gmaps_scraper_server.main_api:app", "--host", "0.0.0.0", "--port", "8001"]
