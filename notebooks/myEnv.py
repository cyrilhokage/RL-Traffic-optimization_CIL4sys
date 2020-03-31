# import the base environment class
from flow.envs import Env
from gym.spaces.box import Box
import numpy as np



# define the environment class, and inherit properties from the base environment class
class MyEnv(Env):
    
    """
        Function to get Vehicles ids in an environment
        Return : a list of vehicles id in the environment
        
    """
    def get_veh_ids(self):
        
        try:
            
            ids = self.k.vehicle.get_ids()
            assert len(ids) != 0       #On teste si la liste des ids n'est pas vide
            
            return ids
            
        except AssertionError:
            print("\n \n \n \n \t -------------------- \n \t  Un probleme lors de la récupération des ids des véhicules ! \n \t ------------ \n \n ")
            return None 
    
    
    @property
    def action_space(self):
        #num_actions = self.initial_vehicles.num_rl_vehicles
        num_actions = len(self.k.vehicle.get_rl_ids())
        accel_ub = self.env_params.additional_params["max_accel"]
        accel_lb = - abs(self.env_params.additional_params["max_decel"])

        return Box(low=accel_lb,
                   high=accel_ub,
                   shape=(num_actions,))
    
    @property
    def observation_space(self):
        return Box(
            low=0,
            high=float("inf"),
            shape=(40*len(self.k.vehicle.get_ids()),),
        )
    
    def _apply_rl_actions(self, rl_actions):
        # the names of all autonomous (RL) vehicles in the network
        rl_ids = self.k.vehicle.get_rl_ids()

        # use the base environment method to convert actions into accelerations for the rl vehicles
        self.k.vehicle.apply_acceleration(rl_ids, rl_actions)
        
    
    def get_state(self, **kwargs):
        # the get_ids() method is used to get the names of all vehicles in the network
        ids = self.k.vehicle.get_ids()

        # we use the get_absolute_position method to get the positions of all vehicles
        pos = [self.k.vehicle.get_x_by_id(veh_id) for veh_id in ids]

        # we use the get_speed method to get the velocities of all vehicles
        vel = [self.k.vehicle.get_speed(veh_id) for veh_id in ids]

        # the speeds and positions are concatenated to produce the state
        return np.concatenate((pos, vel))
    
    def compute_reward(self, rl_actions, **kwargs):
        # the get_ids() method is used to get the names of all vehicles in the network
        ids = self.get_veh_ids()
        
        # we next get a list of the speeds of all vehicles in the network
        speeds = self.k.vehicle.get_speed(ids)
            
        # finally, we return the average of all these speeds as the reward
        return np.mean(speeds)
        
     
    