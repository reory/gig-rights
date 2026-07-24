# Use official Python 3.12 slim image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside container
WORKDIR /app

# Install system dependencies (build tools needed for C-extensions/ReportLab if required)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project dependency files first for layer caching
COPY pyproject.toml README.md /app/

# Copy the entire source code
COPY . /app

# Install package in editable mode along with dependencies
RUN pip install --no-cache-dir -e .

# Expose FastAPI port
EXPOSE 8000

# Default command to run the Uvicorn server
CMD ["uvicorn", "gig_rights.main:app", "--host", "0.0.0.0", "--port", "8000"]