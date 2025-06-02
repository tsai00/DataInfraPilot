FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update &&  \
    apt-get install -y gcc python3-dev curl &&  \
    apt-get clean &&  \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl && \
    pip install --no-cache-dir uv && \
    uv pip install --system -r pyproject.toml

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/helm /usr/local/bin/helm

COPY src/ /app/src

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]