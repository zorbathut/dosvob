FROM python:3.8-alpine

RUN apk add --no-cache --update openssh-keygen openssh-client rsync
RUN pip install pipenv

COPY . /app
WORKDIR /app

RUN pipenv install --system

COPY dockertools/dosvob /etc/periodic/daily/dosvob

CMD ["dockertools/run.sh"]
