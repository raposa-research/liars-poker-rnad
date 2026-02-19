import json
import os
import pickle
from datetime import datetime

import cloudpickle
import numpy as np
import pyspiel
from open_spiel.python import rl_agent, rl_environment
from open_spiel.python.algorithms.rnad import rnad
from open_spiel.python.jax import dqn
from tqdm import trange

from best_response_output import BR_HEADER
from utils import dump_config, load_config


def create_training_agents(game, num_players, dqn_config):
    return [
        dqn.DQN(
            player_id=idx,
            state_representation_size=(game.information_state_tensor_shape()[0]),
            num_actions=game.num_distinct_actions(),
            **dqn_config,
        )
        for idx in range(num_players)
    ]


def get_action(rng, agent, env, time_step, is_evaluation=False):
    if isinstance(agent, rl_agent.AbstractAgent):
        return agent.step(time_step, is_evaluation=is_evaluation).action
    elif isinstance(agent, rnad.RNaDSolver):
        action_probs = agent.action_probabilities(env.get_state)
        return rng.choice(list(action_probs.keys()), p=list(action_probs.values()))
    else:
        raise RuntimeError("unknown agent type")


def eval_against_fixed_bots(rng, env, trained_agents, fixed_agents, num_episodes):
    """Evaluates `trained_agents` against `fixed_agents` for `num_episodes`."""
    num_players = len(fixed_agents)
    sum_episode_rewards = np.zeros(num_players)
    for player_pos in range(num_players):
        cur_agents = fixed_agents[:]
        cur_agents[player_pos] = trained_agents[player_pos]
        for _ in range(num_episodes):
            time_step = env.reset()
            episode_rewards = 0
            turn_num = 0
            while not time_step.last():
                turn_num += 1
                player_id = time_step.observations["current_player"]
                if env.is_turn_based:
                    action_list = [
                        get_action(
                            rng,
                            cur_agents[player_id],
                            env,
                            time_step,
                            is_evaluation=True,
                        )
                    ]
                else:
                    action_list = [
                        get_action(agent, env, time_step, is_evaluation=True)
                        for agent in cur_agents
                    ]
                time_step = env.step(action_list)
                episode_rewards += time_step.rewards[
                    player_pos
                ]  # grab the rewards for only the exploiting agent
            sum_episode_rewards[player_pos] += episode_rewards
    return sum_episode_rewards / num_episodes


class RollingAverage(object):
    """Class to store a rolling average."""

    def __init__(self, size=100):
        self._size = size
        self._values = np.array([0] * self._size, dtype=np.float64)
        self._index = 0
        self._total_additions = 0

    def add(self, value):
        self._values[self._index] = value
        self._total_additions += 1
        self._index = (self._index + 1) % self._size

    def mean(self):
        n = min(self._size, self._total_additions)
        if n == 0:
            return 0
        return self._values.sum() / n

    def stdev(self):
        n = min(self._size, self._total_additions)
        if n == 0:
            return 0
        return np.std(self._values[0:n])


def train(
    config,
    save_dir,
    log,
    summary_file,
):
    """
    :param config: read from config_br.yaml
    :param save_dir: path to save logs, summary, and final BR agent
    :param log: open file for writing training logs
    :param summary_file: open file for final agent's performance
    """

    rng = np.random.default_rng(seed=config.train.seed)

    # Load Liar's Poker Game

    game = pyspiel.load_game(
        "python_liars_poker",
        {
            "players": config.game.num_players,
            "num_digits": config.game.num_digits,
            "hand_length": config.game.hand_length,
        },
    )
    env = rl_environment.Environment(game, include_full_state=True)
    num_players = config.game.num_players

    saved_agent_path = os.path.join(
        config.io.input_dir, f"agent_{config.agent_step}.pickle"
    )
    if not os.path.isfile(saved_agent_path):
        raise ValueError(f"Unable to find checkpoint at {saved_agent_path}")

    # Load agents from checkpoint
    print("loading agent from: %s" % saved_agent_path)
    exploitee_agents = []
    for idx in range(num_players):
        with open(saved_agent_path, "rb") as f:
            exploitee_agents.append(pickle.load(f))

    # Create DQN best response agents
    learning_agents = create_training_agents(
        game, num_players, config.train.dqn.model_dump()
    )

    # we train all permutations of players
    # each permutation has one best response agent and (num_players - 1) Liar's Poker agents
    all_agents = [
        [
            learning_agents[j] if i == j else exploitee_agents[j]
            for j in range(num_players)
        ]
        for i in range(num_players)
    ]

    # TODO rewrite to handle more than 4 players
    rolling_window_size = config.train.rolling_window_size
    rolling_averager = RollingAverage(rolling_window_size)
    rolling_averager_p0 = RollingAverage(rolling_window_size)
    rolling_averager_p1 = RollingAverage(rolling_window_size)
    if num_players > 2:
        rolling_averager_p2 = RollingAverage(rolling_window_size)
    if num_players > 3:
        rolling_averager_p3 = RollingAverage(rolling_window_size)
    total_value = 0
    total_value_n = 0

    print("Training DQN agent...")
    start_time = datetime.now()
    for ep in trange(config.train.num_train_episodes):
        if (ep + 1) % config.train.evaluate_every == 0:
            r_mean = eval_against_fixed_bots(
                rng,
                env,
                learning_agents,
                exploitee_agents,
                config.train.evaluate_num_episodes,
            )
            value = sum(r_mean)

            rolling_averager.add(value / num_players)
            rolling_averager_p0.add(r_mean[0])
            rolling_averager_p1.add(r_mean[1])
            rolling_value = rolling_averager.mean()
            rolling_value_p0 = rolling_averager_p0.mean()
            rolling_value_p1 = rolling_averager_p1.mean()
            rolling_std = rolling_averager.stdev()
            rolling_std_p0 = rolling_averager_p0.stdev()
            rolling_std_p1 = rolling_averager_p1.stdev()
            if num_players > 2:
                rolling_averager_p2.add(r_mean[2])
                rolling_value_p2 = rolling_averager_p2.mean()
                rolling_std_p2 = rolling_averager_p2.stdev()
            if num_players > 3:
                rolling_averager_p3.add(r_mean[3])
                rolling_value_p3 = rolling_averager_p3.mean()
                rolling_std_p3 = rolling_averager_p3.stdev()

            total_value += value
            total_value_n += 1
            avg_value = total_value / total_value_n / num_players

            log_values = {
                "epoch": ep,
                "mean_rewards_p0": r_mean[0],
                "mean_rewards_p1": r_mean[1],
                "eval_avg_value": value / num_players,
                "rolling_value_p0": rolling_value_p0,
                "rolling_value_p1": rolling_value_p1,
                "rolling_std_p0": rolling_std_p0,
                "rolling_std_p1": rolling_std_p1,
                "rolling_avg_value": rolling_value,
                "rolling_avg_std": rolling_std,
                "total_avg_value": avg_value,
            }
            if num_players > 2:
                log_values.update(
                    {
                        "mean_rewards_p2": r_mean[2],
                        "rolling_value_p2": rolling_value_p2,
                        "rolling_std_p2": rolling_std_p2,
                    }
                )
            if num_players > 3:
                log_values.update(
                    {
                        "mean_rewards_p3": r_mean[3],
                        "rolling_value_p3": rolling_value_p3,
                        "rolling_std_p3": rolling_std_p3,
                    }
                )
            log.write(json.dumps(log_values) + "\n")

            print(
                f"[{ep + 1}] Mean episode rewards {r_mean}, "
                f"avg_value: {value / num_players:.2f}, "
                f"total_avg_value: {avg_value:.2f}, "
                f"rolling_avg_value: {rolling_value:.2f}, "
                f"rolling_std: {rolling_std:.4f}"
            )

        for agents in all_agents:
            time_step = env.reset()
            while not time_step.last():
                player_id = time_step.observations["current_player"]
                if env.is_turn_based:
                    action_list = [get_action(rng, agents[player_id], env, time_step)]
                else:
                    action_list = [
                        get_action(rng, agent, env, time_step) for agent in agents
                    ]
                time_step = env.step(action_list)

            # Episode is over, step all DQN agents with final info state.
            for agent in agents:
                if isinstance(agent, rl_agent.AbstractAgent):
                    agent.step(time_step)

    end_time = datetime.now()
    runtime_in_hours = (end_time - start_time).total_seconds() / 3600

    print("appending to summary file")

    # TODO update to handle more than 3 players
    if num_players == 2:
        summary_file.write(
            "%s,%d,%d,%d,%d,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.2f,%d,%.4f,%.4f,%.4f,%.4f\n"
            % (
                saved_agent_path,
                config.agent_step,
                config.train.num_train_episodes,
                config.train.evaluate_every,
                config.train.evaluate_num_episodes,
                config.train.rolling_window_size,
                config.train.dqn.learning_rate,
                rolling_value,
                avg_value,
                rolling_value_p0,
                rolling_value_p1,
                -1,
                runtime_in_hours,
                config.train.dqn.replay_buffer_capacity,
                rolling_std,
                rolling_std_p0,
                rolling_std_p1,
                -1,
            )
        )

    elif num_players == 3:
        summary_file.write(
            "%s,%d,%d,%d,%d,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.2f,%d,%.4f,%.4f,%.4f,%.4f\n"
            % (
                saved_agent_path,
                config.agent_step,
                config.train.num_train_episodes,
                config.train.evaluate_every,
                config.train.evaluate_num_episodes,
                config.train.rolling_window_size,
                config.train.dqn.learning_rate,
                rolling_value,
                avg_value,
                rolling_value_p0,
                rolling_value_p1,
                rolling_value_p2,
                runtime_in_hours,
                config.train.dqn.replay_buffer_capacity,
                rolling_std,
                rolling_std_p0,
                rolling_std_p1,
                rolling_std_p2,
            )
        )

    output_agent_path = os.path.join(
        save_dir, config.io.output_agent_filename % config.agent_step
    )
    print("writing %s to: %s" % (str(learning_agents[0]), output_agent_path))
    with open(output_agent_path, "wb") as f:
        cloudpickle.dump(learning_agents[0], f)


if __name__ == "__main__":
    config = load_config("../config_br.yaml", config_type="best_response")

    # set up IO
    save_dir = os.path.join(config.io.output_dir, config.io.input_dir.replace("/", "_"))
    if not os.path.isdir(save_dir):
        os.mkdir(save_dir)

    dump_config(config, save_dir)

    # log is specific to this agent checkpoint
    log = open(os.path.join(save_dir, config.io.log_file % config.agent_step), "w")

    # summary file keeps track of the results across various agent_steps
    summary_file_path = os.path.join(save_dir, config.io.summary_file)
    add_header = not os.path.isfile(summary_file_path)

    summary = open(summary_file_path, "a")
    if add_header:
        summary.write(BR_HEADER + "\n")

    # initiate training
    train(config, save_dir, log, summary)
