FROM python:3.7.7-slim-buster
RUN mkdir /app
WORKDIR /app
COPY README.md .
COPY setup.cfg .
COPY setup.py .
COPY requirements.txt .
# Creating an empty src dir is a (hopefully) temporary hack to improve layer caching and speed up image builds
# todo fix once the Pipfile, setup.py, requirements.txt, pyprojec.toml build/dist story is figured out
RUN mkdir src && pip install -q .
COPY .streamlit .streamlit
COPY settings.cfg .
COPY src src

ARG BUILD_TIME
ARG VERSION_NUMBER
ENV BUILD_TIME=$BUILD_TIME
ENV VERSION_NUMBER=$VERSION_NUMBER
RUN echo $BUILD_TIME $VERSION_NUMBER

CMD ["streamlit", "run", "src/app.py"]

