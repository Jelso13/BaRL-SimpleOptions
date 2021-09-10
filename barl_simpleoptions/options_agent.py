import math
import random
import numpy as np

from copy import deepcopy
from typing import Hashable, List, Union

from barl_simpleoptions.option import Option
from barl_simpleoptions.environment import BaseEnvironment


class OptionAgent:
    """
    An agent which acts in a given environment, learning using the Macro-Q learning
    and intra-option learning algorithms.
    """

    def __init__(
        self,
        env: "BaseEnvironment",
        epsilon: float = 0.15,
        macro_alpha: float = 0.2,
        intra_option_alpha: float = 0.2,
        gamma: float = 0.9,
    ):
        """
        Constructs a new OptionAgent object.

        Arguments:
            env {Environment} -- The environment for the agent to act in.
            epsilon {float} -- The chance of the agent taking a random action when following its base policy.
            alpha {float} -- The learning rate used in the Macro-Q Learning updates.
            alpha {float} -- The learning rate used in the Intra-Option Learning updates.
            gamma {float} -- The environment's decay factor.
        """

        self.q_table = {}
        self.env = env
        self.epsilon = epsilon
        self.gamma = gamma
        self.macro_q_alpha = macro_alpha
        self.intra_option_alpha = intra_option_alpha
        self.executing_options = []
        self.executing_options_states = []
        self.executing_options_rewards = []

    def macro_q_learn(self, state_trajectory: List[Hashable], rewards: List[float], option: "Option") -> None:
        """
        Performs Macro Q-Learning updates along the given trajectory for the given Option.

        Args:
            state_trajectory (List[Hashable]): The list of states visited each time-step while the option was executing.
            rewards (List[float]): The list of rewards earned each time-step while the Option was executing.
            option (Option): The option to perform an update for.
        """
        state_trajectory = deepcopy(state_trajectory)
        rewards = deepcopy(rewards)
        option = deepcopy(option)

        termination_state = state_trajectory[-1]

        while len(state_trajectory) > 1:
            num_rewards = len(rewards)
            initiation_state = state_trajectory[0]

            old_value = self.q_table.get((hash(initiation_state), hash(option)), 0)

            # Compute discounted sum of rewards.
            discounted_sum_of_rewards = self._discounted_return(rewards, self.gamma)

            # Get Q-Values for Next State.
            if not self.env.is_state_terminal(termination_state):
                q_values = [
                    self.q_table.get((hash(termination_state), hash(o)), 0)
                    for o in self.env.get_available_options(termination_state)
                ]
            # Cater for terminal states (Q-value is zero).
            else:
                q_values.append(0)

            # Perform Macro-Q Update
            self.q_table[(hash(initiation_state), hash(option))] = old_value + self.macro_q_alpha * (
                discounted_sum_of_rewards + math.pow(self.gamma, len(rewards)) * max(q_values) - old_value
            )

            state_trajectory.pop(0)
            rewards.pop(0)

    def intra_option_learn(
        self, state_trajectory: List[Hashable], rewards: List[float], executed_option: "Option"
    ) -> None:
        """
        Performs Intra-Option Learning updates along the given trajectory for the given Option.

        Args:
            state_trajectory (List[Hashable]): The list of states visited each time-step while the option was executing.
            rewards (List[float]): The list of rewards earned each time-step while the Option was executing.
            option (Option): The option that was executed.
        """
        state_trajectory = deepcopy(state_trajectory)
        rewards = deepcopy(rewards)
        executed_option = deepcopy(executed_option)

        termination_state = state_trajectory[-1]

        while len(state_trajectory) > 1:
            num_rewards = len(rewards)
            initiation_state = state_trajectory[0]

            # We perform an intra-option update for all other options which select option in this state.
            for other_option in self.env.get_available_options(initiation_state):
                if other_option.initiation(initiation_state) and hash(executed_option.policy(initiation_state)) == hash(
                    executed_option
                ):

                    old_value = self.q_table.get((hash(initiation_state), hash(other_option)), 0)

                    # Compute discounted sum of rewards.
                    discounted_sum_of_rewards = self._discounted_return(rewards, self.gamma)

                    # If the option terminates, we consider the value of the next best option.
                    next_q_terminates = other_option.termination(termination_state) * max(
                        [
                            self.q_table.get((hash(termination_state), hash(o)), 0)
                            for o in self.env.get_available_options(termination_state)
                        ]
                    )
                    # If the option continues, we consider the value of the currently executing option.
                    next_q_continues = (1 - other_option.termination(termination_state)) * self.q_table.get(
                        (hash(termination_state), hash(other_option)), 0
                    )

                    # Perform Intra-Option Update.
                    self.q_table[
                        (hash(termination_state), hash(other_option))
                    ] = old_value + self.intra_option_alpha * (
                        discounted_sum_of_rewards
                        + math.pow(self.gamma, len(rewards)) * (next_q_continues + next_q_terminates)
                        - old_value
                    )

            state_trajectory.pop(0)
            rewards.pop(0)

    def select_action(self, state: Hashable) -> Union[Option, Hashable, None]:
        """
        Returns the selected option for the given state.

        Arguments:
            state {Hashable} -- The state in which to select an option.

        Returns:
            {Option, Hashable, None} -- Returns an Option, or a Primitive Action (as a Hashable).
        """

        # Select option from set of available options
        # Use epsilon greedy at lowest level, use option policy at higher levels.

        # If we do not currently have any options executing, we act according to the agent's
        # base epsilon-greedy policy over the set of currently available options.
        if len(self.executing_options) == 0:
            available_options = self.env.get_available_options(state)

            # Random Action.
            if random.random() < self.epsilon:
                return random.choice(available_options)
            # Best Action.
            else:
                # Find Q-values of available options.
                q_values = [self.q_table.get((hash(state), hash(o)), 0) for o in available_options]

                # Return the option with the highest Q-value, breaking ties randomly.
                return available_options[
                    random.choice(idx for idx, q_value in enumerate(q_values) if q_value == max(q_values))
                ]
        # If we are currently following an option's policy, return what it selects.
        else:
            return self.executing_options[-1].policy(state)

    def run_agent(self, num_episodes: int) -> List[float]:
        """
        Trains the agent for a given number of episodes.

        Args:
            num_episodes (int): The number of episodes to train the agent for.

        Returns:
            List[float]: A list containing floats representing
        """
        episode_rewards = [[] for __ in range(num_episodes)]

        for episode in range(num_episodes):
            # Initialise initial state variables.
            state = self.env.reset()
            terminal = False

            while not terminal:
                selected_option = self.select_action(state)

                # Handle if the selected option is a higher-level option.
                if isinstance(selected_option, Option):
                    self.executing_options.append(deepcopy(selected_option))
                    self.executing_options_states.append([deepcopy(state)])
                    self.executing_options_rewards.append([])

                # Handle if the selected option is a primitive action.
                else:
                    next_state, reward, terminal, __ = self.env.step(selected_option)

                    state = deepcopy(next_state)
                    episode_rewards[episode].append(reward)

                    for i in range(len(self.executing_options)):
                        self.executing_options_states[i].append(deepcopy(next_state))
                        self.executing_options_rewards[i].append(reward)

                    # Terminate any options which need terminating this time-step.
                    while self._roll_termination(self.executing_options[-1], next_state):
                        # Perform a macro-q learning update for the terminating option.
                        self.macro_q_learn(
                            self.executing_options_states[-1],
                            self.executing_options_rewards[-1],
                            self.executing_options[-1],
                        )
                        # Perform an intra-option learning update for the terminating option.
                        self.intra_option_learn(
                            self.executing_options_states[-1],
                            self.executing_options_rewards[-1],
                            self.executing_options[-1],
                        )
                        self.executing_options_states.pop()
                        self.executing_options_rewards.pop()
                        self.executing_options.pop()

                # Handle if the current state is terminal.
                if terminal:
                    while len(self.executing_options) > 0:
                        # Perform a macro-q learning update for the topmost option.
                        self.macro_q_learn(
                            self.executing_options_states[-1],
                            self.executing_options_rewards[-1],
                            self.executing_options[-1],
                        )
                        # Perform an intra-option learning update for the topmost option.
                        self.intra_option_learn(
                            self.executing_options_states[-1],
                            self.executing_options_rewards[-1],
                            self.executing_options[-1],
                        )
                        self.executing_options_states.pop()
                        self.executing_options_rewards.pop()
                        self.executing_options.pop()
        return episode_rewards

    def _discounted_return(self, rewards: List[float], gamma: float) -> float:
        # Computes the discounted reward given an ordered list of rewards, and a discount factor.
        num_rewards = len(rewards)

        # Fill an array with gamma^index for index = 0 to index = num_rewards - 1.
        gamma_exp = np.power(np.full(num_rewards, gamma), np.arange(0, num_rewards))

        # Element-wise multiply and then sum array.
        discounted_sum_of_rewards = np.sum(np.multiply(rewards, gamma_exp))

        return discounted_sum_of_rewards

    def _roll_termination(self, option: "Option", state: Hashable):
        # Rolls on whether or not the given option terminates in the given state.
        # Will work with stochastic and deterministic termination functions.
        if random.random() > option.termination(state):
            return False
        else:
            return True