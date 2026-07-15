# Build from the repo root:  docker build -f deploy/Dockerfile -t chinese-reader:0.1.0 .
# The full CC-CEDICT is fetched at build time (see the fetch step below), so no
# pre-build step is needed — a fresh `git pull && docker build` is self-contained.
# Requires network during the build (to reach MDBG); the NAS has it.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 CR_DATA_DIR=/data

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY web /app/web

# Bake the full dictionary into the image (cedict.u8 is gitignored / dockerignored
# and never vendored — CC-BY-SA + ~10 MB — so we pull it fresh here instead).
RUN python /app/backend/scripts/fetch_cedict.py

# config.py derives WEB_DIR as <repo>/web; here <repo> is /app.
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000"]
