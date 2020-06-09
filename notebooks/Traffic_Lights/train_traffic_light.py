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
from flow.core.params import SumoCarFollowingParams, SumoLaneChangeParams
from flow.core.params import NetParams
from flow.core.params import InitialConfig
from flow.core.params import EnvParams
from flow.core.params import SumoParams
from flow.controllers import IDMController
from flow.core.params import InFlows
from collections import OrderedDict
import ray
from ray.tune import run_experiments

# ========= NETWORK ======= #
# Specifie les noms des routes du network dont les vehicules peuvent être s'insérer
# et les itinéraires possibles que les voitures utilisent
  
from Issy_Network import IssyOSMNetwork, EDGES_DISTRIBUTION


# ======= flux de voiture ====== #
n_veh    = 10
vehicles = VehicleParams()
vehicles.add("human", acceleration_controller=(IDMController, {}), num_vehicles=n_veh, car_following_params=SumoCarFollowingParams(speed_mode="right_of_way"),
             lane_change_params=SumoLaneChangeParams(lane_change_mode=2722), color='red')
vehicles.add("flow", acceleration_controller=(IDMController, {}), num_vehicles=n_veh, car_following_params=SumoCarFollowingParams(speed_mode="right_of_way"),
             lane_change_params=SumoLaneChangeParams(lane_change_mode=2722), color='white')

inflow = InFlows()
inflow.add(veh_type="human", edge="4794817", probability=0.01, depart_speed=7, depart_lane=0)
inflow.add(veh_type="human", edge="4783299#0", probability=0.2, depart_speed=7, depart_lane=0)
inflow.add(veh_type="human", edge="-100822066", probability=0.25, depart_speed=7,depart_lane=0)
inflow.add(veh_type="human",edge="155558218",probability=0.01, depart_speed=7, depart_lane=0)


# ======= Environnement personnalisé pour RL ======= #
from IssyEnv import IssyEnv1


# ======= Lance un Training RLlib ======= #

# actions possibles 
action_spec = OrderedDict({ "30677963": [ "GGGGrrrGGGG", "rrrrGGGrrrr"], "30677810": [ "GGrr", "rrGG"]})

# parameters
horizon  = 1000
SIM_STEP = 0.2
rollouts = 10
n_cpus   = 1


# SUMO PARAM
sumo_params = SumoParams(sim_step=SIM_STEP, overtake_right=True, render=False, restart_instance=True, print_warnings=False, no_step_log=False)

# ENVIRONMENT PARAM
ADDITIONAL_ENV_PARAMS = {"beta": n_veh, "action_spec": action_spec, "algorithm": "DQN", "tl_constraint_min": 100,  "tl_constraint_max": 600, "sim_step": SIM_STEP}
env_params = EnvParams(additional_params=ADDITIONAL_ENV_PARAMS, horizon=horizon, warmup_steps=1)

# NETWORK PARAM
path_osm  = '/home/julien/projet_CIL4SYS/NOTEBOOKS/issy.osm'
net_params = NetParams(inflows=inflow, osm_path=path_osm) 

# NETWORK
network = IssyOSMNetwork

# INITIAL CONFIG
initial_config = InitialConfig(spacing="uniform", edges_distribution=EDGES_DISTRIBUTION)


flow_params = dict( exp_tag   = "ISSY_traffic", 
                    env_name  = IssyEnv1,  
                    network   = IssyOSMNetwork,
                    simulator = 'traci',
                    sim       = sumo_params,
                    env       = env_params,
                    net       = net_params,
                    veh       = vehicles,
                    initial   = initial_config)


# # Configure RLlib library

from config_RLlib import setup_DQN_exp

alg_run, gym_name, config = setup_DQN_exp(flow_params, n_cpus, horizon, rollouts)


# # Run Experiment

# In[12]:

ray.init(num_cpus=n_cpus+1, ignore_reinit_error=True, include_webui=True, webui_host="") # , local_mode=True)



# In[14]:

# generate customize Callbacks 
from callbacks import Customize_Callbacks

config["callbacks"] = Customize_Callbacks(n_veh)


# In[14]:

# Run experiment
exp_tag = {"run": alg_run,
           "env": gym_name,
           "config": {**config},
           "checkpoint_freq": 2,
           "checkpoint_at_end": True,
           "max_failures": 10,
           "stop": {"training_iteration": 4}}
           #"resources_per_trial": {"cpu":2,"gpu":0}}


trials = run_experiments({flow_params["exp_tag"]: exp_tag}, queue_trials=True)


# In[ ]:

ray.shutdown()



