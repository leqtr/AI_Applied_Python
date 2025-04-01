FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

RUN apt-get update && apt-get install -y netcat-openbsd && apt-get clean

COPY . .

RUN chmod +x start.sh

CMD ["./start.sh"]
