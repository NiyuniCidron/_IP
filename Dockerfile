# Use a lightweight base image
FROM python:3.9-slim-buster

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables (example)
ENV DISCORD_WEBHOOKS="your_webhook_url1,your_webhook_url2"
ENV CHECK_INTERVAL=5
ENV CHECK_INTERVAL_UNIT="minutes"

# Expose the health check port
EXPOSE 9595

# Run the application
CMD ["python", "external-ip-notify.py"]

# Health check
HEALTHCHECK --interval=1m --timeout=3s \
  CMD curl -f http://localhost:9595 || exit 1