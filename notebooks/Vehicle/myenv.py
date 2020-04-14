# import the base environment class
#from flow.envs.base import Env
from flow.envs import Env
from gym.spaces.box import Box
import numpy as np


class myEnv(Env):

    @property
    def action_space(self):
        
        num_actions = self.network.vehicles.num_rl_vehicles # self.k.vehicle.num_rl_vehicles # 
        accel_ub    = self.env_params.additional_params["max_accel"]
        accel_lb    = - abs(self.env_params.additional_params["max_decel"])

        return Box(low=accel_lb, high=accel_ub, shape=(num_actions,), dtype=np.float32)

    @property
    def observation_space(self):
        
        num_obs = 2*self.network.vehicles.num_vehicles # 2*self.k.vehicle.num_vehicles # 
        return Box(low=-float("inf"), high=float("inf"), shape=(num_obs,), dtype=np.float32)

    def _apply_rl_actions(self, rl_actions):

        rl_ids = self.k.vehicle.get_rl_ids()
        self.k.vehicle.apply_acceleration(rl_ids, rl_actions)

    def get_state(self, **kwargs):

        ids = self.k.vehicle.get_ids()
        pos = [self.k.vehicle.get_x_by_id(veh_id) for veh_id in ids]
        vel = [self.k.vehicle.get_speed(veh_id) for veh_id in ids]

        return np.concatenate((pos, vel))

    def compute_reward(self, rl_actions, **kwargs):

        ids = self.k.vehicle.get_ids()
        speeds = self.k.vehicle.get_speed(ids)

        return np.mean(speeds)

    def additional_command(self):
        """
        Used to insert vehicles that are on the exit edge and place them
        back on their entrance edge.
        """
        for veh_id in self.k.vehicle.get_ids():
            #if "rl" in veh_id:
            self._reroute_if_final_edge(veh_id)

    def _reroute_if_final_edge(self, veh_id):
        """Reroute vehicle associated with veh_id.
        Checks if an edge is the final edge. If it is return the route it
        should start off at.
        """
        edge = self.k.vehicle.get_edge(veh_id)
        current_route = self.k.vehicle.get_route(veh_id)
        if len(current_route) == 0: # this occurs to inflowing vehicles, whose information is not added  to the subscriptions in the first step that they departed
            return None
        elif edge == current_route[-1]:
            route_id = current_route[0]
            # remove the vehicle
            self.k.vehicle.remove(veh_id)
            # reintroduce it at the start of the network
            if "rl" in veh_id:
                type_id = "rl"
            elif "human" in veh_id:
                type_id = "human"
            else:
                print(veh_id,"= ERROR TYPE VEHICULE")
            lane_index = "free"
            self.k.vehicle.add(veh_id=veh_id, edge=route_id, type_id=str(type_id), lane=str(lane_index), pos="0", speed="max")
        else:
            return None
