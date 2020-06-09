import numpy as np


class Rewards:
    """Class providing rewards as methods allowing for easy composition of
    rewards from the IssyEnvAbstract derived classes.

    All public methods return an integer corresponding to the reward calculated
    at that time step."""

    def __init__(self, kernel, action_spec):
        """Instantiates a Reward object.

        Parameters
        ----------
        kernel: `flow.core.kernel.vehicle.TraCIVehicle`
            The TraCI Flow kernel for interacting with Sumo vehicles.
        action_spec: `BaseIssyEnv.action_spec`
            OrderedDict of controlled traffic light IDs with their allowed
            states."""
        self.kernel = kernel
        self.action_spec = action_spec
        self.tl_states = []  # traffic light states

    def _get_veh_ids(self):
        """Returns IDs of vehicles on the map at current time step."""
        return self.kernel.vehicle.get_ids()

    def _get_obs_veh_ids(self):
        """Returns IDs of the beta observable vehicles on the map at current
        time step."""
        return [
            veh_id for veh_id in self.kernel.vehicle.get_ids()
            if 'human' in veh_id
        ]

    def _get_controlled_tl_ids(self):
        return list(self.action_spec.keys())

    def penalize_min_speed(self, min_speed, reward=1, penalty=0):
        """This rewards the beta vehicles traveling over min_speed.

        Parameters
        ----------
        min_speed: int
            speed above which rewards are assigned
        reward: int
            reward for each vehicles traveling above the min_speed
        penalty: int
             penalty to assign to vehicles traveling under min_speed"""
        return np.sum([
            reward
            if self.kernel.vehicle.get_speed(id) > min_speed else penalty
            for id in self._get_obs_veh_ids()
        ])

    def penalize_tl_switch(self, penatly=10):
        """This reward penalizes when a controlled traffic light switches
        before a minimum amount of time steps.

        Parameters
        ----------
        penalty: int
             penalty to assign to vehicles traveling under min_speed"""
        current_states = [
            self.kernel.traffic_light.get_state(id)
            for id in self._get_controlled_tl_ids()
        ]

        # Return 0 at first time step and set tl_states
        if not len(self.tl_states):
            self.tl_states = current_states
            return 0

        reward = 0
        for i, old_state in enumerate(self.tl_states):
            if old_state is not current_states[i]:
                reward -= penatly

        self.tl_states = current_states

        return reward

    def penalize_max_emission(self, max_emission, reward=1, penalty=0):
        """This rewards the beta vehicles emitting less CO2 than a constraint.

        Parameters
        ----------
        min_emission: int
            emission level (in mg for the last time step, which is what Sumo
            outputs by default) under which rewards are assigned.
        reward: int
            reward for each vehicles emitting less than max_emission.
        penalty: int
             penalty to assign to vehicles emitting more than max_emission."""
        return np.sum([
            reward if self.kernel.vehicle.kernel_api.vehicle.getCO2Emission(id)
            < max_emission else penalty for id in self._get_veh_ids()
        ])

    def penalize_max_acc(self, obs_veh_acc, max_acc, reward=1, penalty=0):
        """This rewards the beta vehicles accelerating less than a constraint.

        Parameters
        ----------
        obs_veh_acc: Dict<String, Float>, type of `BaseIssyEnv.obs_veh_acc`
            Dictionary of accelerations in m/s^2.
        max_acc: float
            Absolute acceleration above which penalties are assigned.
        reward: int
            reward for each vehicles accelerating less than max_acc.
        penalty: int
             penalty to assign to vehicles traveling under max_acc"""
        return np.sum([reward if np.abs(acc) < max_acc else penalty for acc in obs_veh_acc.values()])
        
    def sum_acc_pos(self, obs_veh_acc):
        """This rewards the beta vehicles accelerating less than a constraint.

        Parameters
        ----------
        obs_veh_acc: Dict<String, Float>, type of `BaseIssyEnv.obs_veh_acc`
            Dictionary of accelerations in m/s^2."""
            
        return np.sum([np.max([0,acc]) for acc in obs_veh_acc.values()])


    def penalize_max_wait(self,
                          obs_veh_wait_steps,
                          max_wait,
                          reward=1,
                          penalty=0):
        """Penalizes each observable vehicle that has been idled for over
        `max_wait` timesteps.

        Parameters
        ----------
        obs_veh_wait_steps: dict<veh_id, int>
            Dictionary assigning to each observable vehicle ID the number of
            timesteps this vehicle has been idled for.
            (See `BaseIssyEnv._init_obs_veh_wait_steps` comments for more info)
        max_wait: int
            Maximum number of timesteps a car can be idled without being penalized.
        reward: int
            reward for each vehicles being idled for less that `max_wait`.
        penalty: int
             penalty to assign to vehicles idled for more than `max_wait`.
        """
        return np.sum([
            reward if obs_veh_wait_steps[veh_id] < max_wait else penalty
            for veh_id in self._get_obs_veh_ids()
        ])
    
    def sum_wait_step(self, obs_veh_wait_steps):
        
        return np.sum([obs_veh_wait_steps[veh_id] for veh_id in self._get_obs_veh_ids() ])

    def mean_speed(self):
        """Returns the mean velocity for all vehicles on the simulation."""
        speeds = self.kernel.vehicle.get_speed(self._get_veh_ids())
        return np.mean(speeds)

    def mean_emission(self):
        """Returns the mean CO2 emission for all vehicles on the simulation."""
        emission = [
            self.kernel.vehicle.kernel_api.vehicle.getCO2Emission(id)
            for id in self._get_veh_ids()
        ]

        return np.mean(emission)
