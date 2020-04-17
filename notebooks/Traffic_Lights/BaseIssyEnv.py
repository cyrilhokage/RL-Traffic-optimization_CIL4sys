import itertools
import numpy as np
from collections import OrderedDict

from gym.spaces.box import Box
from gym.spaces.discrete import Discrete

from flow.envs import Env

from Rewards import Rewards
from States import States


class BaseIssyEnv(Env):
    """Abstract class to inherit from. It provides helpers
    used accross models such as a traffic light state inversion method

    Required from env_params:

    * beta: (int) number of vehicles the agent can observe
    * action_spec: (dict<str,[str]>) allowed states for each traffic light ID.

    States
        To be defined in child class.

    Actions
        The action space consist of a list of float variables ranging from 0-1
        specifying whether a traffic light is supposed to switch or not.

    Rewards
        To be defined in child class.

    Termination
        A rollout is terminated once the time horizon is reached.
    """

    def __init__(self, env_params, sim_params, network, simulator='traci'):
        super().__init__(env_params, sim_params, network, simulator)
        self.beta              = env_params.get_additional_param("beta")
        self.tl_constraint_min = env_params.get_additional_param("tl_constraint_min")
        self.tl_constraint_max = env_params.get_additional_param("tl_constraint_max")
        self.action_spec       = env_params.get_additional_param("action_spec")
        self.algorithm         = env_params.get_additional_param("algorithm")
        self.sim_step          = env_params.get_additional_param("sim_step")
        self.model_params      = dict(beta=self.beta, )
        self.rewards           = Rewards(self.k, self.action_spec)
        self.states            = States(self.k, self.beta)

        print('=== INITIALISATION ===')
        self._init_obs_veh_acc()
        self._init_obs_veh_wait_steps()
        self._init_obs_tl_wait_steps()

        # Used for debug purposes
        self.current_timestep = 0


    def _init_obs_veh_acc(self):
        """Initializes the data structures that will store vehicle speeds and accelerations"""
        self._obs_veh_vel = OrderedDict([('human_' + str(i), 0)  for i in range(self.beta)])
        self.obs_veh_acc  = OrderedDict([('human_' + str(i), [0]) for i in range(self.beta)])

    def _update_obs_veh_acc(self):
        """Updates the observed vehicle speed and acceleration data structures.
        We do so by using an ordered dict to maintain column order across
        timesteps. When vehicles are being re-spawned, we set their
        acceleration to 0."""
        #print('i=',self.current_timestep,':',self.obs_veh_acc,'\n')
        
        placeholder = 0.
        speed_odict = OrderedDict([('human_' + str(i), placeholder) for i in range(self.beta)])

        for id in self.get_observable_veh_ids():
            speed_odict[id] = self.k.vehicle.get_speed(id)

        for i, id in enumerate(self.get_observable_veh_ids()):
            new_acc  = (speed_odict[id] - self._obs_veh_vel[id]) / self.sim_step
            list_acc = self.obs_veh_acc[id].copy()
            list_acc.append(new_acc)
            self.obs_veh_acc[id] = list_acc

        self._obs_veh_vel = speed_odict

    def _init_obs_veh_wait_steps(self):
        """Initializes attributes that will store the number of steps stayed
        idle by the beta observable vehicles"""

        # Because Sumo has not instantiated vehicles at this stage, we manually
        # generate the name of controllable vehicles according to the Sumo
        # naming convention.
        # We store this list in an attribute since it is needed when updating
        # `self.obs_veh_wait_steps` in the update loop and
        # `self.k.vehicles.get_ids` will not list vehicles that are being re-
        # routed (see `self._reroute_if_final_edge`).
        self._all_obs_veh_names = ['human_' + str(i) for i in range(self.beta)]

        # We instantiate a dictionary with veh_ids as keys and time steps spent
        # idled as values. We set all values to 0 since this is an init.
        self.obs_veh_wait_steps = {veh_id: 0 for veh_id in self._all_obs_veh_names}

    def _init_obs_tl_wait_steps(self):
        """Initializes attributes that will store the number of steps stayed
        idle by the traffic lights"""

        # Contrary to the observation of vehicules, the traffic light are
        # already named
        self._all_tl_names = self.action_spec.keys()

        # We instantiate a dictionary with tl_ids as keys and time steps spent
        # idled as values. We set all values to 0 since this is an init.
        self.obs_tl_wait_steps = {tl_id: {'current_state': '','timer': 0} for tl_id in self._all_tl_names}

    def map_action_to_tl_states(self, rl_actions):
        """Maps an rl_action list to new traffic light states based on
        `action_spec` or keeps current traffic light states as they are.

        Since the shape of `rl_action` depends on `self.algorithm`, the
        mapping from actions to new states is implemented for each algorithm.

        Parameters
        ----------
        rl_actions:
            PPO:  [float] - list of action probabilities of length
                 `self.get_num_actions()`. TODO: For the moment, only binary
                 intersections are handled.
            DQN: int - action number

        Returns: [string]
        -------
            List of strings of length `self.action_spec.keys()` containing
            the new state configuration for each intersection.
        """
        new_state = []
        if self.algorithm == "DQN":
            # identity_action = [
            #     tuple(
            #         self.k.traffic_light.get_state(id)
            #         for id in self.action_spec.keys())
            # ]
            all_actions = list(itertools.product(*list(self.action_spec.values())))  # + identity_action
            new_state = all_actions[rl_actions]
        elif self.algorithm == "PPO":
            new_state = [v[int(rl_actions[i])] for i, v in enumerate(list(self.action_spec.values()))]
        else:
            return NotImplementedError

        # Don't update traffic lights that have not exceeded the timer
        new_state = list(new_state)
        for i, tl_id in enumerate(self.action_spec.keys()):
            current_state = self.k.traffic_light.get_state(tl_id)
            timer_value   = self.obs_tl_wait_steps[tl_id]['timer']
            if timer_value < self.tl_constraint_min:
                new_state[i] = current_state
            else:
                # Pick new state if tl state hasn't changed in a while
                cond_A = timer_value > self.tl_constraint_max
                cond_B = new_state[i] == current_state
                if cond_A and cond_B:
                    possible_states = list(self.action_spec[tl_id])  # copy
                    possible_states.remove(current_state)
                    num_states = len(possible_states)
                    if num_states:
                        new_state_index = np.random.randint(num_states)
                        new_state[i] = possible_states[new_state_index]

                # Update state and timer if state changed
                if new_state[i] is not current_state:
                    self.obs_tl_wait_steps[tl_id] = {'current_state': new_state[i],'timer': 0}

        return new_state

    def get_num_traffic_lights(self):
        """Counts the number of traffic lights by summing
        the state string length for each intersection.

        Returns
        -------
        Number of traffic lights (int)"""
        count = 0
        for k in self.action_spec.keys():
            count += len(self.action_spec[k][0])
        return count

    def get_num_actions(self):
        """Calculates the number of possible actions by counting the
        traffic light states based on `self.action_spec`.

        In the DQN case, it counts the cardinality of the cartesian product of
        all traffic light states. It also adds 1 to that product to account
        for the "identity" action which keeps the traffic light states as they
        were in the last timestep.

        In the PPO case, it returns the number of intersections.

        Returns
        -------
        Number of actions (int)
        """
        count = 1
        for k in self.action_spec.keys():
            count *= len(self.action_spec[k])
        if self.algorithm == "DQN":
            return count  # + 1
        elif self.algorithm == "PPO":
            return len(self.action_spec.keys())
        else:
            return NotImplementedError

    @property
    def action_space(self):
        """Vector of floats from 0-1 indicating traffic light states."""
        if self.algorithm == "DQN":
            return Discrete(self.get_num_actions())
        elif self.algorithm == "PPO":
            return Box(low=0,high=1,shape=(self.get_num_actions(),), dtype=np.float32)
        else:
            return NotImplementedError

    def get_controlled_tl_ids(self):
        """Returns the list of RL controlled traffic lights."""
        return [
            id for id in self.k.traffic_light.get_ids()
            if id in self.action_spec.keys()
        ]

    def get_free_tl_ids(self):
        """Returns the list of uncontrollable traffic lights."""
        return [
            id for id in self.k.traffic_light.get_ids()
            if id not in self.action_spec.keys()
        ]

    def _apply_rl_actions(self, rl_actions):
        """Converts probabilities of choosing configuration for states of
        traffic lights on the map. All traffic lights for which IDs are not
        keys of `self.action_spec` are updated to all green light states.

        Parameters
        ----------
        rl_actions: [float]
            Individual probabilities of choosing a particular traffic
            light state configuration for controllable traffic lights on
            the map.
        """
        # Upadate controllable traffic lights
        new_tl_states = self.map_action_to_tl_states(rl_actions)
        for counter, tl_id in enumerate(self.action_spec.keys()):
            self.k.traffic_light.set_state(tl_id, new_tl_states[counter])

        # Set all other traffic lights to green
        free_tl_ids = self.get_free_tl_ids()
        for tl_id in free_tl_ids:
            old_state = self.k.traffic_light.get_state(tl_id)
            new_state = "G" * len(old_state)
            self.k.traffic_light.set_state(tl_id, new_state)

    def _update_obs_wait_steps(self):
        """This method updates `self.obs_veh_wait_steps`.

        Ex: If human_1 has been idled for 5 timesteps and human_2 is moving at
        1km/h, then `self.obs_veh_wait_steps` = {'human_1': 5, 'human_2': 0}"""
        self.obs_veh_wait_steps = {
            veh_id: 0 if not self.k.vehicle.get_speed(veh_id) else
            self.obs_veh_wait_steps[veh_id] + 1
            for veh_id in self.get_observable_veh_ids()
        }

        # Because when vehicles are being rerouted, they will not appear in the
        # list returned by `self.get_observable_veh_ids`, they will be left out
        # of `self.obs_veh_wait_steps`. We patch the dictionary as follows to
        # prevent key errors.
        for k in self._all_obs_veh_names:
            if k not in self.obs_veh_wait_steps:
                self.obs_veh_wait_steps[k] = 0

    def _increment_obs_tl_wait_steps(self):
        """This method increments `self.obs_tl_wait_steps`."""
        for tl_id in self.action_spec.keys():
            self.obs_tl_wait_steps[tl_id]['timer'] += 1

    def additional_command(self):
        """ Gets executed at each time step.

        - updates how long observable vehicles have been waiting for.
        - updates how long traffic lights have been in the same state for.
        - Used to insert vehicles that are on the exit edge and place them back on their entrance edge.
        - It also colors the beta observable vehicles on sumo's gui.

        See parent class for more information."""
        self._update_obs_wait_steps()
        self._increment_obs_tl_wait_steps()
        self._update_obs_veh_acc()

        for veh_id in self.k.vehicle.get_ids():
            self._reroute_if_final_edge(veh_id)


        # Used for debug purposes
        self.current_timestep += 1

    def get_observable_veh_ids(self):
        """Get the ids of all the vehicles observable by the model.

        Returns
        -------
        A list of vehicle ids (str)
        """
        return [id for id in self.k.vehicle.get_ids() if "human" in id]

    def _reroute_if_final_edge(self, veh_id):
        """Checks if an edge is the final edge. If it is spawn a new
        vehicle on a random edge and remove the old one."""

        # no need to reroute inflows
        if "flow" in veh_id:
            return

        # don't reroute if vehicle is not on route final edge
        current_edge = self.k.vehicle.get_edge(veh_id)
        final_edge   = self.k.vehicle.get_route(veh_id)[-1]
        if current_edge != final_edge:
            return

        type_id = self.k.vehicle.get_type(veh_id)

        # remove the vehicle
        self.k.vehicle.remove(veh_id)
        # reintroduce it at the start of the network
        random_route = self.network.get_random_route()
        self.k.vehicle.add(veh_id=veh_id,
                           edge=random_route,
                           type_id=str(type_id),
                           lane=str(0),
                           pos="0",
                           speed="max")
