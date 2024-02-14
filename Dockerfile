FROM python:3.11 AS base

RUN apt update
RUN apt install -y rsync git cron
RUN pip install pipenv

# install xethub
RUN \
    wget https://github.com/xetdata/xet-tools/releases/latest/download/xet-linux-x86_64.tar.gz && \
    tar -xvf xet-linux-x86_64.tar.gz && \
    rm xet-linux-x86_64.tar.gz && \
    mv git-xet /usr/local/bin && \
    chmod +x /usr/local/bin/git-xet && \
    git xet install

COPY . /app
WORKDIR /app

RUN pipenv install --system
RUN chmod +x /app/dockertools/*

WORKDIR /app/dockertools

FROM base AS cron

CMD ["./setup_cron.sh"]

FROM base AS debug

CMD ["./setup_debug.sh"]
