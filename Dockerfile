FROM python:3.11-slim

WORKDIR /code

# Copy requirements first for better caching
COPY requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy application code
COPY . /code/

# Set environment variable with default value
ENV PORT=8000

# Expose port for the application
EXPOSE ${PORT}

# Command to run the application using the environment variable
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT} 