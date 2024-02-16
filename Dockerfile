FROM python:3.11 AS base

# enable packports
RUN echo 'deb http://deb.debian.org/debian bullseye-backports main contrib non-free' >> /etc/apt/sources.list

RUN apt update
RUN apt install -y git git-filter-repo golang-1.16 
RUN pip install pipenv

RUN git config --global user.name dosvob
RUN git config --global user.email dosvob

# install diskrsync
RUN \
    mkdir workspace && \
    cd workspace && \
    GOPATH=$(pwd) /usr/lib/go-1.16/bin/go install github.com/dop251/diskrsync/diskrsync@latest && \
    cp -a bin/diskrsync /usr/local/bin && \
    cd .. && \
    rm -rf workspace

COPY . /app
WORKDIR /app

# copy ssh key from current directory if it exists
COPY id_rsa* /root/.ssh/

RUN pipenv install --system
RUN chmod +x /app/dockertools/*

WORKDIR /app/dockertools

FROM base AS cron

CMD ["./setup_cron.sh"]

FROM base AS debug

CMD ["./setup_debug.sh"]
