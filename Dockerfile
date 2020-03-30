FROM python:3.7.7-slim-buster

COPY .streamlit ~/

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -q -r requirements.txt

COPY . ./

ARG BUILD_TIME
ARG VERSION_NUMBER
ENV BUILD_TIME=$BUILD_TIME
ENV VERSION_NUMBER=$VERSION_NUMBER
RUN echo $BUILD_TIME $VERSION_NUMBER

CMD ["streamlit", "run", "src/app.py"]
