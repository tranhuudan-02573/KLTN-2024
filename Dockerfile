# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/srv

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the model and source code
COPY ./final-model-v1 ./final-model-v1
COPY ./src ./src
COPY ./app.py .

# Add the current directory to PYTHONPATH
ENV PYTHONPATH=/usr/srv

# Make port 8068 available to the world outside this container
EXPOSE 8068

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8068", "--reload"]