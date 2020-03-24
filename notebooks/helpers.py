"""Utility method for registering environments with OpenAI gym."""

import gym
from gym.envs.registration import register

from copy import deepcopy

from flow.core.params import InitialConfig
from flow.core.params import TrafficLightParams
from flow.core.params import InFlows

def flatten(l):
    
    """Flattens nested list.
    Parameters
    ----------
    lst: list
        Nested list to flatten.
    Returns
    -------
    Flattened list."""
    return [item for sublist in l for item in sublist]
    

def invert_tl_state(old_state, api="sumo"):
    
    """Invert state for given traffic light.
    It currently only implements conversion for the sumo light state.
    This function returns the new state string (of the same length as the
    input state), this allows for handling intersections with different
    numbers of lanes and lights elegantly.
    This function takes any sumo light state but only convets to a "green"
    or "red" state. Orange and other states are converted accordingly, see
    implementation for more detail.
    Parameters
    ----------
    old_state: str
        Traffic light state string to invert.
    api: str
        Simulator API which defines the light state format to return.
        Currently only implements the sumo traffic state format.
        (see: https://sumo.dlr.de/wiki/Simulation/Traffic_Lights#Signal_state_definitions)
    Returns
    ----------
    new_state: str
        New light state consisting of only red and green lights that
        oppose the previous state as much as possible.
    """
    if api == "sumo":
        state = old_state.replace("g", "G")
        state = state.replace("y", "r")
        state = state.replace("G", "tmp")
        state = state.replace("r", "G")
        state = state.replace("tmp", "r")
        return state
    else:
        return NotImplementedError


def pad_list(lst, length, pad_with=0):
    """ Pads a list with extra elements.
    Parameters
    ----------
    lst: list
        List to pad
    length: int
        Must be greater than the length of `l`. The
        difference will be padded.
    pad_with: any
        Element to pad `l` with.
    e.g. pad_list([1,2,3], 5, 0) outputs [1,2,3,0,0]
    We use this helper to make sure that our states are of
    constant dimension even when some cars are not on the
    map (which happens when they get respawned)."""
    if len(lst) == length:
        return lst

    lst += [pad_with] * (length - len(lst))
    return lst


def get_inflow(spec):
    """ Generates an InFlows object based on a spec
    Prameters
    ---------
    spec : dict
        - keys : edge name to inject vehicles into
        - values : number of cars to inject hourly
    """
    inflow = InFlows()
    for k, v in spec.items():
        inflow.add(veh_type="human",
                   edge=k,
                   vehs_per_hour=v,
                   departSpeed=10,
                   departLane="random")
    return inflow


def make_create_env(params, version=0, render=None):
    """Create a parametrized flow environment compatible with OpenAI gym.
    This is a slightly modified version of `flow.contrib.registry`'s
    make_create_env so we don't have to drop our environments and
    scenarios in Flow's modules. The original docstring is copied pasted
    bellow.
    This environment creation method allows for the specification of several
    key parameters when creating any flow environment, including the requested
    environment and scenario classes, and the inputs needed to make these
    classes generalizable to networks of varying sizes and shapes, and well as
    varying forms of control (e.g. AVs, automated traffic lights, etc...).
    This method can also be used to recreate the environment a policy was
    trained on and assess it performance, or a modified form of the previous
    environment may be used to profile the performance of the policy on other
    types of networks.
    Parameters
    ----------
    params : dict
        flow-related parameters, consisting of the following keys:
         - exp_tag: name of the experiment
         - env_name: name of the flow environment the experiment is running on
         - scenario: name of the scenario class the experiment uses
         - sim: simulation-related parameters (see flow.core.params.SimParams)
         - env: environment related parameters (see flow.core.params.EnvParams)
         - net: network-related parameters (see flow.core.params.NetParams and
           the scenario's documentation or ADDITIONAL_NET_PARAMS component)
         - veh: vehicles to be placed in the network at the start of a rollout
           (see flow.core.vehicles.Vehicles)
         - initial (optional): parameters affecting the positioning of vehicles
           upon initialization/reset (see flow.core.params.InitialConfig)
         - tls (optional): traffic lights to be introduced to specific nodes
           (see flow.core.params.TrafficLightParams)
    version : int, optional
        environment version number
    render : bool, optional
        specifies whether to use the gui during execution. This overrides
        the render attribute in SumoParams
    Returns
    -------
    function
        method that calls OpenAI gym's register method and make method
    str
        name of the created gym environment
    """
    exp_tag = params["exp_tag"]

    env_name = params["env_name"] + '-v{}'.format(version)

    module = __import__(params["scenario"], fromlist=[params["scenario"]])
    scenario_class = getattr(module, params["scenario"])

    env_params = params['env']
    net_params = params['net']
    initial_config = params.get('initial', InitialConfig())
    traffic_lights = params.get("tls", TrafficLightParams())

    def create_env(*_):
        sim_params = deepcopy(params['sim'])
        vehicles = deepcopy(params['veh'])

        scenario = scenario_class(
            name=exp_tag,
            vehicles=vehicles,
            net_params=net_params,
            initial_config=initial_config,
            traffic_lights=traffic_lights,
        )

        if render is not None:
            sim_params.render = render

        try:
            register(id=env_name,
                     entry_point="IssyEnv" + ':{}'.format(params["env_name"]),
                     kwargs={
                         "env_params": env_params,
                         "sim_params": sim_params,
                         "scenario": scenario,
                         "simulator": params['simulator']
                     })
        except Exception:
            pass
        return gym.envs.make(env_name)

    return create_env, env_name