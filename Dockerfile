# S7 — ishlab chiqarish obrazi (API; bot alohida profil)
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ECO_LEDGER_DB=/app/data/eco_ledger.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/
COPY db/ db/
COPY docs/ docs/
COPY tests/ tests/

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/v1/health')"

# birinchi ishga tushishda demo ma'lumotlar seed qilinadi (real rejimda o'chiriladi)
CMD ["sh", "-c", "python3 scripts/run_demo.py && uvicorn src.api.app:app --host 0.0.0.0 --port 8000"]
