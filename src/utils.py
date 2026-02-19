import os
from datetime import datetime

import yaml
from pydantic import BaseModel

from config_schema import (
    BestResponseConfig,
    PlayAgentsConfig,
    PlayInteractiveConfig,
    TrainConfig,
)


def load_config(
    file_path: str = "../config.yaml", config_type: str = "train"
) -> BestResponseConfig | PlayAgentsConfig | PlayInteractiveConfig | TrainConfig:
    with open(file_path, "r") as f:
        raw_dict = yaml.safe_load(f)
        if config_type == "train":
            return TrainConfig(**raw_dict)
        if config_type == "best_response":
            return BestResponseConfig(**raw_dict)
        if config_type == "play_interactive":
            return PlayInteractiveConfig(**raw_dict)
        if config_type == "play_agents":
            return PlayAgentsConfig(**raw_dict)
        raise ValueError(f"config type {config_type} not recognized")


def dump_config(config: BaseModel, save_dir: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filepath = os.path.join(save_dir, f"config_log_{ts}.txt")
    with open(filepath, "w") as f:
        yaml.dump(config.model_dump(), f, sort_keys=False, indent=4)
    return ts
