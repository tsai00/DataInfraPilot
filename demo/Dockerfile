FROM --platform=linux/amd64 python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update &&  \
    apt-get install -y gcc python3-dev curl build-essential libpq-dev &&  \
    apt-get clean &&  \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv && uv pip install --system -r pyproject.toml

COPY src /app/src

CMD ["tail", "-f", "/dev/null"]