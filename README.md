# Liar's Poker R-NaD

Liar's Poker is a popular Wall Street game played with digits. It combines statistical reasoning
with decision making under uncertainty. This repository provides source code to train AI agents to play
the game, a framework for evaluating their performance, and two play modes, automated and interactive.


This project utilizes an updated fork of OpenSpiel v1.5 
specifically patched to support macOS (Intel/Apple Silicon) and Linux 
using modern pybind11 (v3.0+) and **Python 3.11+**.

## Architecture

This setup uses two repos:
1.  **OpenSpiel Fork**: Contains the C++ engine and the Python bindings. It is based on OpenSpiel v1.5.
2.  **Liar's Poker R-NaD**: Training agents, evaluation, and interactive play.

You will need both, as the upstream OpenSpiel's dependencies are out of sync 
with the version of the library that contains Liar's Poker.

---

## Installation & Quickstart

### 1. Prerequisites
Ensure you have a C++ compiler (Clang or GCC) and `uv` installed.
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone the Repositories

Make sure you run these in the same directory for the downstream steps to work.

```bash
# Clone the modernized engine fork
git clone https://github.com/raposa-research/open_spiel

# Clone this project
git clone https://github.com/raposa-research/liars-poker-rnad
````

### 3. Build OpenSpiel

OpenSpiel installs a number of important dependencies in this step.
Run the install script in the top directory of `open_spiel`. 

```bash
cd /path/to/cloned/open_spiel
./install.sh
```

### 4. Build the virtual env

We have tested this code using python 3.11. To use that version, we recommend
installing it with `pyenv`. 

```bash
cd /path/to/cloned/liars-poker-rnad

# Install the latest 3.11 release
pyenv install 3.11

# Set it as the local version for this folder
pyenv local 3.11

# Verify that, in this directory, 3.11 is the linked version of python
python --version
# Should output: Python 3.11.x
```

The following should create your virtual environment and install all dependencies, including the one
you installed in ``../open_spiel``

```bash
cd /path/to/cloned/liars-poker-rnad
uv sync

```

### 5. Verify install

Run this command from your directory to ensure that `pyspiel` is working correctly.

```bash
uv run python -c "import pyspiel; game = pyspiel.load_game('tic_tac_toe'); print(f'Success! Loaded: {game.get_type().short_name}')"
```


## Training

To train an agent to play Liar's Poker, update the `config.yaml` with your local preferences.
You can set the game size, MLP architecture, and IO paths there.

If your training is ever disrupted, you can restart at an existing checkpoint by providing 
`config.yaml` with the filename of the checkpoint:

```python
run_id = "my_run_name"
load_checkpoint = "agent_9999.pickle"
save_dir = "checkpoints/"
```

The above will search for and load the agent saved at `checkpoints/my_run_name/agent_9999.pickle`.
A null value for load_checkpoint will create an agent trained from scratch.

In either case, you can run the training using the following command:

```bash
uv run train.py
```

## Best Response Evaluation

Configure the best response (BR) training with the `config_br.yaml` file.
Check the paths to make sure you are pointing to an existing Liar's Poker agent binary file.

Run the BR process using the following command:

```bash
uv run best_response_rl_multiplayer.py
```

The code presently fully supports best response training for up to a 3-player game. You can get total stats for a game 
with more players, but position-level data is limited to 3 players at this time. 

You will see the following outputs in your save directory:
* config_log_DATETIME.txt: this is a dump of your configurations read from file at the time of running
* best_response_agent_<step>.log: this is the best response training log in JSON format for the checkpoint specified in the name
* summary.txt: All checkpoints processed by BR will be included in this file; position-level data is limited to the first 3 players

The most important metrics to track in `summary.txt` are the `rolling_window` ones. `rolling_avg_value` is the average
BR score (avg equity per round) across all player positions. `rolling_std` is the standard deviation of that 
BR score.

## Automated Play

Automated play mode simulates agents/models playing against each other. We currently support three model types:
- Liar's Poker agents, which are created through the `train.py` file
- Baseline models, which use pure binomial probability policies and employ a greedy strategy
- Large Language Models, specifically those of OpenAI. You will need an API key for this.

You can play any combination of these model types, up to 3 players. If using a Liar's Poker agent, 
the number of players and game size (3x3, etc.) are fixed to what the agent was trained on. 

To start automated play mode, confirm your configs and run the script:

```bash
uv run play_agents.py
```

The logs contain a comprehensive, step-by-step output of each round, cumulative 
results, and other useful information.

## Interactive Play

Interactive play mode allows you to engage in a real-life scenario playing against real opponents.
The interactive game flow is highly manual to ensure realistic play; 
* the Liar's Poker agent does not know the opponent's hands, 
* you will have to provide your opponent(s) with their hands in advance,
* agent hands are entered manually as they are intended to be read off of physical printouts,
* and the full hands of opponents are not known by the agent, just the counts.

Opponent (human) counts are entered manually by you at the end of each round.

Configure interactive play using the `config_play_interactive.yaml` file. This is important
for ensuring your game is captured in the log file. `debug` mode allows you to see the agent's policy
for allowed moves prior to each decision point. 

Currently, we only support playing against 1 AI agent. 

To enter into interactive play mode, confirm your configs and run the script:

```bash
uv run play_interactive.py
```