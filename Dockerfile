FROM python:3.8-alpine

RUN apk add --no-cache --update openssh-keygen openssh-client rsync
RUN pip install pipenv

COPY . /app
WORKDIR /app

RUN pipenv install --system

COPY dockertools/dosib /etc/periodic/daily/dosib

CMD ["dockertools/run.sh"]
