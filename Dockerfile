FROM continuumio/miniconda3:latest
WORKDIR /app
# MAINTAINER Fangyu Wu (fangyuwu@berkeley.edu)

# System
RUN apt-get update && \
	apt-get -y upgrade && \
	apt-get install -y \
    vim \
    apt-utils && \
    pip install -U pip

# Flow dependencies
RUN cd ~ && \
    conda install opencv
    #pip install tensorflow

#FLOW
RUN cd /app && git clone https://github.com/flow-project/flow.git 

#SUMO dépendencies
RUN apt update

RUN apt -y install cmake swig libgtest-dev python-pygame python-scipy \
            autoconf libtool pkg-config libgdal-dev libxerces-c-dev \
            libproj-dev libfox-1.6-dev libxml2-dev libxslt1-dev build-essential \
            curl unzip flex bison python python-dev python3-dev libsm6 libxext6

#Create FLOW environnement
RUN conda env create -f /app/flow/environment.yml

RUN cd /app/flow/ && pip install -e .
# RUN echo "conda activate flow" >> ~/.bashrc

#SUMO Installation
RUN  bash /app/flow/scripts/setup_sumo_ubuntu1804.sh

#Install firefox
RUN apt install firefox-esr


#Install jupyteexir in flow environnement
RUN conda install --quiet --yes -n flow jupyter

EXPOSE 8888

# docker run -ti -p 8888:8888 -e DISPLAY=$DISPLAY flow_cil4sys

# jupyter notebook --ip=127.0.0.1 --allow-root
