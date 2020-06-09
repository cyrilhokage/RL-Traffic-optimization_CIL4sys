
import numpy as np

def Customize_Callbacks(n_veh):

    def on_episode_start(info):
        episode = info["episode"]
        episode.user_data["accelerations"]  = []
        episode.user_data["speeds"]         = []
        episode.user_data["veh_wait_steps"] = []
        episode.user_data["CO2_emissions"]  = []

    def on_episode_step(info):
        episode = info["episode"]
        acceleration  = np.mean(episode.last_observation_for()[:n_veh])
        speed         = np.mean(episode.last_observation_for()[n_veh:2*n_veh])
        CO2_emission  = np.mean(episode.last_observation_for()[2*n_veh:3*n_veh])
        veh_wait_step = np.mean(episode.last_observation_for()[3*n_veh:4*n_veh])
        episode.user_data["accelerations"].append(acceleration)
        episode.user_data["speeds"].append(speed)
        episode.user_data["CO2_emissions"].append(CO2_emission)
        episode.user_data["veh_wait_steps"].append(veh_wait_step)

    def on_episode_end(info):
        episode = info["episode"]
        acceleration  = np.mean(episode.user_data["accelerations"])
        speed         = np.mean(episode.user_data["speeds"])
        CO2_emission  = np.mean(episode.user_data["CO2_emissions"])
        veh_wait_step = np.mean(episode.user_data["veh_wait_steps"])
        episode.custom_metrics["acceleration"]  = acceleration
        episode.custom_metrics["speed"]         = speed
        episode.custom_metrics["CO2_emission"]  = CO2_emission
        episode.custom_metrics["veh_wait_step"] = veh_wait_step


    MyCallbacks = {"on_episode_start": on_episode_start,
                "on_episode_step": on_episode_step,
                "on_episode_end" : on_episode_end}
    
    return MyCallbacks

