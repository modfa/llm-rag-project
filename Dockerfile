FROM python:3.12-slim

WORKDIR /app

RUN pip install pipenv

COPY data/travel_data.csv data/travel_data.csv
COPY ["Pipfile", "Pipfile.lock", "./"]

RUN pipenv install --deploy --ignore-pipfile --system

COPY travel_guide .

EXPOSE 5000

CMD gunicorn --bind 0.0.0.0:5000 app:app