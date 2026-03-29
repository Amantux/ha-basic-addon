FROM python:3.12-slim

WORKDIR /app

COPY run.sh main.py requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt && \
    chmod +x /app/run.sh

EXPOSE 8080

ENTRYPOINT ["./run.sh"]
