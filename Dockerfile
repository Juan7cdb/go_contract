# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port (Railway will override this via $PORT, Uvicorn needs to listen on it)
EXPOSE 8000

# Run the application
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
