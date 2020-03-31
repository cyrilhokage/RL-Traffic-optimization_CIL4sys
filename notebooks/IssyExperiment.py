import json

from flow.core.params import VehicleParams
from flow.core.params import NetParams
from flow.core.params import InitialConfig
from flow.core.params import EnvParams
from flow.core.params import SumoParams
from flow.utils.rllib import FlowParamsEncoder

import ray
try:
    from ray.rllib.agents.agent import get_agent_class
except ImportError:
    from ray.rllib.agents.registry import get_agent_class
from ray.tune import run_experiments
from ray.tune.registry import register_env

from helpers import make_create_env, get_inflow


class RayClusterParams:
    """"Parameters for the ray cluster."""

    def __init__(self, use_cluster, redis_address):
        """ Instantiate an experiment parameter object.
        Parameters
        ----------
        use_cluster: bool
            Should the experiment run on a cluster.
        redis_address: string
            IP and port of the ray cluster head node ("<IP>:<PORT>")
        """
        self.use_cluster = use_cluster
        self.redis_address = redis_address


class IssyExperimentParams:
    """Parameters for the Issy RL experiment.
    This class is used configure the experiment.
    """

    def __init__(
            self,
            horizon,
            rollouts,
            inflow_spec,
            action_spec,
            n_cpus,
            n_veh,
            cluster_params,
            checkpoint_freq=20,
            training_iteration=200,
            discount_rate=0.999,
            env_name='IssyEnv1',
            algorithm='PPO',
            warmup_steps=750,
            render=False,
            tl_constraint=100,
            sim_step=0.1,
            osm_path='/Users/adrienly/Documents/Telecom/Cil4Sys/CIL4SYS/flow/issy.osm'
    ):
        """Instantiate an experiment parameter object.
        Parameters
        ----------
        horizon: int
            How many steps per rollouts.
        rollouts: int
            How many rollouts are performed at each timesteps.
            From the Flow paper:
            "To accumulate samples, we must be able torolloutthe policy for T
             timesteps. Each iteration, samples are aggregated from multiple
            rollouts into a batch and the resulting gradient is used to update
            the policy."
            https://flow-project.github.io/papers/Flow_Deep_Reinforcement_Learning_for_Control_in_SUMO.pdf
        inflow_spec: dict
            Dictionary defining how to setup the experiment inflows.
            See `helpers.get_inflow` docstring for more information.
        action_spec: dict
            Dictionary defining allowed states for a given traffic light ID.
            - keys: (str) the traffic light ID
            - values: (Array<str>) acceptable states for that traffic light ID.
        n_cpus: int
            How many cpus to request for parallel training.
        n_veh: int
            How many vehicules are on the mesh at the start of the rollout.
        cluster_params: RayClusterParams
            Parameters for the ray cluster to run the experiment on. See
            `RayClusterParams.init` docstring for more information.
        checkpoint_freq: int
            Number of simulations between model checkpoint saves.
        training_iteration: int
            How many simulations the agent is trained for.
        discount_rate: float
            Reward discount rate.
        env_name: str
            Name of environment class in the file `IssyEnv` that inherits
            `IssyEnvAbstract`.
        algorithm: str
            RLlib algorithm name ('PPO', 'DQN', etc).
            See: https://ray.readthedocs.io/en/latest/rllib-env.html
        warmup_steps: int
            Number of steps performed before the initialization of training
            during a rollout. These warmup steps are not added as steps
            into training, and the actions of rl agents during these steps
            are dictated by sumo. Defaults to zero
            Copied from: `flow.core.params.EnvParams.warup_steps` docstring.
        render: boolean
            Should sumo-gui be launched during training.
        tl_constraint: [Int, Int]
            Array of 2 ints, the first one stipulating the minimum number of
            timesteps tl has to remain in same state and the second one the
            maximum number of timesteps a tl can remain in the same state,
            after which, the simulator will randomly choose a new state.
        sim_step: float
            Number of seconds between steps on simulator (Sumo in our case)
        osm_path: str
            Path to the .osm file of the district to simulate.
        Returns
        -------
        An instance of IssyExperimentParams with the parameters as keys with
        the following additions:
        edge_distribution: str
            Edges to add inflows to.
        """
        self.horizon = horizon
        self.rollouts = rollouts
        self.n_cpus = n_cpus
        self.inflow_spec = inflow_spec
        self.action_spec = action_spec
        self.n_veh = n_veh
        self.checkpoint_freq = checkpoint_freq
        self.training_iteration = training_iteration
        self.algorithm = algorithm
        self.env_name = env_name
        self.discount_rate = discount_rate
        self.render = render
        self.warmup_steps = warmup_steps
        self.cluster_params = cluster_params
        self.tl_constraint = tl_constraint
        self.sim_step = sim_step

        self.osm_path = osm_path
        self.edges_distribution = list(inflow_spec.keys())


class IssyExperiment:
    """Issy experiment class, it sets up paramaters necessary to setup a flow
    experiment with RLlib."""

    def __init__(self, params):
        """Setup experiment parameters and initialize ray.
        Parameters
        ----------
        params: IssyExperimentParams
           See IssyExperimentParams class definition
        """
        self.exp_params = params
        self.flow_params = self.make_flow_params()

        # Configure init for cluster use if requested
        if self.exp_params.cluster_params.use_cluster:
            ray.init(
                redis_address=self.exp_params.cluster_params.redis_address)
        else:
            ray.init(num_cpus=self.exp_params.n_cpus + 1)

    def run(self):
        """Runs the experiment according to the constructor input
        parameters."""
        alg_run, gym_name, config = 1, 1, 1  # placeholders
        if self.exp_params.algorithm == 'PPO':
            alg_run, gym_name, config = self.setup_ppo_exp()
        elif self.exp_params.algorithm == 'DQN':
            alg_run, gym_name, config = self.setup_dqn_exp()
        else:
            return NotImplementedError

        run_experiments({
            self.flow_params['exp_tag']: {
                'run': alg_run,
                'env': gym_name,
                'config': {
                    **config
                },
                'checkpoint_freq': self.exp_params.checkpoint_freq,
                'max_failures': 999,
                'stop': {
                    'training_iteration': self.exp_params.training_iteration,
                },
            }
        })

    def setup_dqn_exp(self):
        """Configures RLlib DQN algorithm to be used to train the RL model."""

        alg_run = 'DQN'

        agent_cls = get_agent_class(alg_run)
        config = agent_cls._default_config.copy()
        config['num_workers'] = self.exp_params.n_cpus
        config['train_batch_size'] = self.exp_params.horizon * \
            self.exp_params.rollouts
        config['gamma'] = self.exp_params.discount_rate
        config['model'].update({'fcnet_hiddens': [32, 32]})
        config['clip_actions'] = False  # FIXME(ev) temporary ray bug
        config['horizon'] = self.exp_params.horizon
        config["hiddens"] = [256]

        # save the flow params for replay
        flow_json = json.dumps(self.flow_params,
                               cls=FlowParamsEncoder,
                               sort_keys=True,
                               indent=4)
        config['env_config']['flow_params'] = flow_json
        config['env_config']['run'] = alg_run

        create_env, gym_name = make_create_env(params=self.flow_params,
                                               version=0)

        # Register as rllib env
        register_env(gym_name, create_env)
        return alg_run, gym_name, config

    def setup_ppo_exp(self):
        """Configures RLlib PPO algorithm to be used to train the RL model.
        See: https://ray.readthedocs.io/en/latest/rllib-algorithms.html#proximal-policy-optimization-ppo"""

        alg_run = 'PPO'

        agent_cls = get_agent_class(alg_run)
        config = agent_cls._default_config.copy()
        config['num_workers'] = self.exp_params.n_cpus
        config['train_batch_size'] = self.exp_params.horizon * \
            self.exp_params.rollouts
        config['gamma'] = self.exp_params.discount_rate
        config['model'].update({'fcnet_hiddens': [32, 32]})
        config['use_gae'] = True
        config['lambda'] = 0.97
        config['kl_target'] = 0.02
        config['num_sgd_iter'] = 10
        config['clip_actions'] = False  # FIXME(ev) temporary ray bug
        config['horizon'] = self.exp_params.horizon

        # save the flow params for replay
        flow_json = json.dumps(self.flow_params,
                               cls=FlowParamsEncoder,
                               sort_keys=True,
                               indent=4)
        config['env_config']['flow_params'] = flow_json
        config['env_config']['run'] = alg_run

        create_env, gym_name = make_create_env(params=self.flow_params,
                                               version=0)

        # Register as rllib env
        register_env(gym_name, create_env)
        return alg_run, gym_name, config

    def make_flow_params(self):
        """Configures Flow simulation parameters.
        Returns
        -------
        A dictionary containing all necessary parameters for the Flow
        simulation to take place."""
        return dict(
            exp_tag='IssyEnv',
            env_name=self.exp_params.env_name,
            scenario='IssyScenario',
            simulator='traci',
            sim=self.make_sumo_params(),
            env=self.make_env_params(),
            net=self.make_net_params(),
            veh=self.make_vehicles(),
            initial=self.make_initial_config(),
        )

    def make_inflow(self):
        """Configure simulation inflows.
        Returns
        -------
        An inflow object to be used to inject cars into the simulation.
        See `helpers.get_inflows` for more information.
        """
        return get_inflow(self.exp_params.inflow_spec)

    def make_vehicles(self):
        """Defines the number of human controlled cars on the mesh at time step 0.
        Returns
        -------
        A VehicleParams object defining human controlled vehicles
        """
        vehicles = VehicleParams()
        vehicles.add('human', num_vehicles=self.exp_params.n_veh)
        return vehicles

    def make_net_params(self):
        """Configures the network network.
        Returns
        -------
        A NetParams object loading the OSM map with the appropriate inflow
        object.
        """
        return NetParams(
            osm_path=self.exp_params.osm_path,
           # no_internal_links=False,
            inflows=self.make_inflow(),
        )

    def make_initial_config(self):
        """Configures the simulation's edge distribution.
        Returns
        -------
        An InitialConfig object loading the network edges distribution.
        """
        return InitialConfig(
            edges_distribution=self.exp_params.edges_distribution, )

    def make_env_params(self):
        """Configures the environment parameters.
        Returns
        -------
        An EnvParams object with the correct parameters and
        additional env params.
        """
        return EnvParams(
            additional_params={
                "beta": self.exp_params.n_veh,
                "action_spec": self.exp_params.action_spec,
                "algorithm": self.exp_params.algorithm,
                "tl_constraint_min": self.exp_params.tl_constraint[0],
                "tl_constraint_max": self.exp_params.tl_constraint[1],
                "sim_step": self.exp_params.sim_step,
            },
            horizon=self.exp_params.horizon,
            warmup_steps=self.exp_params.warmup_steps,
        )

    def make_sumo_params(self):
        """Configures the Sumo simulator.
        Returns
        -------
        A SumoParams object. In particular it configures the "restart_instance"
        parameter as recommended by the Flow documentation when using inflows.
        See `flow.envs.base_env.reset` docstring for more information.
        """
        return SumoParams(render=self.exp_params.render,
                          restart_instance=True,
                          sim_step=self.exp_params.sim_step)