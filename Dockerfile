FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt ./

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code and configs
COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/

# Expose the port your app runs on (change if needed)
EXPOSE 5000

# Run the application (adjust if your entrypoint is different)
CMD ["python", "src/orchestrator/chaos_injector.py"]