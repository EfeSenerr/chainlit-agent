FROM python:3.11-slim

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY ./chainlit/requirements.txt .
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
COPY ./chainlit ./chainlit
COPY ./utils ./utils

EXPOSE 80

CMD ["chainlit", "run", "chainlit/chainlit_app.py", "--host", "0.0.0.0", "--port", "80"]