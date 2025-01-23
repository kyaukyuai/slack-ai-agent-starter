#!/bin/bash
set -e

# Copy .env.example to .env if .env doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Execute the command passed to docker run
exec "$@"
