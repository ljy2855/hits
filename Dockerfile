FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv==0.6.3 && \
    uv sync --no-dev

# Copy the entire server directory structure
COPY server /app/server/

ENV ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["uv", "run", "--no-dev", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "server.main:app"]