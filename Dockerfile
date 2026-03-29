ARG BUILD_FROM
FROM ${BUILD_FROM}

WORKDIR /app

COPY addon/main.py addon/requirements.txt ./

RUN pip3 install --no-cache-dir -r requirements.txt

# Register with s6-overlay (HA base image init system, PID 1).
# Never override CMD/ENTRYPOINT — the base image ENTRYPOINT is /init (s6).
COPY addon/run.sh /etc/services.d/ha-basic-addon/run
RUN chmod a+x /etc/services.d/ha-basic-addon/run

EXPOSE 8080
