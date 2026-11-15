# Build from the repo root:  docker build -f deploy/Dockerfile -t chinese-reader:0.1.0 .
# The full CC-CEDICT is fetched at build time (see the fetch step below), so no
# pre-build step is needed — a fresh `git pull && docker build` is self-contained.
# Requires network during the build (to reach MDBG); the NAS has it.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 CR_DATA_DIR=/data

# --chmod: COPY keeps file modes as the user running `docker build` sees them. On
# the NAS's UGOS share (ACL mode since 1.21) root sees 0770, so a build run with
# sudo or from root cron would leave the PUID:PGID user (1000:10) unable to read
# its own code (nas-stack's trackers hit this 2026-11-13). 0755 works for any
# builder (dirs need x). See nas-stack CLAUDE.md.
COPY --chmod=0755 backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY --chmod=0755 backend /app/backend
COPY --chmod=0755 web /app/web

# Bake the full dictionary into the image (cedict.u8 is gitignored / dockerignored
# and never vendored — CC-BY-SA + ~10 MB — so we pull it fresh here instead).
RUN python /app/backend/scripts/fetch_cedict.py

# config.py derives WEB_DIR as <repo>/web; here <repo> is /app.
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000"]
