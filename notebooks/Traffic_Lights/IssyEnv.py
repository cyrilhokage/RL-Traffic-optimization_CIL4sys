import numpy as np

from gym.spaces.box import Box

from BaseIssyEnv import BaseIssyEnv


class IssyEnv1(BaseIssyEnv):
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

        return Box(low=0, high=float("inf"), shape=(7 * self.network.vehicles.num_vehicles + self.get_num_traffic_lights() + len(self.action_spec.keys()), ) )

    def get_state(self, **kwargs):
        """ We concatenate time tl have maintained state and vehicle
        accelerations to parent class state, and also include the vehicle
        accelerations.

        (See parent class for more information)"""
        veh_ids = self.get_observable_veh_ids()
        tl_ids  = self.get_controlled_tl_ids()

        return np.concatenate((
            self.states.veh.speeds(veh_ids),
            self.states.veh.orientations(veh_ids),
            self.states.veh.CO2_emissions(veh_ids),
            self.states.veh.wait_steps(self.obs_veh_wait_steps),
            self.states.veh.accelerations(self.obs_veh_acc),
            self.states.tl.binary_state_ohe(tl_ids),
            self.states.tl.wait_steps(self.obs_tl_wait_steps),
        ))

    def compute_reward(self, rl_actions, **kwargs):
        """We reward vehicule speeds and penalize their emissions along
        with idled cars.

        (See parent class for more information)"""
        max_emission    = 3000  # mg of CO2 per timestep
        min_speed       = 10    # km/h
        idled_max_steps = 80    # steps
        max_abs_acc     = 0.15  # m / s^2
        c = 0.001
        return c * (
            self.rewards.penalize_min_speed(min_speed) +
            self.rewards.penalize_max_emission(max_emission) +
            self.rewards.penalize_max_wait(self.obs_veh_wait_steps, idled_max_steps, 0, -10) +
            self.rewards.penalize_max_acc(self.obs_veh_acc, max_abs_acc, 1, 0)
        )
