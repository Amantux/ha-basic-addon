FROM python:3.12-slim

WORKDIR /app

COPY addon/run.sh addon/main.py addon/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt && \
    chmod +x ./run.sh

EXPOSE 8080

ENTRYPOINT ["./run.sh"]
