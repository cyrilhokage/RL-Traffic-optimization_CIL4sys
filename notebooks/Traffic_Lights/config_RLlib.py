#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  4 10:22:44 2020

@author: julien
"""

from ray.rllib.agents.registry import get_agent_class
from ray.tune.registry import register_env
from flow.utils.registry import make_create_env
from flow.utils.rllib import FlowParamsEncoder
import json


# DQN
def setup_DQN_exp(flow_params, n_cpus, horizon, rollouts):

    alg_run   = 'DQN'
    agent_cls = get_agent_class(alg_run)
    config    = agent_cls._default_config.copy()
    config['num_workers']      = n_cpus
    config['train_batch_size'] = horizon * rollouts
    config['gamma']            = 0.99
    config['clip_actions']     = False  # FIXME(ev) temporary ray bug
    config['horizon']          = horizon
    config["exploration_fraction"] = 0.05
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



# PPO 
def setup_PPO_exp(flow_params, n_cpus, horizon, rollouts):

    alg_run   = 'PPO'
    agent_cls = get_agent_class(alg_run)
    config    = agent_cls._default_config.copy()
    config['num_workers']      = n_cpus
    config['train_batch_size'] = horizon * rollouts
    config['gamma']            = 0.99 # Discount factor of the MDP.
    config['horizon']          = horizon
    config['clip_actions']     = False  # FIXME(ev) temporary ray bug

    # save the flow params for replay
    flow_json = json.dumps(flow_params, cls=FlowParamsEncoder,sort_keys=True,indent=4)
    config['env_config']['flow_params'] = flow_json
    config['env_config']['run'] = alg_run

    create_env, gym_name = make_create_env(params=flow_params,version=0)

    # Register as rllib env
    register_env(gym_name, create_env)
    
    return alg_run, gym_name, config
