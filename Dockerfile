FROM python:3.9

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir --upgrade pip

RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    rm -Rf ta-lib ta-lib-0.4.0-src.tar.gz

RUN --mount=type=cache,target=/root/.cache pip install --editable .

RUN apt update -y && apt install supervisor -y
COPY ./supervisord.conf /etc/supervisor/conf.d/supervisord.conf

ENTRYPOINT ["/usr/bin/supervisord"]
