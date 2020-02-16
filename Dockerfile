FROM ubuntu:latest

#  $ docker build . -t continuumio/anaconda3:latest -t continuumio/anaconda3:5.3.0
#  $ docker run --rm -it continuumio/anaconda3:latest /bin/bash
#  $ docker push continuumio/anaconda3:latest
#  $ docker push continuumio/anaconda3:5.3.0

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH

RUN apt-get update --fix-missing && apt-get install -y wget bzip2 ca-certificates \
    libglib2.0-0 libxext6 libsm6 libxrender1 \
    git mercurial subversion

RUN wget --quiet https://repo.anaconda.com/archive/Anaconda3-5.3.0-Linux-x86_64.sh -O ~/anaconda.sh && \
    /bin/bash ~/anaconda.sh -b -p /opt/conda && \
    rm ~/anaconda.sh && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc

RUN apt-get install -y curl grep sed dpkg && \
    TINI_VERSION=`curl https://github.com/krallin/tini/releases/latest | grep -o "/v.*\"" | sed 's:^..\(.*\).$:\1:'` && \
    curl -L "https://github.com/krallin/tini/releases/download/v${TINI_VERSION}/tini_${TINI_VERSION}.deb" > tini.deb && \
    dpkg -i tini.deb && \
    rm tini.deb && \
    apt-get clean

ENTRYPOINT [ "/usr/bin/tini", "--" ]
CMD [ "/bin/bash" ]

####################### INSTALLATION SUMO & FLOW ##########################
WORKDIR /app
# MAINTAINER Fangyu Wu (fangyuwu@berkeley.edu)

# System
RUN apt-get update && \
	apt-get -y upgrade && \
	apt-get install -y \
    vim \
    apt-utils  && \
    pip install -U pip


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


ENV PATH /opt/conda/envs/flow/bin:$PATH
RUN /bin/bash -c "source activate flow" &&  \
    cd /app/flow/ && \
    pip install -e .   


#SUMO Installation
RUN apt install sudo
RUN  bash /app/flow/scripts/setup_sumo_ubuntu1804.sh

#Install
RUN apt install firefox --yes



#RUN conda init bash 
#RUN source ~/bashrc
#RUN ["/bin/bash", "-c", "conda init bash"] 
#RUN ["/bin/bash", "-c", "source ~/.bashrc"] 
#RUN ["/bin/bash", "-c", "conda activate flow"] 
#RUN conda activate flow
#Install jupyteexir in flow environnement
RUN conda install --quiet --yes -n flow jupyter




EXPOSE 8888