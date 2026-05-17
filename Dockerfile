# syntax=docker/dockerfile:1.7
# Multi-stage build → distroless runtime.
# Real-world analogy: we build the cake in a kitchen (builder stage), then
# serve it on a plate without bringing the messy kitchen along (distroless).

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS builder
WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --upgrade pip build && \
    pip wheel --wheel-dir /wheels . && \
    pip install --no-deps --target /deps /wheels/*.whl && \
    pip install --target /deps click rich pydantic pyyaml httpx

FROM gcr.io/distroless/python3-debian12:nonroot
LABEL org.opencontainers.image.source="https://github.com/Barrie20/terradrift"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.description="TerraDrift CLI"

WORKDIR /app
COPY --from=builder /deps /app
ENV PYTHONPATH=/app
USER nonroot

ENTRYPOINT ["python3", "-m", "terradrift.cli"]
CMD ["--help"]
