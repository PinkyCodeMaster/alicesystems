FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /srv/alice/apps/hub-api

COPY apps/hub-api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY apps/hub-api /srv/alice/apps/hub-api
COPY infra/docker/practice/hub-api/practice-entrypoint.sh /usr/local/bin/practice-hub-entrypoint.sh

RUN chmod +x /usr/local/bin/practice-hub-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/practice-hub-entrypoint.sh"]
