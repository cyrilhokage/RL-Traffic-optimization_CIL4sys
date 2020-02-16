# DQN_CIL4SYS
An implementation of a traffic simulation optimisation with reinforcement learning, with FLOW and SUMO.

## Quick start tutorial 
#### 0. Requiements
    To start, it is recommanded to use a UNIX/LINUX operating system. If you are on windows, you can use a Windws Linux Subsystem.
    It is necessary to have docker installed on your computer.
    For all the following steps, you should stay at the root of this repository.

#### 1. Build Docker image (8.8 Gb data)
    This part may take some time to achieve.

    `docker build -t flow_ubuntu .`


#### 2. Start & run the container in interractive mode:

        `docker run -ti \
            -e DISPLAY=$DISPLAY \
            -p 8888:8888 \
            --name flow-container \
            --mount src="$(pwd)/notebooks",target=/app/notebooks,type=bind \
            flow_ubuntu`

  For this step, this are the meanings of our diffrecents parameters :
  
        - `-it` : we start the docker container in interractive mode
        
        - `-e DISPLAY=$DISPLAY` : with an environement variable to display GUI apps (brower, jupyter-notebook & SUMO). There make sur your environnement variable $DISPLAY is well configurated. If you run docker directly from Ubuntu, don't mind. But you run your container from a MAC OS or a Windows Linux Subsystem (WSL), you may have to use and configure Xlaunch / Xserver and configure the $DISPLAY variable.
        
        - `-p 8888:8888` to open the connection between the container and the local machine on port 8888; beacause jupyter notebooks listen this port.
        
        - `--name flow-container` : is the name of the container, you can put what you want here.
        
        - `-mount src=$(pwd)/notebooks, target=/app/notebooks, type=bind` : this allow us to mount a volume to create a shared folder between the folder 'notebooks' of this repo and a notebook folder in the container.
        
        - `flow_ubuntu` : The image of he container  
    
#### 3. Once the container is started (you will see a `#` at the beging of each command line in place of a `$`). Write the following commands :

    3.1 `conda activate flow` to activate the flow environement
    3.2 `jupyter notebook --ip=127.0.0.1 --allow-root` to start the jupyter notebook.

    Then a browser window should probably open, you can copy/paste the url in the command prompt into your browser to open the notebook.

#### 4. You can Start ! :) 

    

    
