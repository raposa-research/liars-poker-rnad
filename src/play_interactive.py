import logging
import os
from typing import List, Literal

import cloudpickle
import numpy as np
import pyspiel
from open_spiel.python import games  # pylint: disable=unused-import

from setup_logs import get_logger
from utils import dump_config, load_config


class LiarsPokerGame:

    def __init__(self, agent, game, player_names):
        self.game = game
        self.agent = agent
        self.num_players = agent._game.num_players()
        self.num_digits = agent._game.num_digits
        self.hand_length = agent._game.hand_length
        self.players = self.create_player_object(player_names)

        self.actions = [
            (x, y)
            for x in range(1, self.num_players * self.hand_length + 1)
            for y in list(range(1, self.num_digits + 1))
        ]
        self.action_map = {
            self.actions[ix]: ix + 1
            for ix in range(0, self.num_players * self.num_digits * self.hand_length)
        }
        self.action_map[(0, 0)] = 0
        self.allowed_moves_map = {v: k for k, v in self.action_map.items()}

        self.game_ctr = 0

        self.current_game_action_list = []

    def create_player_object(self, player_names):
        return {
            i: {
                "name": player_names[i] if i < (self.num_players - 1) else "AI",
                "player_type": "human" if i < (self.num_players - 1) else "ai",
                "ix": None,  # these change each round depending on starting_player
                "points": 0,
                "wins": 0,
                "losses": 0,
            }
            for i in range(self.num_players)
        }

    def get_pid_and_type_from_ix(self, ix):
        for pid in self.players.keys():
            if self.players[pid]["ix"] == ix:
                return pid, self.players[pid]["player_type"]
        raise ValueError("Did not find ix %d in players: %s" % (ix, str(self.players)))

    def get_pid_from_name(self, name):
        for pid in self.players.keys():
            if self.players[pid]["name"] == name:
                return pid
        raise ValueError("Did not find %s in players: %s" % (name, str(self.players)))

    def update_points(self, bidder_pid, outcome_type: Literal["winner", "loser"]):
        for this_pid in self.players.keys():
            if this_pid == bidder_pid:
                gain_or_loss = (
                    (self.num_players - 1)
                    if outcome_type == "winner"
                    else -(self.num_players - 1)
                )
                self.players[this_pid]["points"] += gain_or_loss
                self.players[this_pid]["wins"] += 1 if outcome_type == "winner" else 0
                self.players[this_pid]["losses"] += 1 if outcome_type == "loser" else 0
            else:
                gain_or_loss = -1 if outcome_type == "winner" else 1
                self.players[this_pid]["points"] += gain_or_loss
                self.players[this_pid]["losses"] += 1 if outcome_type == "winner" else 0
                self.players[this_pid]["wins"] += 1 if outcome_type == "loser" else 0

    def set_starting_player(self, starting_player_pid):
        for i in self.players.keys():
            self.players[i]["ix"] = (
                i - starting_player_pid + self.num_players
            ) % self.num_players

    def register_game_outcome(self, final_bidder: str, is_successful_bid: bool) -> int:
        gain_or_loss_amount = self.num_players - 1
        bidder_pid = self.get_pid_from_name(final_bidder)

        # check if there was a winning bidder
        if is_successful_bid:
            self.update_points(bidder_pid, "winner")
            log.info(
                "\n%s wins %d, all others lose 1"
                % (self.players[bidder_pid]["name"], gain_or_loss_amount)
            )
        # otherwise there was a losing bidder
        else:
            self.update_points(bidder_pid, "loser")
            log.info(
                "\n%s loses %d, all others gain 1"
                % (self.players[bidder_pid]["name"], gain_or_loss_amount)
            )

        # in any situation, final bidder starts the next round
        log.info("%s starts the next round" % final_bidder)
        return bidder_pid

    def create_hand_state(self, hand):
        state = self.game.new_initial_state()

        # populate hands
        for card in hand:
            for i in range(self.num_players):
                state.apply_action(card)

        return state

    def rewind(self, state, action_list):
        for action in action_list:
            action_string = state.action_to_string(state.current_player(), action)
            state.apply_action(action)
            self.current_game_action_list.append(action)

            previous_action = action_string
            if action_string != "Challenge":
                last_non_challenge_bid = action_string
        return state, previous_action, last_non_challenge_bid

    def get_ai_bid_count(self, ai_hand: List[int], bid_digit: int) -> int:
        return sum(1 if x == bid_digit else 0 for x in ai_hand)

    def get_human_count_input(self, player_ix, bid_digit: int):
        this_player_count = input(
            f"How many {bid_digit}s did {self.players[player_ix]['name']} have?"
        )
        try:
            ct = int(this_player_count)
            assert 0 <= ct <= self.hand_length * self.num_players
        except ValueError:
            log.info("Entered value must be an integer")
        except AssertionError:
            log.info(
                f"Entered value must be non-negative and at most {self.hand_length * self.num_players}"
            )
        return ct

    def play_game(
        self, starting_player: int, ai_hand: List[int], action_list=None
    ) -> int:
        """
        Play a game of Liar's Poker.
        inputs:
          starting_player: PID of the starting player. In the code below, this player's IX will be 0.

        returns:
            next_round_opener_pid: pid of the final bidder, regardless of winning/losing the round
        """
        if not action_list:
            # new game, we're moving on to the next round
            self.game_ctr += 1

        # flush current game action list
        self.current_game_action_list = []

        log.info("\nSTARTING ROUND %d" % self.game_ctr)
        log.info("AI hand: %s" % ai_hand)

        # Get a new state
        state = self.create_hand_state(ai_hand)
        self.set_starting_player(starting_player)

        if action_list:
            state, previous_action, last_non_challenge_bid = self.rewind(
                state, action_list
            )
            print("Previous action: %s" % previous_action)
            print("Last non-challenge bid: %s" % last_non_challenge_bid)
        else:
            print("\n########## Starting new game ###########\n")
            print(
                "########## Starting player: %s ########## "
                % self.players[starting_player]["name"]
            )

            previous_action = ""
            last_non_challenge_bid = ""

        # play the game
        while not state.is_terminal():
            # The state can be three different types: chance node,
            # simultaneous node, or decision node
            if state.is_chance_node():
                raise EnvironmentError("State should already be set with AI's hand")
            else:
                # Decision node: sample action for the single current player
                # player_type should be either "human" or "ai"
                pid, player_type = self.get_pid_and_type_from_ix(state.current_player())
                player_name = self.players[pid]["name"]
                if player_type == "ai":
                    # Agent turn.
                    print("-------------------\n%s's turn" % player_name)
                    action_probs = self.agent(state)
                    if config.debug:
                        print(
                            "%s's hand: %s"
                            % (player_name, str(state.hands[state.current_player()]))
                        )
                        for i, a in enumerate(
                            state.legal_actions(state.current_player())
                        ):
                            print(
                                "%01d) %s  (p = %.1f%%)"
                                % (i, state.action_to_string(a), action_probs[a] * 100)
                            )
                    prob_sum = sum(action_probs.values())
                    action = np.random.choice(
                        list(action_probs.keys()),
                        p=[x / prob_sum for x in action_probs.values()],
                    )
                    self.current_game_action_list.append(action)
                else:
                    # Human turn.
                    print("-------------------\n%s's turn." % player_name)
                    print("Moves available: ")
                    for i, a in enumerate(state.legal_actions(state.current_player())):
                        print(str(i) + ") " + state.action_to_string(a))
                    action_ix = int(
                        input(
                            "Enter the number corresponding to a move. "
                            + "Enter -1 to rewind.\n"
                        )
                    )
                    if action_ix == -1:
                        n_steps = int(input("How many steps to undo?"))
                        log.info("REWINDING %d STEPS" % n_steps)
                        return self.play_game(
                            starting_player,
                            ai_hand,
                            self.current_game_action_list[0:-n_steps],
                        )
                    action = state.legal_actions(state.current_player())[int(action_ix)]
                    self.current_game_action_list.append(action)

                action_string = state.action_to_string(state.current_player(), action)
                if previous_action:
                    extra = (
                        " to %s" % last_non_challenge_bid
                        if previous_action == "Challenge"
                        else ""
                    )
                    print(
                        "Player %s selected action: %s\n(Previous action was %s)\n"
                        % (player_name, action_string, previous_action + extra)
                    )
                else:
                    print(
                        "Player %s selected action: %s  (initial bid)\n"
                        % (player_name, action_string)
                    )

                log.info("%s,%s" % (player_name, action_string))

                state.apply_action(action)
                previous_action = action_string
                if action_string != "Challenge":
                    last_non_challenge_bid = action_string

        # Round is now over
        log.info("-------------------\nRound over.\n")
        final_bidder = self.players[
            self.get_pid_and_type_from_ix(state._bid_originator)[0]
        ]["name"]
        log.info(
            "Last %s (%s)"
            % (
                last_non_challenge_bid,
                final_bidder,
            )
        )
        bid_details = last_non_challenge_bid.strip("Bid: ").split(" of ")
        bid_count = int(bid_details[0])
        bid_digit = int(bid_details[1])

        player_counts = []
        for player_ix in self.players:
            if self.players[player_ix]["player_type"] == "ai":
                player_counts.append(self.get_ai_bid_count(ai_hand, bid_digit))
            else:
                this_player_count = self.get_human_count_input(player_ix, bid_digit)
                player_counts.append(int(this_player_count))

        total_count = sum(player_counts)
        log.info(f"There were {total_count} of the final bid digit in this round")

        is_successful_challenge = bid_count <= total_count
        next_round_opener_pid = self.register_game_outcome(
            final_bidder, is_successful_challenge
        )

        log.info("\nPlayer points:")
        for pid in self.players.keys():
            log.info(
                f"{self.players[pid]['name']}: {self.players[pid]['points']} points, {self.players[pid]['wins']} wins"
            )

        # stop for banter
        input("\nPress RETURN to continue to next round.")

        return next_round_opener_pid


def main():

    with open(agent_full_path, "rb") as f:
        agent = cloudpickle.load(f)

    game = pyspiel.load_game(
        "python_liars_poker",
        {
            "players": agent._game.num_players(),
            "num_digits": agent._game.num_digits,
            "hand_length": agent._game.hand_length,
        },
    )

    player_names = []
    ctr = 0
    for _ in range(agent._game.num_players() - 1):
        prompt_str = "First Player" if ctr == 0 else "Next Player"
        player_name = input("Enter %s's name:  " % prompt_str)
        player_names.append(player_name)
        ctr += 1

    liars_poker_game = LiarsPokerGame(agent, game, player_names)

    players_str = "\n".join(
        ["%d: %s" % (ix + 1, name) for ix, name in enumerate(player_names)]
        + ["%d: AI" % (len(player_names) + 1)]
    )
    starting_player_input = int(
        input("Enter starting player:\n0: Random\n%s\n" % players_str)
    )
    if starting_player_input > 0:
        starting_player = int(starting_player_input - 1)
    else:
        starting_player = np.random.randint(0, agent._game.num_players())

    # start playing the games
    while True:
        ai_hand_str = input("Enter AI's hand for this round (format 1,2,3,...):  ")
        try:
            ai_hand = [int(x) for x in ai_hand_str.split(",")]
        except ValueError:
            print("Could not parse hand. Check the formatting.")
            continue
        if len(ai_hand) != agent._game.hand_length:
            print("Wrong Number of digits. Check the formating and try entering again.")
            continue

        starting_player = liars_poker_game.play_game(starting_player, ai_hand)


if __name__ == "__main__":
    config = load_config(
        "../config_play_interactive.yaml", config_type="play_interactive"
    )

    # set up IO
    save_dir = os.path.join(config.output_dir, config.agent_path.replace("/", "_"))
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    ts = dump_config(config, save_dir)

    agent_full_path = os.path.join(config.agent_path, config.agent_filename)

    # log is specific to these hands
    logfile = f"game_{os.path.basename(config.agent_filename)}_{ts}.log"
    log = get_logger(os.path.join(save_dir, logfile))

    # initiate game
    main()
