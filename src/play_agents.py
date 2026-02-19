import datetime
import os
import re

import cloudpickle
import pyspiel
from numpy.random import default_rng
from openai import OpenAI

from config_schema import PlayAgentsConfig
from setup_logs import get_logger

rng = default_rng()
from baseline import BaselineModel
from llm_inputs import (
    instructions_reminder,
    liars_poker_instructions_2players,
    liars_poker_instructions_3players,
    liars_poker_rules,
)
from utils import dump_config, load_config


class Round:
    def __init__(
        self,
        round_num,
        hand_length,
        n_digits,
        n_players,
        player_names,
        player_types,
        starting_player_ix,
        announcements,
        game,
        agent,
        slips,
        llm_model,
        llm_clients,
        llm_last_response_ids,
        file_ptr,
    ):
        self.agent = agent

        self.round_num = round_num
        self.hand_length = hand_length
        self.n_digits = n_digits
        self.n_players = n_players
        self.player_names = player_names
        self.player_types = player_types
        self.player_rewards = {player: None for player in self.player_names}

        self.masked_names = ["Player%d" % (x + 1) for x in range(self.n_players)]
        self.player_order, self.player_names_ordered = self.calculate_player_order(
            starting_player_ix
        )
        self.starting_player_ix = starting_player_ix
        self.current_player_ix = starting_player_ix
        self.current_player_name = player_names[starting_player_ix]
        self.announcements = announcements
        self.hands = [slips[name][self.round_num - 1] for name in self.player_names]
        self.hands_ordered = [
            slips[name][self.round_num - 1] for name in self.player_names_ordered
        ]
        self.player_counts = []

        self.file_ptr = file_ptr
        self.llm_model = llm_model
        self.llm_clients = llm_clients
        self.llm_last_response_ids = llm_last_response_ids

        self.state = self.create_new_game_state(game, self.hands_ordered)

        self.last_bidder = ""
        self.last_bid = ""
        self.bid_history = []
        self.result = ""
        self.total_counts = ""
        self.traj_length = 0

        self.baseline_player = BaselineModel(
            self.hand_length, self.n_digits, self.n_players
        )

    def calculate_player_order(self, start_ix):
        player_order = [(x + start_ix) % self.n_players for x in range(self.n_players)]
        return player_order, [self.player_names[x] for x in player_order]

    def generate_hands_list(self, slips):
        return [slips[name][self.round_num - 1] for name in self.player_names_ordered]

    def print_round_status(self):
        log.info(
            "\n".join(
                [
                    f"LLM Model:{self.llm_model}",
                    f"Round: {self.round_num}",
                    f"Trajectory length: {self.traj_length}",
                    f"Last bidder: {self.last_bidder}",
                    f"Last bid: {self.last_bid}",
                    f"Current player: {self.current_player_name} (ix={self.current_player_ix})",
                ]
            )
        )

    def get_hand_type(self, hand, hand_length):
        # only implemented for 3x3 2-player and 3-player for now
        if self.n_players == 3 and hand_length == 3:
            set_len = len(set(hand))
            if set_len == hand_length:
                return "1 of each"
            else:
                return "%d of a kind" % (hand_length + 1 - set_len)
        elif self.n_players == 2 and hand_length == 3:
            set_len = len(set(hand))
            if set_len == hand_length:
                return "1 of each"
            else:
                return "%d of a kind" % (hand_length + 1 - set_len)
        else:
            return "unknown"

    def categorize_last_move(self, player_ix, hand, last_bid_count, last_bid_digit):
        hand_digit_count = sum([1 if int(s) == last_bid_digit else 0 for s in hand])
        count_diff = last_bid_count - hand_digit_count
        return (
            "%d bid" % count_diff
            if self.player_names[player_ix] == self.last_bidder
            else "%d challenge" % -count_diff
        )

    def write_round_stats(self, header=False):
        bid_count, bid_digit = [int(x) for x in self.last_bid.split(" of ")]
        if header:
            log.info(
                "round_num,position,player,player_type,hand,hand_type,reward,is_last_bidder,last_move_type\n"
            )
        for ix in range(self.n_players):
            player = self.player_names[ix]
            last_move_type = self.categorize_last_move(
                ix, self.hands[ix], bid_count, bid_digit
            )
            log.info(
                "%d,%d,%s,%s,%s,%s,%d,%s,%s\n"
                % (
                    self.round_num,
                    (self.player_order[ix] + 1),
                    player,
                    self.player_types[ix],
                    self.hands[ix],
                    self.get_hand_type(self.hands[ix], self.hand_length),
                    self.player_rewards[self.player_names[ix]],
                    "yes" if self.last_bidder == player else "no",
                    last_move_type,
                )
            )

    def create_new_game_state(self, game, hands_list):
        state = game.new_initial_state()

        for ix in range(self.hand_length):
            for hand in hands_list:
                state.apply_action(int(hand[ix]))

        return state

    def submit_prompt(self, prompt, player_name):
        log.info("PROMPT TO %s: %s" % (player_name, prompt[:500]))

        response = self.llm_clients[player_name].responses.create(
            model=self.llm_model,
            input=prompt,
            previous_response_id=self.llm_last_response_ids[player_name],
        )
        self.llm_last_response_ids[player_name] = response.id
        return response

    @staticmethod
    def parse_digit_count(digit_str, digit, parse_type):
        if parse_type == "count":
            return int(digit_str)
        elif parse_type == "hand":
            return len(digit_str) - len(digit_str.replace(str(digit), ""))
        else:
            raise TypeError("unknown digit count type: %s" % parse_type)

    def validate_ai_response(self, response, player_name, bid_count, bid_digit):
        response_text = response.output_text.lower()
        if response_text in [
            "challenge",
            "count",
            "challengecount",
            "challengechallenge",
        ]:
            return response

        if bid_count < 0 and bid_digit < 0:
            return response

        match = re.search(r"^(\d) of (\d)$", response_text)
        if not match:
            raise ValueError("unexpected response: %s" % response_text)

        ai_bid_count = int(match.groups()[0])
        ai_bid_digit = int(match.groups()[1])
        if ai_bid_count < bid_count or (
            ai_bid_count == bid_count and ai_bid_digit <= bid_digit
        ):
            error_msg = (
                "your bid of %s must be stronger than the current one (%d of %d), please try bidding again"
                % (response_text, bid_count, bid_digit)
            )
            log.error(error_msg)

            response = self.submit_prompt(error_msg, player_name)
            return self.validate_ai_response(
                response, player_name, bid_count, bid_digit
            )
        else:
            return response

    def parse_move(self, move_str):
        move_str = move_str.lower()
        if "challenge" in move_str:
            return {
                "move_str": "challenge",
                "move_type": "challenge",
                "state_action": 0,
            }
        elif "count" in move_str:
            return {
                "move_str": "challenge",
                "move_type": "challenge",
                "state_action": 0,
            }
        else:
            try:
                bid_count, bid_digit = [
                    int(x) for x in move_str.replace("bid: ", "").split(" of ")
                ]
                return {
                    "move_str": "%d of %d" % (bid_count, bid_digit),
                    "move_type": "bid",
                    "state_action": (self.state.encode_bid(bid_count, bid_digit) + 1),
                }
            except Exception as e:
                raise ValueError(move_str + "\n" + str(e))

    def get_agent_action(self):
        policy = self.agent(self.state)
        action = rng.choice(list(policy.keys()), p=list(policy.values()))
        return self.state.action_to_string(action), action

    def get_llm_action(self, order_ix, player_ix, bid_count, bid_digit):
        this_player_name = self.player_names[player_ix]
        this_player_masked_name = self.masked_names[player_ix]
        player_order_masked_names = [self.masked_names[x] for x in self.player_order]

        # include announcements about previous round and player's hand during the first round of betting
        if self.traj_length <= self.n_players:
            prompt = self.announcements.get(this_player_name, "")
            if len(prompt) > 0:
                prompt += "Player order will now be %s." % ", ".join(
                    player_order_masked_names
                )
            prompt += "\nHAND %s" % self.hands_ordered[order_ix]

        # also include bid history during the first round of betting for all but the first bidder
        if 1 < self.traj_length <= self.n_players:
            prompt += "\nThe initial bids were:\n"
            prompt += "\n".join(
                "%s: %s" % (self.masked_names[self.player_names.index(name)], bid)
                for name, bid in self.bid_history
            )
        # for all later moves, just show the previous players' moves
        elif self.traj_length > self.n_players:
            prompt = "\n".join(
                [
                    "%s: %s"
                    % (
                        self.masked_names[
                            self.player_names.index(
                                self.bid_history[-self.n_players + 1 + x][0]
                            )
                        ],
                        self.bid_history[-self.n_players + 1 + x][1],
                    )
                    for x in range(self.n_players - 1)
                ]
            )
        prompt += "\nIt is now your turn. %s" % instructions_reminder

        # switch out this LLM's masked name
        prompt = prompt.replace(this_player_masked_name, "You")

        t1 = datetime.datetime.now()
        response = self.submit_prompt(prompt, this_player_name)
        t2 = datetime.datetime.now()
        dt = (t2 - t1).total_seconds()

        log.info(f"response time: {str(dt)} sec")

        response = self.validate_ai_response(
            response, this_player_name, bid_count, bid_digit
        )
        return response.output_text

    def format_move_str(self, order_ix, move):
        return f"{self.current_player_name} move (hand {self.hands_ordered[order_ix]}): {move}"

    def play_round(self):
        bid_count = -1
        bid_digit = -1
        while True:
            for order_ix, player_ix in enumerate(self.player_order):
                self.traj_length += 1
                self.current_player_name = self.player_names[player_ix]
                self.current_player_ix = player_ix

                if self.player_types[player_ix] == "agent":
                    solly_move_str, solly_move_int = self.get_agent_action()
                    this_move_dict = self.parse_move(solly_move_str)
                    assert solly_move_int == this_move_dict["state_action"]

                    log.info(self.format_move_str(order_ix, this_move_dict["move_str"]))

                elif self.player_types[player_ix] == "llm":
                    llm_move = self.get_llm_action(
                        order_ix, player_ix, bid_count, bid_digit
                    )
                    this_move_dict = self.parse_move(llm_move)

                    log.info(self.format_move_str(order_ix, this_move_dict["move_str"]))

                elif self.player_types[player_ix] == "baseline":
                    self.baseline_player.set_hand(self.hands_ordered[order_ix])
                    is_rebid = self.last_bidder == self.player_names[player_ix]
                    self.baseline_player.set_current_bid(self.last_bid, is_rebid)
                    action_str = self.baseline_player.get_next_action_str(use_ev=True)
                    this_move_dict = self.parse_move(action_str)

                    log.info(self.format_move_str(order_ix, action_str))

                else:
                    raise ValueError(
                        "Unknown player type:", self.player_types[player_ix]
                    )

                self.bid_history.append(
                    (self.current_player_name, this_move_dict["move_str"])
                )

                if this_move_dict["move_type"] == "bid":
                    self.last_bid = this_move_dict["move_str"]
                    self.last_bidder = self.player_names[player_ix]
                    bid_count, bid_digit = [int(x) for x in self.last_bid.split(" of ")]

                log.info(
                    "Applying action to state: %s"
                    % self.state.action_to_string(this_move_dict["state_action"])
                )

                self.state.apply_action(this_move_dict["state_action"])
                if self.state.is_terminal():
                    break
            if self.state.is_terminal():
                break

        assert bid_count > 0 and bid_digit > 0
        self.total_counts = sum(
            [len(hand) - len(hand.replace(str(bid_digit), "")) for hand in self.hands]
        )
        if self.total_counts >= bid_count:
            self.result = "win"
            result_mult = 1
        else:
            self.result = "loss"
            result_mult = -1
        for player in self.player_names:
            self.player_rewards[player] = (
                result_mult * (self.n_players - 1)
                if player == self.last_bidder
                else -result_mult
            )
            self.player_counts.append(
                sum(
                    [
                        1 if int(s) == bid_digit else 0
                        for s in self.hands[self.player_names.index(player)]
                    ]
                )
            )
        assert self.total_counts == sum(self.player_counts)

        log.info(self.hands_ordered)
        log.info(
            f"{self.result} for {self.last_bidder} with bid {self.last_bid} and total count {self.total_counts}"
        )
        self.write_round_stats(header=True)


class AllRounds:
    def __init__(
        self,
        config,
        agent,
    ):
        self.agent = agent
        self.hand_length = agent._game.hand_length
        self.n_digits = agent._game.num_digits
        self.n_players = agent._game.num_players()

        self.game = pyspiel.load_game(
            "python_liars_poker",
            {
                "players": self.n_players,
                "num_digits": self.n_digits,
                "hand_length": self.hand_length,
            },
        )

        self.n_rounds = config.n_rounds

        assert len(config.player_names) == self.n_players
        assert len(config.player_names) == len(set(config.player_names))
        assert len(config.player_types) == self.n_players

        self.player_names = config.player_names
        self.player_types = config.player_types
        self.player_equity = [0] * self.n_players
        self.player_wins_by_bid = [0] * self.n_players
        self.player_losses_by_bid = [0] * self.n_players
        self.player_wins_by_challenge = [0] * self.n_players
        self.player_losses_by_challenge = [0] * self.n_players

        self.rounds = []
        self.n_successful_rounds = 0
        self.slips = None
        self.generate_slips()

        self.llm_model = config.open_ai_model
        self.llm_clients = {}
        self.llm_last_response_ids = {}
        for player_name, player_type in zip(self.player_names, self.player_types):
            assert player_type in ["agent", "llm", "baseline"]
            if player_type == "llm":
                self.llm_clients[player_name] = OpenAI(api_key=config.open_ai_api_key)
            else:
                self.llm_clients[player_name] = None
            self.llm_last_response_ids[player_name] = None

        self.round_num = 0

        self.file_ptr = log

        self.last_20_rewards = {player: [0] * 20 for player in self.player_names}

    def update_equity_and_counts(self, round_results):
        last_bidder_name = round_results["final_bidder"]
        result = round_results["result"]
        if result == "failed":
            return

        last_bidder_ix = self.player_names.index(last_bidder_name)

        assert result in ["win", "loss"]

        for ix in range(self.n_players):
            if result == "win":
                if ix == last_bidder_ix:
                    self.player_equity[ix] += self.n_players - 1
                    self.player_wins_by_bid[ix] += 1
                else:
                    self.player_equity[ix] += -1
                    self.player_losses_by_challenge[ix] += 1
            elif result == "loss":
                if ix == last_bidder_ix:
                    self.player_equity[ix] += -(self.n_players - 1)
                    self.player_losses_by_bid[ix] += 1
                else:
                    self.player_equity[ix] += 1
                    self.player_wins_by_challenge[ix] += 1
        self.n_successful_rounds += 1

        assert (
            sum(self.player_wins_by_bid) + sum(self.player_losses_by_bid)
        ) == self.n_successful_rounds

    def print_equity_and_counts(self):
        log.info(
            f"\nTotal successful rounds: {self.n_successful_rounds}\n"
            + "\t".join(
                [
                    "Wins by Bid",
                    "Losses by Bid",
                    "Wins by Challenge",
                    "Losses by Challenge",
                    "Equity",
                    "Avg Reward",
                ]
            )
        )

        for ix in range(self.n_players):
            log.info(
                "\t".join(
                    [
                        self.player_names[ix],
                        str(self.player_wins_by_bid[ix]),
                        str(self.player_losses_by_bid[ix]),
                        str(self.player_wins_by_challenge[ix]),
                        str(self.player_losses_by_challenge[ix]),
                        str(self.player_equity[ix]),
                        "%2.2f" % (self.player_equity[ix] / self.n_successful_rounds),
                    ]
                )
            )

    def generate_slips(self):
        self.slips = {}
        for player in self.player_names:
            self.slips[player] = [
                "".join(
                    [
                        str(x)
                        for x in rng.integers(1, self.n_digits + 1, self.hand_length)
                    ]
                )
                for _ in range(self.n_rounds)
            ]

    def choose_starting_player(self):
        return rng.choice(self.player_names)

    def create_instructions_prompt(self, starting_player_ix, this_player_ix):
        masked_names = [
            "Player%d" % (x + 1) if x != this_player_ix else "You"
            for x in range(self.n_players)
        ]
        player_order = [
            masked_names[(starting_player_ix + x) % self.n_players]
            for x in range(self.n_players)
        ]
        starting_player_name = masked_names[starting_player_ix]

        if self.n_players == 2:
            prompt = liars_poker_instructions_2players % (
                self.n_rounds,
                starting_player_name,
                liars_poker_rules,
            )
        elif self.n_players == 3:
            prompt = liars_poker_instructions_3players % (
                self.n_rounds,
                starting_player_name,
                player_order,
                liars_poker_rules,
            )
        else:
            raise ValueError(f"Unsupported number of players {self.n_players}")
        return prompt

    def submit_instructions(self, starting_player_ix):
        for player_ix in range(self.n_players):
            if self.player_types[player_ix] == "llm":
                prompt = self.create_instructions_prompt(starting_player_ix, player_ix)

                log.info(
                    "PROMPT TO %s: %s"
                    % (
                        self.player_names[player_ix],
                        prompt[:1000],
                    )
                )

                response = self.llm_clients[
                    self.player_names[player_ix]
                ].responses.create(
                    model=self.llm_model,
                    input=prompt,
                    previous_response_id=self.llm_last_response_ids[
                        self.player_names[player_ix]
                    ],
                )
                self.llm_last_response_ids[self.player_names[player_ix]] = response.id

    def generate_initial_prompts(
        self, starting_player_ix, previous_result, previous_total_count, previous_counts
    ):
        prompts = {player: "" for player in self.player_names}
        last_bidder_masked = "Player%d" % (starting_player_ix + 1)
        if previous_result == "none":
            return prompts

        previous_counts_str = (
            ", ".join(
                [
                    "Player%d had %d" % (p_ix + 1, previous_counts[p_ix])
                    for p_ix in range(self.n_players)
                ]
            )
            + " of that digit"
        )

        if previous_result == "win":
            announcement = """
There were a total of %s in the round.
%s.
%s won by successful bid.
Let's move on to the next round.
"""
        elif previous_result == "loss":
            announcement = """
There were a total of %s in the round.
%s.
%s lost by unsuccessful bid.
Let's move on to the next round.
"""
        else:
            raise ValueError("unknown result type:", previous_result)

        prompts = {}
        for ix in range(self.n_players):
            if self.player_types[ix] == "llm":
                prompts[self.player_names[ix]] = announcement % (
                    previous_total_count,
                    previous_counts_str,
                    last_bidder_masked,
                )

        return prompts

    def play_next_round(
        self,
        starting_player_name,
        previous_result,
        previous_total_count,
        previous_counts,
    ):
        starting_player_ix = self.player_names.index(starting_player_name)
        self.round_num += 1
        log.info(
            "\nROUND %d INITIAL BIDDER: %s"
            % (
                self.round_num,
                starting_player_name,
            )
        )

        if self.round_num == 1:
            self.submit_instructions(starting_player_ix)

        announcements = self.generate_initial_prompts(
            starting_player_ix, previous_result, previous_total_count, previous_counts
        )

        this_round = Round(
            self.round_num,
            self.hand_length,
            self.n_digits,
            self.n_players,
            self.player_names,
            self.player_types,
            starting_player_ix,
            announcements,
            self.game,
            self.agent,
            self.slips,
            self.llm_model,
            self.llm_clients,
            self.llm_last_response_ids,
            self.file_ptr,
        )

        this_round.play_round()

        round_results = {
            "length": this_round.traj_length,
            "final_bid": this_round.last_bid,
            "final_bidder": this_round.last_bidder,
            "result": this_round.result,
            "total_counts": "%s of %s"
            % (this_round.total_counts, this_round.last_bid[-1]),
            "player_counts": this_round.player_counts,
        }
        self.rounds.append(round_results)
        self.update_equity_and_counts(round_results)

        for player in self.player_names:
            self.last_20_rewards[player].pop(0)
            self.last_20_rewards[player].append(this_round.player_rewards[player])
        return round_results


def main(config: PlayAgentsConfig):
    agent_full_path = os.path.join(config.agent_path, config.agent_filename)
    if not os.path.isfile(agent_full_path):
        raise ValueError(f"Could not find agent at {agent_full_path}")

    with open(agent_full_path, "rb") as f:
        agent = cloudpickle.load(f)

    batch = AllRounds(config, agent)

    prev_round = {
        "final_bidder": batch.choose_starting_player(),
        "result": "none",
        "total_counts": "none",
        "player_counts": {},
    }
    for _ in range(config.n_rounds):
        this_round = batch.play_next_round(
            prev_round["final_bidder"],
            prev_round["result"],
            prev_round["total_counts"],
            prev_round["player_counts"],
        )
        if this_round["result"] != "failed":
            prev_round = this_round
            batch.print_equity_and_counts()


if __name__ == "__main__":
    config = load_config("../config_play_agents.yaml", config_type="play_agents")

    # set up IO
    save_dir = os.path.join(config.output_dir, config.agent_path.replace("/", "_"))
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    ts = dump_config(config, save_dir)

    # validate OpenAI configs
    if "llm" in config.player_types:
        assert config.open_ai_api_key
        assert config.open_ai_model

    player_names_concat = "_".join(config.player_names)
    log = get_logger(f"{save_dir}/{player_names_concat}_{ts}.log")

    main(config)
