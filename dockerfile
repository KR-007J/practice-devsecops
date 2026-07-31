FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN adduser -D appuser && chown -R appuser:appuser /app
USER appuser
ENV APP_HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "app.py"]
