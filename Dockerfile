FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . && useradd --create-home appuser && mkdir -p results && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["methane-monitor", "api"]
