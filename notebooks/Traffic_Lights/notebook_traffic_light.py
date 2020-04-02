#!/usr/bin/env python
# coding: utf-8

# # Train Traffic Lights Agents
# 
# Utilise les fonctions de @Binetruy
# 
# - crée un network à partir d'un fichier .osm et des trajectoires de véhiculess
# - ajoute un flux de voiture sur les routes
# - personnalise un Environnement pour le RL
# - integre l'environnement pour RLlib et execute la simulation
# 

# In[1]:


from flow.core.params import VehicleParams
from flow.core.params import NetParams, SumoCarFollowingParams
from flow.core.params import InitialConfig
from flow.core.params import EnvParams
from flow.core.params import SumoParams
from flow.controllers import RLController, IDMController
from flow.networks import Network
from flow.core.params import InFlows
from collections import OrderedDict
import json
import ray
from ray.rllib.agents.registry import get_agent_class
from ray.tune import run_experiments
from ray.tune.registry import register_env
from flow.utils.registry import make_create_env
from flow.utils.rllib import FlowParamsEncoder
from flow.core.params import VehicleParams, SumoCarFollowingParams


# ## Crée le network

# Specifie les noms des routes du network dont les vehicules peuvent être s'insérer

# In[2]:


EDGES_DISTRIBUTION = ["-100822066", "4794817", "4783299#0", "155558218"]


# créer la classe Network pour spécifier les itinéraires possibles

# In[3]:


class IssyOSMNetwork(Network):

    def specify_routes(self, net_params):
        return {
            "-100822066": [ #N
                "-100822066",
                "-352962858#1",
                "-352962858#0",
                "-4786940#1",
                 "-4786940#0",
            ],
            
            "4794817" : [ #Loop
                "4794817",
                "4786972#0",
                "4786972#1",
                "4786972#2",
                "4786965#1",
                "4786965#2",
                "4786965#3",
                "4795729",
                "-352962858#1",
                "4795742#0",
                "4795742#1",
                "4786965#3",
                "4786965#4",
                "4786965#5",
            ],
            
            "4783299#0": [    #E
                "4783299#0",
                "4783299#1",
                "4783299#2",
                "4783299#3",
                "4783299#4",
                "4783299#5",
                "4783299#6",
                "4786940#0",
                "4786940#1",
                "352962858#0",
                "352962858#1",
                "100822066",
            ],
            
            "155558218": [
                "155558218",
                "4786940#1",
                "352962858#0",
                "352962858#1",
                "100822066",
            ],     
        }


# ## Ajoute les flux de voiture

# `IDMController` : The Intelligent Driver Model is a car-following model specifying vehicle dynamics by a differential equation for acceleration $\dot{v}$.
# 
# `RLController` : a trainable autuonomous vehicle whose actions are dictated by an RL agent. 

# In[4]:


vehicles = VehicleParams()
vehicles.add("human",acceleration_controller=(IDMController, {}), num_vehicles=10)
vehicles.add("rl",acceleration_controller=(RLController, {}), num_vehicles=2)


# - `vehs_per_hour`: nombre de vehicule par heure, uniformément espacés. Par exemple, comme il y a $60 \times 60 = 3600$ secondes dans une heure, le parametre $\frac{3600}{5}=720$ va faire rentrer des vehicules dans le network toutes les $5$ secondes.
# 
# - `probability`: c'est la probabilité qu'un véhicule entre dans le network toutes les secondes. Par exemple, si on la fixe à $0.2$, alors chaque seconde de la simulation un véhicule aura $\frac{1}{5}$ chance d'entrer dans le network
# 
# - `period`: C'est le temps en secondes entre 2 véhicules qui sont insérés. Par exemple, le fixer à $5$ ferait rentrer des véhicules dans le network toutes les $5$ secondes (ce qui équivaut à mettre `vehs_per_hour` à $720$).
# 
# <font color='red'>
# $\rightarrow$ Exactement 1 seul de ces 3 paramètres doit être configurer !
# </font>

# In[5]:


inflow = InFlows()

inflow.add(veh_type      = "human",
           edge          = "4794817",
           probability   = 0.3, 
           depart_speed  = 7,
           depart_lane   = "random")

inflow.add(veh_type      = "human",
           edge          = "4783299#0",
           probability   = 0.2,
           depart_speed  = 7,
           depart_lane   = "random")

inflow.add(veh_type       = "human",
           edge           = "-100822066",
           probability    = 0.25,
           depart_speed   = 7,
           depart_lane    = "random")

inflow.add(veh_type       = "rl",
           edge           = "-100822066",
           probability    = 0.05,
           depart_speed   = 7,
           depart_lane    = "random",
           color          = "blue")

inflow.add(veh_type       = "human",
           edge          = "155558218",
           probability   = 0.2,
           depart_speed  = 7,
           depart_lane   = "random")


# ## Personnalise un Environnement pour le RL
# 
# plus de méthodes sur : http://berkeleyflow.readthedocs.io/en/latest/

# In[6]:


from IssyEnv import IssyEnv1


# ## Lance une simulation avec Training RLlib
# 
# Pour qu'un environnement puisse être entrainé, l'environnement doit être accessible via l'importation à partir de flow.envs. 
# 
# 
# <font color='red'>
# Copier l'environnement créé dans un fichier .py et on importe l'environnement dans `flow.envs.__init__.py`.
# Mettre le chemin absolu du fichier .osm .
# </font> 

# In[7]:


# possibles actions
action_spec = OrderedDict({ "30677963": [ "GGGGrrrGGGG", "rrrrGGGrrrr"],
                            "30763263": ["GGGGGGGGGG",  "rrrrrrrrrr"],
                            "30677810": [ "GGrr", "rrGG"]})


# In[8]:


horizon  = 100
SIM_STEP = 0.1
n_veh    = 12
rollouts = 10
n_cpus   = 2
discount_rate = 0.999


# In[9]:


# SUMO PARAM
sumo_params = SumoParams(sim_step=SIM_STEP, render=False, restart_instance=True)

# ENVIRONMENT PARAM
ADDITIONAL_ENV_PARAMS = {"beta": n_veh, "action_spec": action_spec, "algorithm": "DQN", "tl_constraint_min": 100,  "tl_constraint_max": 600, "sim_step": SIM_STEP}
env_params = EnvParams(additional_params=ADDITIONAL_ENV_PARAMS, horizon=horizon, warmup_steps=1)

# NETWORK PARAM
path_file  = '/home/julien/projet_CIL4SYS/NOTEBOOKS/issy.osm'
net_params = NetParams(inflows=inflow, osm_path=path_file) 

# NETWORK
network = IssyOSMNetwork

# INITIAL CONFIG
initial_config = InitialConfig(edges_distribution=EDGES_DISTRIBUTION)


flow_params = dict( exp_tag   = "ISSY_traffic", 
                    env_name  = IssyEnv1,  
                    network   = IssyOSMNetwork,
                    simulator = 'traci',
                    sim       = sumo_params,
                    env       = env_params,
                    net       = net_params,
                    veh       = vehicles,
                    initial   = initial_config)


# # Setup RLlib library

# Configures RLlib DQN algorithm to be used to train the RL model.

# In[10]:


def setup_DQN_exp():

    alg_run   = 'DQN'
    agent_cls = get_agent_class(alg_run)
    config    = agent_cls._default_config.copy()
    config['num_workers']      = n_cpus
    config['train_batch_size'] = horizon * rollouts
    config['gamma']            = discount_rate
    config['clip_actions']     = False  # FIXME(ev) temporary ray bug
    config['horizon']          = horizon
    config["hiddens"]          = [256]
    config['model'].update({'fcnet_hiddens': [32, 32]})

    # save the flow params for replay
    flow_json = json.dumps(flow_params, cls=FlowParamsEncoder, sort_keys=True, indent=4)
    config['env_config']['flow_params'] = flow_json
    config['env_config']['run'] = alg_run

    create_env, gym_name = make_create_env(params=flow_params, version=0)

    # Register as rllib env
    register_env(gym_name, create_env)
    
    return alg_run, gym_name, config


# Configures RLlib PPO algorithm to be used to train the RL model.
# 
# See: https://ray.readthedocs.io/en/latest/rllib-algorithms.html#proximal-policy-optimization-ppo

# In[11]:


def setup_PPO_exp():

    alg_run   = 'PPO'
    agent_cls = get_agent_class(alg_run)
    config    = agent_cls._default_config.copy()
    config['num_workers']      = n_cpus
    config['train_batch_size'] = horizon * rollouts
    config['gamma']            = discount_rate
    config['use_gae']          = True
    config['lambda']           = 0.97
    config['kl_target']        = 0.02
    config['num_sgd_iter']     = 10
    config['clip_actions']     = False  # FIXME(ev) temporary ray bug
    config['horizon']          = horizon
    config['model'].update({'fcnet_hiddens': [32, 32]})

    # save the flow params for replay
    flow_json = json.dumps(flow_params,cls=FlowParamsEncoder,sort_keys=True,indent=4)
    config['env_config']['flow_params'] = flow_json
    config['env_config']['run'] = alg_run

    create_env, gym_name = make_create_env(params=flow_params,version=0)

    # Register as rllib env
    register_env(gym_name, create_env)
    
    return alg_run, gym_name, config


# # Run Experiment

# In[12]:


alg_run, gym_name, config = setup_DQN_exp()

ray.init(num_cpus=n_cpus + 1)


# In[13]:


# import pixiedust
# %%pixie_debugger


# In[14]:


exp_tag = {"run": alg_run,
           "env": gym_name,
           "config": {**config},
           "checkpoint_freq": 2,
           "checkpoint_at_end": True,
           "max_failures": 999,
           "stop": {"training_iteration": 6}}


trials = run_experiments({flow_params["exp_tag"]: exp_tag})


# In[ ]:




