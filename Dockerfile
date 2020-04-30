FROM mmastand/chime-base:0.0.2

RUN mkdir /app
WORKDIR /app
COPY README.md .
COPY setup.cfg .
COPY setup.py .
COPY requirements.txt .
RUN pip install -U setuptools
# Creating an empty src dir is a (hopefully) temporary hack to improve layer caching and speed up image builds
# todo fix once the Pipfile, setup.py, requirements.txt, pyprojec.toml build/dist story is figured out
RUN mkdir src && pip install .
COPY .streamlit .streamlit
COPY settings.cfg .
COPY src src
RUN pip install requests
COPY national_data_downloader.py .

# Include any necessary data files
RUN mkdir data
COPY ./modeling/data/county_populations.csv ./modeling/king_ets_ff4.csv ./modeling/nyc_ets_ff23.csv ./data/

# Include any R scripts
COPY ./modeling/jason_model.R ./src/

ARG BUILD_TIME
ARG VERSION_NUMBER
ENV BUILD_TIME=$BUILD_TIME
ENV VERSION_NUMBER=$VERSION_NUMBER
RUN echo $BUILD_TIME $VERSION_NUMBER

CMD  python3.8 ./national_data_downloader.py & \
     gunicorn --bind localhost:8765 --workers 1 --threads 1 src.model_runner:app & \
     streamlit run src/app.py

