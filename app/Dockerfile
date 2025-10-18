FROM python:3.13-slim

WORKDIR /app

COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt

COPY . .

CMD ["python", "app.py"]