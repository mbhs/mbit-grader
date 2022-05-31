FROM debian:bullseye-slim AS jail
RUN apt-get update -y && apt-get install -y pypy3 g++ openjdk-17-jdk

FROM python:3.10

RUN apt-get update && \
  apt-get install -y autoconf bison flex gcc g++ libnl-route-3-dev libprotobuf-dev libseccomp-dev libtool make pkg-config protobuf-compiler

WORKDIR /tmp/nsjail-build
COPY nsjail .
RUN make -j
RUN mv nsjail /usr/bin/nsjail
WORKDIR /app

RUN rm -r /tmp/nsjail-build

COPY --from=jail / /jail

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY cases /cases
COPY src /app
COPY jail-cfg /jail-cfg

ARG PORT=8080
ENV PORT=${PORT}

CMD gunicorn --workers 1 --threads 8 --timeout 0 main:app
