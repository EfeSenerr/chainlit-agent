FROM python:3.11-slim

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app


COPY ./api/requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
COPY ./api ./api
COPY ./utils ./utils

EXPOSE 80

CMD ["fastapi", "run", "api/main.py", "--port", "80"]