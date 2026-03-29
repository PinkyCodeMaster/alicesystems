FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /srv/mock-device

COPY infra/docker/practice/mock-device/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY infra/docker/practice/mock-device/mock_device.py /srv/mock-device/mock_device.py

EXPOSE 8080

CMD ["python", "/srv/mock-device/mock_device.py"]
