FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for ML packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (needed for some ML packages)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies with more memory and timeout
RUN pip install --no-cache-dir --timeout=1000 -r requirements.txt

# Copy backend application code
COPY backend/ ./backend/

# Set working directory to backend
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 