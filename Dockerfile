FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Package only what the current API reads. Training datasets and source workbooks
# remain outside the serving image.
COPY backend ./backend
COPY scripts/__init__.py scripts/train_real_baseline.py ./scripts/
COPY data/processed/canonical_ie.csv data/processed/training_table_labeled_jan2026.csv ./data/processed/
COPY artifacts/real_baseline/forecast_1h_occurrence.joblib artifacts/real_baseline/forecast_1h_volume.joblib ./artifacts/real_baseline/

RUN useradd --uid 10001 --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
