#! /bin/bash

if [ $# -lt 1 ]; then
    echo "Please supply a version number as an argument."
    exit 1
fi

docker build --build-arg BUILD_TIME="`date +\"%A, %B %d, %Y\"`" --build-arg VERSION_NUMBER=$1 -t dsintegration.azurecr.io/aks/chime:$1 .