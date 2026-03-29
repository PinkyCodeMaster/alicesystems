FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /srv/alice/apps/assistant-runtime

COPY apps/assistant-runtime/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY apps/assistant-runtime /srv/alice/apps/assistant-runtime

EXPOSE 8010

CMD ["python", "-m", "uvicorn", "assistant_runtime.main:app", "--host", "0.0.0.0", "--port", "8010"]
