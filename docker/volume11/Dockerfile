# syntax=docker/dockerfile:1
# Volume 11 example: source staging is separate from the non-root runtime image.
# No package build, credential, registry, or image execution occurs in this teaching artifact.
FROM python:3.12-slim AS source

WORKDIR /build
COPY src/ai_platform /build/ai_platform

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser
COPY --from=source --chown=10001:10001 /build/ai_platform /app/src/ai_platform
USER appuser

EXPOSE 8080
CMD ["python", "-m", "ai_platform.api.server"]
