# syntax=docker/dockerfile:1
# Volume 11 example: the image contains no credentials and accepts configuration at runtime.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY src/ai_platform /app/src/ai_platform

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8080
CMD ["python", "-m", "ai_platform.api.server"]
