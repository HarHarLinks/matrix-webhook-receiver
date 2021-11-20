# syntax=docker/dockerfile:1

FROM python:alpine
COPY requirements.txt ./
RUN apk add --no-cache --virtual .build-deps gcc g++ musl-dev \
 && pip install --no-cache-dir -r requirements.txt \
 && apk del .build-deps gcc g++ musl-dev 
RUN mkdir -p /app/data
COPY main.py /app
COPY profiles.html /app
WORKDIR /app
EXPOSE 8000/tcp
CMD uvicorn --host 0.0.0.0 --port 8000 main:app
