import re
from math import factorial as fc


class BaselineModel:
    def __init__(self, hand_length, n_digits, n_players):
        self.hand_length = hand_length
        self.n_digits = n_digits
        self.n_players = n_players
        self.max_allowed_moves = hand_length * n_digits * n_players

        self.n_total_digits = n_digits * n_players
        self.n_unknown_digits = n_digits * (n_players - 1)

        self.win_reward = n_players - 1
        self.challenge_reward = 1

        self.openspiel_action_int_to_str = self.generate_action_map()
        self.openspiel_action_str_to_int = {
            v: k for k, v in self.openspiel_action_int_to_str.items()
        }
        self.actions = {
            k: self.parse_bid(k)
            for k in self.openspiel_action_str_to_int.keys()
            if k != "challenge"
        }

        self.current_hand_counts = {}
        self.current_bid = {"digit": None, "count": None, "str": None, "int": None}
        self.count_diff = None

        self.digit_prob = 1.0 / self.n_digits
        self.probs = self.generate_conditional_binomial_probs()

    def set_hand(self, hand_str):
        # hands are expected to be in the string form 12345
        self.current_hand_counts = {}
        for ix in range(1, self.n_digits + 1):
            self.current_hand_counts[ix] = sum(
                [1 if int(s) == ix else 0 for s in hand_str]
            )
        # reset the count_diff so it doesn't accidentally get used
        self.count_diff = None

    def parse_bid(self, bid_str):
        if bid_str == "challenge":
            raise ValueError("'challenge' is not a valid bid str")

        if len(bid_str) == 0:
            # typically for the initial bidder
            return {
                "count": None,
                "digit": None,
                "int": 0,
            }

        match = re.search(r"^(\d) of (\d)$", bid_str)
        if not match:
            raise ValueError("unexpected bid string: %s" % bid_str)

        return {
            "count": int(match.groups()[0]),
            "digit": int(match.groups()[1]),
            "int": self.openspiel_action_str_to_int[bid_str],
        }

    def set_current_bid(self, bid_str, is_rebid):
        action_dict = self.parse_bid(bid_str)
        self.current_bid["count"] = action_dict["count"]
        self.current_bid["digit"] = action_dict["digit"]
        self.current_bid["str"] = bid_str
        self.current_bid["int"] = action_dict["int"]
        self.current_bid["is_rebid"] = is_rebid
        # update count_diff
        if self.current_bid["count"] and self.current_bid["digit"]:
            self.count_diff = (
                self.current_bid["count"]
                - self.current_hand_counts[self.current_bid["digit"]]
            )

    def generate_action_map(self):
        action_list = [
            "%d of %d" % (x, y)
            for x in range(1, self.n_total_digits + 1)
            for y in range(1, self.n_digits + 1)
        ]
        action_map = {
            ix: action_list[ix - 1] for ix in range(1, self.max_allowed_moves + 1)
        }
        action_map[0] = "challenge"
        return action_map

    def binom_bid(self, count_diff):
        # here we sum the binomial distribution probabilities to get the chance of winning a bid
        # relative to the player's private hand (as by count_diff)

        cum_prob = 0
        if count_diff <= 0:
            # I have 3 in my hand and I'm bidding 3
            return 1.0
        if count_diff > self.n_unknown_digits:
            # e.g. in 3x3 2-player, if I have 1 in my hand, there is no way there are 5 or more between both players
            return 0.0
        while count_diff <= self.n_unknown_digits:
            cum_prob += (
                self.digit_prob**count_diff
                * (1 - self.digit_prob) ** (self.n_unknown_digits - count_diff)
                * fc(self.n_unknown_digits)
                / fc(count_diff)
                / fc(self.n_unknown_digits - count_diff)
            )
            count_diff += 1
        return cum_prob

    def binom_challenge(self, count_diff):
        # here we sum the binomial distribution probabilities to get the chance of winning a challenge
        # relative to the player's private hand (as by count_diff)
        # e.g. in 3x3 2-player, if I have 3 in my hand, a -3 count diff means I'm challenging a bid of 6
        #                       and a +1 count_diff means I'm challenging a bid of 2
        cum_prob = 0
        if -count_diff >= 0:
            # e.g. if I have 3 in my hand and challenge a bid of 1, 2, or 3, I will definitely lose
            return 0.0
        if count_diff > self.n_unknown_digits:
            # I'm winning the challenge even if every unknown digit is the right one
            return 1.0

        winning_count = count_diff - 1
        while winning_count >= 0:
            # e.g. I have 3 in my hand and challenge a bid of 4 (count_diff = -1),
            # I win if there are 0 in the remaining hand(s)
            # e.g. If I have 3 in my hand and challenge a bid of 5 (count_diff = -2),
            # I win if there are 0 or 1 in the remaining hand(s)

            cum_prob += (
                self.digit_prob**winning_count
                * (1 - self.digit_prob) ** (self.n_unknown_digits - winning_count)
                * fc(self.n_unknown_digits)
                / fc(winning_count)
                / fc(self.n_unknown_digits - winning_count)
            )
            winning_count -= 1
        return cum_prob

    def generate_conditional_binomial_probs(self):
        # this function generates the likelihood of winning a bet (x or more of a digit) or a challenge (not x or more
        # of the digit) conditional on the difference of count in the current hand and the current bid
        # this is a mapping to be used during decisionmaking

        cond_probs_bid = {}
        cond_probs_challenge = {}
        for count_diff in range(-(self.hand_length - 1), self.n_total_digits + 1):
            cond_probs_bid[count_diff] = self.binom_bid(count_diff)
        for count_diff in range(-(self.hand_length - 1), self.n_total_digits + 1):
            cond_probs_challenge[count_diff] = self.binom_challenge(count_diff)
        return {"bid": cond_probs_bid, "challenge": cond_probs_challenge}

    def get_bid_count_diff(self, action_ix):
        action_dict = self.actions[self.openspiel_action_int_to_str[action_ix]]
        hand_count = self.current_hand_counts[action_dict["digit"]]
        return action_dict["count"] - hand_count

    def get_next_action_int(self, use_ev=False):
        """
        This funtion implements the baseline model's strategy, which is based on binomial probabilities of the
        unknown hand. The strategy produces the greediest move.

        is_rebid: if True, this player was the last bidder and is now on a rebid
        use_ev: if True, the model will take the rewards into account when deciding the move

        returns:
            action_int: openspiel-appropriate integer for this move
        """
        best_action_name = ""
        best_action_ix = -1
        prob_best_action = -1.0

        # deal with initial bid:
        if not self.current_bid["count"] and not self.current_bid["digit"]:
            for ix in range(1, self.max_allowed_moves + 1):
                prob = self.probs["bid"][self.get_bid_count_diff(ix)]
                if prob > prob_best_action:
                    prob_best_action = prob
                    best_action_name = self.openspiel_action_int_to_str[ix]
                    best_action_ix = ix
            return best_action_ix

        # probability of success if challenge
        prob_challenge = self.probs["challenge"][self.count_diff]

        # probability of winnig with the current bid (if rebid)
        prob_count = self.probs["bid"][self.get_bid_count_diff(self.current_bid["int"])]

        # find lowest, greediest bid
        for ix in range(self.current_bid["int"] + 1, self.max_allowed_moves + 1):
            prob = self.probs["bid"][self.get_bid_count_diff(ix)]
            if prob > prob_best_action:
                prob_best_action = prob
                best_action_name = self.openspiel_action_int_to_str[ix]
                best_action_ix = ix

        # strategy:
        # if this is a rebid, consider the win probability/EV of the current bid instead of challenge prob/EV
        #   -> choose 'count' if tied with a higher bid
        # if not a rebid, compare win probability/EV of best action with challenge prob/EV
        #   -> choose 'challenge' if tied with a higher bid

        if use_ev:
            ev_count = self.win_reward * (2 * prob_count - 1)
            ev_challenge = self.challenge_reward * (2 * prob_challenge - 1)
            ev_best_action = self.win_reward * (2 * prob_best_action - 1)
            if self.current_bid["is_rebid"]:
                if ev_count >= ev_best_action:
                    return 0
                else:
                    return best_action_ix
            elif ev_challenge >= ev_best_action:
                return 0
            else:
                return best_action_ix
        else:
            if self.current_bid["is_rebid"]:
                if prob_count >= prob_best_action:
                    return 0
                else:
                    return best_action_ix
            elif prob_challenge >= prob_best_action:
                return 0
            else:
                return best_action_ix

    def get_next_action_str(self, use_ev=False):
        # returns the action in string format
        return self.openspiel_action_int_to_str[self.get_next_action_int(use_ev)]


if __name__ == "__main__":
    # sample code demonstrating the baseline model's bidding strategy for 3 different hands
    bm = BaselineModel(3, 3, 3)
    for hand in ["111", "121", "132"]:
        bm.set_hand(hand)
        print("HAND", hand)
        for action_int in range(1, 20):
            bm.set_current_bid(bm.openspiel_action_int_to_str[action_int], False)
            print(
                "\tchosen next action: %s"
                % (bm.openspiel_action_int_to_str[bm.get_next_action_int()],)
            )
