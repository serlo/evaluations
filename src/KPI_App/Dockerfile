FROM python:3.8

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY KPI_app.py app.py

CMD ["python3", "app.py"]