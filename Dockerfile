FROM python:3.8.2-slim

RUN apt-get update -qq
RUN apt-get install cron git libpng-dev curl sed unzip bash dos2unix vim -y

COPY pubmed-cron /etc/cron.d/pubmed-cron
RUN chmod 0644 /etc/cron.d/pubmed-cron
RUN crontab /etc/cron.d/pubmed-cron

COPY ./fetch_script /fetch_script
COPY ./requirements.txt /requirements.txt

RUN pip3 install -r requirements.txt

WORKDIR /fetch_script

CMD ["cron", "-f"]