FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/jevstudio.db

VOLUME ["/data"]

EXPOSE 8155

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8155"]
