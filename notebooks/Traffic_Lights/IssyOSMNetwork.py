"""Contains the IssyOSM network class."""

from flow.core.params import InitialConfig
from flow.core.params import TrafficLightParams
from flow.networks.base import Network
import numpy as np
from numpy import linspace, pi, sin, cos
import random

ADDITIONAL_NET_PARAMS = {
    # speed limit for all edges
    "speed_limit": 50 # 50Km/h is the limit in Issy
}

EDGES_DISTRIBUTION = [
    "-100822066",
    "4794817",
    "4783299#0",
    "155558218"
]

class IssyOSMNetwork(Network):
    """Network class for Issy simulations.

    This network is a recreation of Issy-les-Moulineaux from a OSM file.

    Usage
    -----
    >>> from flow.core.params import NetParams
    >>> from flow.core.params import VehicleParams
    >>> from flow.core.params import InitialConfig
    >>> from flow.networks import IssyOSMNetwork
    >>>
    >>> network = IssyOSMNetwork(
    >>>     name='Issy',
    >>>     vehicles=VehicleParams(),
    >>>     net_params=NetParams()
    >>> )
    """

    def __init__(self,
                 name,
                 vehicles,
                 net_params,
                 initial_config=InitialConfig(),
                 traffic_lights=TrafficLightParams()):
        """Instantiate the network class."""
        self.nodes_dict = dict()

        super().__init__(name, vehicles, net_params,
                         initial_config, traffic_lights)
    def get_routes_list(self):
        return list(self.specify_routes({}).keys())

    def get_random_route(self):
        return random.choice(self.get_routes_list())

    def specify_routes(self, net_params):
        rts = {
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
                "4786965#4",
                "4786965#5",   
            ],
            
            "4783299#0" : [ #Loop bis
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
                "4795742#0", #??
                "4795742#1",
                "4786965#3",
                "4795729",
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
        return rts
