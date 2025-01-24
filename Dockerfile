FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
   apt-get install -y --no-install-recommends \
   build-essential \
   curl \
   git \
   && rm -rf /var/lib/apt/lists/*

# Install honcho and langgraph
RUN pip install --no-cache-dir honcho "langgraph-cli[inmem]"

# Install poetry
ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python - && \
   cd /usr/local/bin && \
   ln -s /opt/poetry/bin/poetry && \
   poetry config virtualenvs.create false

# Configure poetry
ENV POETRY_NO_INTERACTION=1 \
   POETRY_VIRTUALENVS_CREATE=false \
   PORT=3000

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY slack_ai_agent/ ./slack_ai_agent/
COPY langgraph.json ./

# Install dependencies
RUN poetry install --only main

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 3000
ENTRYPOINT ["docker-entrypoint.sh"]
