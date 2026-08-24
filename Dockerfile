FROM python:3.11-slim

WORKDIR /app

# Install security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging and source
COPY pyproject.toml .
COPY src/ src/
COPY templates/ templates/
COPY schemas/ schemas/
COPY books/ books/
COPY AGENTS.md LICENSE README.md ./

# Install Palimpsest
RUN pip install --no-cache-dir .

# Run with non-privileged user
RUN useradd -u 1000 -m palimpsest && chown -R palimpsest:palimpsest /app
USER palimpsest

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:8765/api/books || exit 1

CMD ["palimpsest", "serve", "--host", "0.0.0.0", "--port", "8765"]
