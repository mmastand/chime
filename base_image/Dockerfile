FROM maxtaggart/r-python-base:r3.6.3-python3.8

# Install low-level forecast dependencies
RUN apt-get update && \
    apt-get install libcurl4-openssl-dev -y && \
    apt-get install gfortran -y && \
    apt-get install liblapack-dev -y

# Install R Dependencies
COPY install_r_dependencies.R .
RUN Rscript ./install_r_dependencies.R