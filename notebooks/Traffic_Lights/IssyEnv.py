import numpy as np

from gym.spaces.box import Box

from BaseIssyEnv import BaseIssyEnv1, BaseIssyEnv2
from collections import Counter

class IssyEnv1(BaseIssyEnv1):
    """Final environment.

    Required from env_params: See parent class

    States
        An observation is the set of positions, orientations, time spend idled,
        and speeds of the beta observed vehicles and the binary state of each
        RL controlled traffic lights along with how long ago each of the
        controlled intersections switched states.

    Actions
        See parent class

    Rewards
        The reward penalizes slow and/or emitting and/or idle time for the beta
        observable vehicles BUT does not penalize tl switches (as in IssyEnv2)

    Termination
        See parent class
    """

    @property
    def observation_space(self):
        """ In this model, we only observe 2D-positions and speed norms of
        the beta observable vehicles in cartesian coordinates, along with
        their orientation, absolute speed, CO2 emission, accelerations and
        time steps spent idled (speed=0). We also include the binary state
        of all RL controlled traffic lights and how many steps each tl have
        maintained their state for.

        Ex: If 2 observed cars and 10 RL controlled traffic lights control 3
        intersections, our state lives in $R^{7\times2} U B^10 U R^3$ where
        B={0,1} is the on/off state each traffic light can take.

        (See parent class for more information)"""

        num_obs_veh = self.beta # self.network.vehicles.num_vehicles #len(self.get_observable_veh_ids())
        return Box(low=-float("inf"), high=float("inf"), shape=(7 * num_obs_veh + self.get_num_traffic_lights() + len(self.action_spec.keys()), ) )

    def get_state(self, **kwargs):
        """ We concatenate time tl have maintained state and vehicle
        accelerations to parent class state, and also include the vehicle
        accelerations.

        (See parent class for more information)"""
        veh_ids = self.get_observable_veh_ids()
        tl_ids  = self.get_controlled_tl_ids()
        return np.concatenate((
            self.states.veh.accelerations(self.obs_veh_acc),
            self.states.veh.speeds(veh_ids),
            self.states.veh.CO2_emissions(veh_ids),
            self.states.veh.wait_steps(self.obs_veh_wait_steps),
            self.states.veh.orientations(veh_ids),
            self.states.tl.wait_steps(self.obs_tl_wait_steps),
            self.states.tl.binary_state_ohe(tl_ids),
        ))

    def compute_reward(self, rl_actions, **kwargs):
        """We reward vehicule speeds and penalize their emissions along
        with idled cars.

        (See parent class for more information)"""
        
        max_emission = 3000    # mg of CO2 per timestep
        min_speed = 10         # km/h
        idled_max_steps = 80   # steps
        max_abs_acc = 0.15     # m / s^2
        c = 0.001
        return c * (
            self.rewards.penalize_min_speed(min_speed) +
            self.rewards.penalize_max_emission(max_emission) +
            self.rewards.penalize_max_wait(self.obs_veh_wait_steps, idled_max_steps, 0, -10) +
            self.rewards.penalize_max_acc(self.obs_veh_acc, max_abs_acc, 1, 0)
        )
        
        """
        min_speed = 10    # km/h
        max_wait  = 80    # steps
        c1 = 1
        c2 = 0.01
        c3 = 100
        return  (c1 * self.rewards.penalize_min_speed(min_speed) - 
                 c2 * self.rewards.penalize_max_wait(self.obs_veh_wait_steps, max_wait) - 
                 c3 * self.rewards.penalize_max_acc(self.obs_veh_acc,1))"""

class IssyEnv2(BaseIssyEnv2):

    @property
    def observation_space(self):
        num_edges = len(self.k.network.get_edge_list())
        print(num_edges)
        return Box(low=-float("inf"), high=float("inf"), shape=(num_edges + self.get_num_traffic_lights(), ) )

            
    def get_queue_length(self):
        edges_each_veh = self.k.vehicle.get_edge(self.all_vehicles_ids)
        
        all_queues     = dict.fromkeys(self.k.network.get_edge_list(),0)
        
        # handle vehicule on junctions
        new_pos_veh      = dict(zip(self.all_vehicles_ids, edges_each_veh))
        new_pos_veh_true = new_pos_veh.copy()
        for veh_id in new_pos_veh:
            if ":" in new_pos_veh[veh_id]:
                new_pos_veh_true[veh_id] = self.pos_veh[veh_id]
            if new_pos_veh[veh_id]=='':
                del new_pos_veh_true[veh_id]
                
        current_queues = Counter(new_pos_veh_true.values())
        
        all_queues.update(dict(zip(current_queues.keys(), current_queues.values())))
        
        return all_queues


    def get_state(self, **kwargs):
        queues_length = [*self.get_queue_length().values()]
        tl_ids        = self.get_controlled_tl_ids()
        tl_states     = self.states.tl.binary_state_ohe(tl_ids)
        print(len(queues_length))
        a = np.concatenate((queues_length, tl_states))
        print(len(a[:len(self.k.network.get_edge_list())]))
        return np.concatenate((queues_length, tl_states))

    def compute_reward(self, rl_actions, **kwargs):
        """We penalize waiting steps"""
        
        return - np.sum([self.veh_wait_steps[veh_id] for veh_id in self.all_vehicles_ids ])
        