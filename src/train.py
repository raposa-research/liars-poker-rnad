import os
import re
import time

import cloudpickle
import jax
import numpy as np
from open_spiel.python.algorithms.rnad import rnad
from open_spiel.python.algorithms.rnad.rnad import RNaDConfig
from tqdm import trange

from config_schema import TrainConfig
from utils import dump_config, load_config


def checkpoint(agent, save_dir, training_step):
    if not os.path.isdir(save_dir):
        os.mkdir(save_dir)

    jax.clear_caches()

    output_file = save_dir + f"/agent_{training_step}.pickle"
    with open(output_file, "wb") as f:
        cloudpickle.dump(agent, f)


def overwrite_internal_config(
    agent, config, param_list, num_digits, hand_length, num_players
):
    # this function is used for forcing configuration changes after an agent has been created, such as
    # loaded checkpoints (otherwise, OpenSpiel uses the original configurations)
    # It is only intended for hyperparameter testing, so use it carefully

    # serialize agent state
    agent_state = agent.__getstate__()
    new_config = RNaDConfig(
        game_name="python_liars_poker(num_digits={},hand_length={},players={})".format(
            num_digits, hand_length, num_players
        ),
        **config,
    )
    agent_state["config"] = new_config

    # rebuild the agent object, resulting in updated optax optimizer function
    agent.__setstate__(agent_state)
    for param in param_list:
        print(f"set {param} in optimizer to", agent_state["config"][param])


def train(config: TrainConfig, save_dir: str):

    # set up agent
    prev_checkpoint = config.io.load_checkpoint
    if prev_checkpoint:
        m = re.search(r"agent_(\d+)\.pickle", prev_checkpoint)
        if m:
            last_step = int(m.group(1))
        else:
            raise RuntimeError(f"Unable to parse step from filename {prev_checkpoint}")

        with open(os.path.join(save_dir, prev_checkpoint), "rb") as f:
            agent = cloudpickle.load(f)
    else:
        last_step = -1
        rnad_config = config.train.rnad.model_dump()

        # Create new agent
        agent = rnad.RNaDSolver(
            rnad.RNaDConfig(
                game_name="python_liars_poker(num_digits={},hand_length={},players={})".format(
                    config.game.num_digits,
                    config.game.hand_length,
                    config.game.num_players,
                ),
                **rnad_config,
            )
        )

    losses = []
    step_times = []

    # training loop
    for step in trange(last_step + 1, last_step + config.train.training_steps + 1):
        start_time = time.time()
        logs = agent.step()
        step_end = time.time()

        losses.append(logs["loss"])
        step_times.append(step_end - start_time)

        if (
            step % config.train.checkpoint_frequency
            == config.train.checkpoint_frequency - 1
        ):
            mean_losses = np.mean(losses[-config.train.checkpoint_frequency :])
            mean_step_time = np.mean(step_times[-config.train.checkpoint_frequency :])
            print(
                f"Step: {step}; "
                f"Avg Loss: {mean_losses:.2f}; "
                f"Avg Step Time (sec): {mean_step_time:.2f}; "
                f"Est. Steps / Day: {int(60 * 60 * 24 / mean_step_time)}"
            )
            checkpoint(agent, save_dir, step)

    # Save final checkpoint
    print("Step: {}".format(step))
    checkpoint(agent, save_dir, step)


if __name__ == "__main__":
    config = load_config()

    # set up IO
    # unless loading a checkpoint, run_id must be new to avoid overwriting data
    save_dir = os.path.join(config.io.save_dir, config.io.run_id)

    if not os.path.isdir(save_dir):
        os.mkdir(save_dir)
    elif not config.io.load_checkpoint:
        raise IOError(
            "config.io.run_id must be unique to avoid accidental overwriting of checkpoints"
        )

    dump_config(config, save_dir)

    # initiate training
    train(config, save_dir)
