# Start with Linux containing Python 3.14.
FROM python:3.14-slim

# Make /public-pulse the working directory inside the image.
WORKDIR /public-pulse

# Install uv inside the image.
RUN pip install --no-cache-dir uv

# Copy dependency configuration before copying the application.
COPY pyproject.toml uv.lock ./

# Create /public-pulse/.venv and install the locked dependencies.
RUN uv sync --frozen --no-install-project

# Copy the remaining project files into /public-pulse.
COPY . .

# Start FastAPI when a container is created from this image.
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]