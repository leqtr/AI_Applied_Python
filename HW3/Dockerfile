FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

COPY start.sh .
CMD ["./start.sh"]

