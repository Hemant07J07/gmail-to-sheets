# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Expect user to mount credentials folder and set env var SPREADSHEET_ID
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "src.main"]
