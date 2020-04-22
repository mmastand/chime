FROM maxtaggart/chime-base:0.0.1
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

# Write the county data to a csv.
COPY ./write_county_data.R .
RUN Rscript ./write_county_data.R

ARG BUILD_TIME
ARG VERSION_NUMBER
ENV BUILD_TIME=$BUILD_TIME
ENV VERSION_NUMBER=$VERSION_NUMBER
RUN echo $BUILD_TIME $VERSION_NUMBER

CMD ["streamlit", "run", "src/app.py"]

