from typing import List, Literal, Tuple

from pydantic import BaseModel

### General Settings ###


class GameSettings(BaseModel):
    hand_length: int = 3
    num_digits: int = 3
    num_players: int = 3


### Training Settings ###


class RNaDConfig(BaseModel):
    batch_size: int = 256
    trajectory_max: int = 15
    policy_network_layers: Tuple[int, int] = (256, 256)


class TrainSettings(BaseModel):
    training_steps: int = 1_000_000
    checkpoint_frequency: int = 10_000
    rnad: RNaDConfig


class IOSettings(BaseModel):
    run_id: str = "test"
    load_checkpoint: str | None = None  # filename only; will look in save_dir/run_id/
    save_dir: str = "checkpoints/"


class TrainConfig(BaseModel):
    app_name: str
    version: float
    game: GameSettings
    train: TrainSettings
    io: IOSettings


### Best Response Evaluation Settings ###


class BestResponseNetworkSettings(BaseModel):
    batch_size: int = 32
    hidden_layers_sizes: List[int] = [64, 64, 64]
    replay_buffer_capacity: int = 100_000
    learning_rate: float = 0.1
    discount_factor: float = 0.99
    epsilon_start: float = 0.5
    epsilon_end: float = 0.1
    gradient_clipping: float = 1.0


class BestResponseTrainSettings(BaseModel):
    seed: int | None = None
    num_train_episodes: int = 1_000_000
    evaluate_every: int = 5000
    evaluate_num_episodes: int = 1000

    # rolling window captures this many eval train episodes,
    # ie the number of episodes in a window is rolling_window_size * evaluate_every
    rolling_window_size: int = 10

    dqn: BestResponseNetworkSettings


class BestResponseIOSettings(BaseModel):
    input_dir: str
    output_dir: str = (
        "best_response_output/"  # custom subdir using input_dir will be auto created
    )
    output_agent_filename: str = "best_response_agent_%d.pickle"
    log_file: str = "best_response_agent_%d.log"  # eval logs, will be in output_dir
    summary_file: str = (
        "summary.txt"  # output final BR agent's performance, will be in output_dir
    )


class BestResponseConfig(BaseModel):
    agent_step: int  # specify the checkpoint number, conforming with io.input_dir/agent_%d.pickle

    game: GameSettings
    train: BestResponseTrainSettings
    io: BestResponseIOSettings


### Play Interactive Settings ###


class PlayInteractiveConfig(BaseModel):
    agent_path: str
    agent_filename: str
    debug: bool = False
    output_dir: str = "play_output/interactive"


### Play Agents Settings


class PlayAgentsConfig(BaseModel):
    agent_path: str
    agent_filename: str
    output_dir: str = "play_output/agents"

    n_rounds: int = 1000
    player_names: List[str]
    player_types: List[Literal["agent", "llm", "baseline"]]

    open_ai_api_key: str | None = None
    open_ai_model: str = "o3"
