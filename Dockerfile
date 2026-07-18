# Compass — Studio + Interview Live (demo-safe: no user resumes baked in)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/compass-core /app/packages/compass-core
COPY apps/studio /app/apps/studio
COPY apps/interview-live /app/apps/interview-live
COPY content/fixtures /opt/compass/fixtures
COPY content/profile/example_profile.json /opt/compass/example_profile.json
COPY content/track/board.example.json /opt/compass/board.example.json

RUN mkdir -p /app/content/evidence /app/content/jobs /app/content/resumes \
    /app/content/interviews /app/content/diagnoses /app/content/track \
    /app/content/questions /app/content/rag /app/content/profile /app/content/fixtures \
    && pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e "/app/packages/compass-core[studio,live,rag]" \
    && pip install --no-cache-dir -r /app/apps/studio/requirements.txt \
    && pip install --no-cache-dir -r /app/apps/interview-live/requirements.txt

ENV COMPASS_ROOT=/app/content
ENV COMPASS_DEMO=1
ENV COMPASS_HOST=0.0.0.0
ENV COMPASS_PORT=7860
ENV COMPASS_LIVE_PORT=8766
ENV PYTHONUNBUFFERED=1

EXPOSE 7860 8766

COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["studio"]
