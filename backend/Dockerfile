FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source
COPY backend/ /app/backend/

# Create __init__.py files for package structure
RUN touch /app/backend/__init__.py

ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
