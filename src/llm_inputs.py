liars_poker_instructions_2players = """
    I'd like to play a game of Liar's Poker with you. 
    Rather than the traditional game that has 8 digits that each go between 0 and 9 I'd like to play a modified game 
    that only has three numbers. And each number will only take the value, 1,2,3. 
    We will play with the Rebidding extension, which allows a player to rebid once if all other players have challenged
    that player's bid. We will not use any of the bonus bids extensions. 
    For each round, we will provide you with a randomly generated hand which I won't be able to see.
    The game will be 2 players, you and me. We will play %d rounds. 
    We will provide you with your hand in the following format: HAND 123.
    We have randomly selected %s to start the game, after which the final bidder of the current round will be the 
    first bidder of the next round.

    Once we start playing, respond with only the following format until the round ends: "x of k", 
    i.e. there are x or more of the digit k in the pool of hands. If you want to challenge my bid, write "challenge", 
    and if I have challenged you and you do not want to rebid, write "count".

    The round ends when a bidder has been challenged and announces the word "count"; if that is you, 
    you should simply say "count" and I will determine the number of digits you have on my end.

    Here are the rules in HTML format:

    %s"""

liars_poker_instructions_3players = """
    We'd like to play a game of Liar's Poker with you. 
    Rather than the traditional game that has 8 digits that each go between 0 and 9, We'd like to play a modified game 
    that only has three numbers. And each number will only take the value, 1,2,3. 
    We will play with the Rebidding extension, which allows a player to rebid once if all other players have challenged
    that player's bid. We will not use any of the bonus bids extensions. 
    For each round, we will provide you with a randomly generated hand which we won't be able to see.
    The game will be 3 players, you and two of us. We will play %d rounds. 
    We will provide you with your hand in the following format: HAND 123.

    We have randomly selected %s to start the game. The initial order of players will be %s,
    after which the final bidder of the current round will be the first bidder of the next round. 

    Once we start playing, respond with only the following format until the round ends: "x of k", 
    i.e. there are x or more of the digit k in the pool of hands. If you want to challenge my bid, write "challenge", 
    and if I have challenged you and you do not want to rebid, write "count".

    The round ends when a bidder has been challenged and announces the word "count"; if that is you, 
    you should simply say "count" and I will determine the number of digits you have on my end.

    Here are the rules in HTML format:

    %s"""

instructions_reminder = (
    "Remember that the acceptable responses are 'x of k', 'challenge', or 'count'"
)

liars_poker_rules = """
<body>
<title>Liars Poker Rules</title>

These rules reflect the most recent changes and evolution of Liars Poker as of February 10, 1986.

Any number of people may play Liars Poker, but the optimal number of players seems to be three to six. The
exact statement of some of these rules depends upon the number of players. Where necessary, we will use n
to refer to the number of players.

<h1>Overview of the basic game</h1>

To begin the game, each player obtains a random eight digit number. The most common method is to have
each player choose a bill (of US currency, generally a one dollar bill (A more primitive version of Liars Poker is
sometimes called "dollar poker.")). A player's number for that round is the serial number on the bill selected.
Play begins as one player makes the opening bid. A typical bid might be "5 sevens." This means that the
player estimates that the total number of sevens in all players’ numbers, including his own, is at least 5. The
turn then passes clockwise to the next player on the left. For his turn, each player must either make a
stronger bid or challenge the previous bid. A bid is stronger if it calls for at least the same number of
occurrences of a higher rank (e.g., "5 nines") or a greater number of occurrences (e.g., "6 threes"). The zero
is considered the highest rank (usually referred to as "ten" as in "7 tens").

Eventually, a bid will be challenged by all the other n-1 players. At this time, the bidder may ask for the count,
and then each player reveals how many of the selected rank he has. If the total number equals or exceeds
the number bid, the bidder wins one unit from each of the other players. If the bid is not made, then the
bidder loses one unit to each of the other players. Whether or not the bid is made, the final bidder is the first
bidder in the next round.

<h1>Extensions</h1>

The most important enhancement of the basic game is the right of rebidding. If a player's bid is challenged
by all of the other players, he has the option of playing this bid or of making a new, stronger bid. However,
only one rebid is allowed. If this new bid is also challenged by all the players, the bidding then stops and this
new bid is the final bid. If this new bid is not challenged by all of the remaining bidders and one of them
makes a stronger bid, the bidding continues with each player, including the bidder who just made a rebid,
having the right to rebid if challenged all the way around.
The allowance of rebids greatly extends the strategic scope of Liars Poker. The necessity to bluﬀ and
determine if others are bluﬃng are major features of the game.

<h1>Bonus Bids</h1>

<h2>The n+3 Rule</h2>

The greater the number of occurrences bid for, the more diﬃcult it is to make the bid. To encourage higher
bidding, the odds are tilted in favor of the bidder for high bids. To give a greater incentive to bid, and to
generally spice things up, if a bid of n+3 of a kind is made, the successful bidder wins two units from each
player instead of one unit. Thus, in a four-person game, a bid of '7 fours" is worth double. However, if the
bidder is unsuccessful at this level, he only loses one unit to each of the other players. Similarly, a successful
bidder of n+5 of a kind wins three units from each player while only risking one unit to each player should he
not make the bid. A bid of n+7 of a kind gets four to one odds; n+9 gets five to one odds, etc.

<h2>The Sixes Rule</h2>

Due to fervently asserted but statistically unverified beliefs that sixes are more diﬃcult to make than other
ranks, any bid of sixes is given preferential odds of twice what the bid would otherwise get. For example, in a
five player game, a bid of "7 sixes" will net the bidder two units from each player if successful, but only cost
him one unit if unsuccessful. A bid ·of "10 sixes" in a five-person game is especially attractive: the bidder can
only lose one unit to each player but he can win six units from each player (a multiplier of three because of
the n+5 rule and a multiplier of two due to the sixes rule for a total multiplier of two times three, i.e., six).

<h2>The Hero Bump</h2>

Occasionally one can make a successful bid without having any of the number bid. Such a "heroic" bid
entitles the bidder to a bump in the multiplier-the bid is worth one more than it would otherwise be. For
example, in a five-person game, if a person bids and makes "6 sixes" without having any sixes himself, he
wins three units from each player (the multiplier of two due to the sixes rule is bumped to three because of
the hero rule).

<h2>The Skunk Rule</h2>

If no player has any of the number bid for (including the bidder), instead of losing, the bidder wins. The
multiplier is 2n-6, independent of how many are bid or whether or not the bid is for sixes. Thus, in a five
person game, if the skunk rule applies, the bidder wins four from each player, whether the bid is "6 threes",
"7 sixes", or "8 twos." In a three person game, the skunk rule multiplier is zero-if there are none and the
game is a push. In a two person game, the skunk rule does not apply.

<h2>Progressive Stakes</h2>

The normal stake for each round is one unit, though it is commonly agreed by all players involved to increase
the stakes at times; a usual agreement is that the last hand of the night is for double stakes. Progressive
stakes is a formal way of varying the basic stake throughout the session. The basic stake for each round is
determined by the prior hand. It is the unit multiplier the bidder won or would have won. For example, in a
five-person game, suppose the hand's final bid is "8 sixes." By the n+3 rule and the sixes rule, this bid merits
a multiplier of four. Whether or not this bid is actually made, the basic stake for the next hand is four units.
Suppose in this next hand the final bid is "8 threes." This bid is a double by the n+3 rule. Since the basic
stake is four units for this hand, if the bid is made, the bidder wins eight units from each player. If the bidder
is unsuccessful, he loses four units to each player. For the following hand, the stake is again increased, this
time to two units (even though a successful bid would have won eight units per player, the multiplier due to
the bid was only two units). If the final bid in this hand is "6 twos." the stake for the following hand reverts
back to one unit. An exception is generally made for the skunk- rule: after a player "goes for the none," the
next hand is just a double, independent of the number of players. If a player has none, he is presumed to be
going for the none and not the hero for purposes of determining the stake for the next hand.

<h1>Conventions and Etiquette</h1>

<h2>Use of Bills</h2>
When using US currency for playing Liars Poker, there are certain conventions the adherence to which
demonstrates to others that a player is truly cultured. First, the selection of new bills for the next round must
be done with proper decorum. When starting a new session, the choice of the first bill goes to the player
whose fortunes as of late have been most disappointing; Thereafter, the final bidder from the previous round
has the honor of choosing the first bill. The choice then rotates clockwise to the next player and continues
around until all players have chosen their bills. In the first hand, the opening bidder is determined by looking
at the two letters which flank the serial number. The lowest pair by alphabetical order is given the first bid.
Thereafter, the final bidder of the previous hand starts oﬀ the bidding in the next round.

<h2>The Final Count</h2>

No matter how crazy the bidding may get, it eventually comes to an end. At this time, the players commence
the count. The historical method, still widely observed, is for the remaining players, starting with the player to
the bidder's left and then continuing clockwise, to hold up their hand with as many fingers raised as they
have digits with the correct rank. A defiant fist indicates the utter absence of the desired number.
"Getting fisted" is finding all the players around you waving their fists at you - certainly a cause for dejection, unless
you can turn the tables on them and skunk them!

<h2>Salomon's Liars Poker Strips SLIPS</h2>

Like most truly valuable pieces of our culture, Liars Poker isn't immune to the onrush of new technology.
Even given rather aggressive assumptions about future inflation and money supply growth, it was becoming
increasingly obvious that the available supply of bills would be exhausted long before the appetites of Liars
Poker players could be satisfied. The solution-- strips of computer generated random numbers known as
Salomon's Liars Poker Strips (SLIPS™)-- arrived not a moment too soon. The use of these sheets of fifteen
random numbers has necessitated several additional conventions to preserve the integrity of the game.

Play begins with each player choosing a SLIP™ of fifteen numbers, using the same conventions described
above for choosing bills. In the first round, each player uses the first number at the top of his SLIP™. To
determine which number is used for the second hand, each player gives the parity (odd/even) of the last digit
of the number just played. For each odd parity, one un-played number is skipped. If the bottom of the SLIP is
reached, the skipping wraps around back to the top. Only ten numbers are played on each SLIP™. The idea
of skipping is so that with progressive stakes, players cannot set up higher stakes when they know the next
number they’ll be playing will be a juicy one, like a number containing four 6’s. The tenth number played is
for double the stakes it otherwise would have been played for.

<h1>History:</h1>

LP goes back at least to 1972, when a game of liars poker featured at about the 12th minute of the movie
‘The Long Goodbye” with Elliot Gould. Also, the game has been played with diﬀerent rules at diﬀerent places
e.g. the story of Aaron Brown at Kidder told in his book, the Poker Face of Wall St, and the Quants. Other
variants are ‘I doubt it’ and Perudo. Wiki entry on the game here:
https://en.wikipedia.org/wiki/Liar%27s_poker (https://en.wikipedia.org/wiki/Liar%27s_poker)

<h2>Getting into the probabilities:</h2>
The basic math is pretty straightforward, and we all had a good sense of the probability distribution of digits
in a random selection of serial numbers. Let’s say you’re playing in a 6 person game, so there are 5 other
players besides yourself. Say that you have 3 8s. How many 8s are there likely to be among the other 5
players? Well, there are 5 times 8, or 40 digits in total, and so we’d expect there would be 4 of each digit
among those players. In fact, the probability that there are 4 or more occurrences of a given digit is a bit
higher than 50%, as you can see from the full calculation. Most players probably did these calculations, but
what’s really important is having a sense for the distribution of occurrences conditional on being challenged.

Unconditional probability of x occurrences in n total number of digits = (9/10)n-x(1/10)x n!/(n-x)!/x!

<h2>Example of winner’s curse in LP bidding:</h2>
The winner’s curse in LP results from the tendency to get challenged when the other players don’t have the
number you’re bidding. For example, in a five man field, with 5 times 8, or 40 digits out there, you’d expect 4
of each digit, but conditional on people only challenging if they have 0 or 1 of the bid digit, the expected
number of each digit is only 2 1/2.

<h3>An illustrative example of a 3 person game.</h3>

Brad: 15101952 Leo: 39540096 Mike: 93004455

Brad starts the bidding with 3 5s, Leo challenges even though he has one 5, but figures Mike will go up,
which he does, bidding 3 8s, a decoy. Brad has no 8s so challenges, and Leo has no 8s so challenges too.
Mike now switches to 4 fives, hoping that Brad’s opening bid meant he had a few. Brad suspects Mike’s
bluﬃng, and anyway, chances are Leo has none as he challenged first time around, and the chance of him
having none is higher than him having 1, so Brad challenges as he thinks he has a high chance of losing 2
units if he bids 5 5s, vs a high chance of losing just one unit if he challenges 4 5s. Leo figures that Mike
probably has two 5s but he’s not sure about Brad as all he did was start with 3 fives, so he challenges too.
It’s 2nd time around, so Mike has to count, and there are five 5s, and so Mike wins, and Brad and Leo both
wish they had gone up. Brad and Leo have to pay Mike one unit each.

LP also probably sharpened our trading skills. It even had some similarities to the calculus of bidding for US
treasury bonds at auction, although that’s quite another story altogether. It was a zero sum game, and so you
had to keep asking yourself what were the mistakes these other smart players might be making, and often
one worried that the best one could hope for was to break even.

If you played enough, you could see a number of decision-making biases of the Kahneman-Tversky variety in
action (we never heard of those guys at the time), including confirmation bias, anchoring, herding (we called
it ‘glomming’), and the fallacy of sunk costs, driving some players to double down and bid more aggressively
to try to dig themselves out of hole, and bidding that sometimes seemed aimed at minimizing regret rather
than maximizing gains. Above all, people tend to be over-confident, much as 90% of drivers believe
themselves to be above average. Most players didn’t like to see themselves as passive, and so didn’t like to
follow a strategy heavy on challenging, which made the more passive approach a good one, and had the
added benefit of allowing you to be a pretty dangerous snake in the grass on occasion. Sometimes a
challenging strategy would come into vogue, and then it would be time to become a more active bidder
(which may provide some answer to the topical question about what happens as index investing becomes
bigger and bigger).

Other variations not mentioned in 1986 rules document: PYB (Pick your best), around the horn, elimination
(usually for determining who would pay for a group dinner), roll ‘em.

<h1>The ‘sheet’:</h1>
A score sheet kept by the most meticulous of the group. It was an honor to be trusted with the sheet.
Generally the sheet was settled monthly. It was not expected that the sheet keeper would keep or share
statistics with players beyond the past month’s tally. On one occasion, the sheet keeper gave a life-to-date
tally to one of the players, who then dropped out of the game forever more, much to the vexation of the rest
of the players.

There are no apps we’d recommend, or good computerized players to practice against, and as far as we
know, no solution to the game, but it does seems solvable with machine learning algorithms if not with other
approaches too.

More statistics and analysis: http://wizardofodds.com/games/liars-poker/
(http://wizardofodds.com/games/liars-poker/)

Thanks to Yung Lim (an honoured former keeper of the sheet) for providing a copy of the 1986 Salomon
rules.
</body>
"""
