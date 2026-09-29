# ---- Stage 1: build the React UI ----
FROM node:22-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci --include=dev
COPY frontend ./
RUN npm run build

# ---- Stage 2: the Python API that also serves the UI ----
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-chat.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-chat.txt

COPY backend ./backend
COPY config ./config
COPY scripts/__init__.py scripts/train_real_baseline.py scripts/fetch_gfs_daily_panel.py scripts/train_gfs_constraint.py scripts/verify_gfs_source_availability.py scripts/run_gfs_constraint_inference.py scripts/forward_constraint.py ./scripts/
COPY data/processed/canonical_ie.csv data/processed/training_table_labeled_jan2026.csv data/processed/training_table_eirgrid_2026_jan_aug.csv data/processed/gfs_daily_2026_jan_aug_manifest.json ./data/processed/
COPY artifacts/real_baseline/forecast_1h_occurrence.joblib artifacts/real_baseline/forecast_1h_volume.joblib ./artifacts/real_baseline/
COPY artifacts/gfs_constraint/final_model.joblib artifacts/gfs_constraint/metrics.json ./artifacts/gfs_constraint/
COPY artifacts/forward_constraint ./artifacts/forward_constraint
COPY --from=ui /ui/dist ./frontend/dist

RUN useradd --uid 10001 --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
