from data_structures.trees import Tree, Node, ChanceNode
from functools import reduce
from enum import Enum
from games.utilities import all_permutations

class TieSolver(Enum):
    Accumulate = 0
    DiscardIfAll = 1
    DiscardIfHigh = 2
    DiscardAlways = 3
    CyclicUtility = 4 # More utility type than TieSolver...

def build_goofspiel_tree(num_players, rank, tie_solver = TieSolver.Accumulate):
    """
    Build a tree for the game of Goofspiel with a given number of players and a given number of ranks in the deck (i.e. how
    many cards).
    """

    root = ChanceNode(0)

    tree = Tree(num_players, 0, root)

    hands = all_permutations(list(range(1, rank+1)))
    hand_probability = 1 / len(hands)
    information_sets = {}

    for hand in hands:
        node_known_info = (0, 0, tuple(hand[:1]), tuple([() for p in range(num_players)]))
        if node_known_info in information_sets:
            information_set = information_sets[node_known_info]
        else:
            information_set = -1

        n = tree.addNode(0, parent = root, probability = hand_probability, actionName = str(hand), information_set = information_set)

        if information_set == -1:
            information_sets[node_known_info] = n.information_set

        build_goofspiel_hand_tree(hand, [list(range(1, rank+1)) for p in range(num_players)],
                                  [[] for p in range(num_players)], 0, 0, n, tree, tie_solver, information_sets)
            
    return tree

def build_goofspiel_hand_tree(hand, remaining_cards, played_cards, current_round, current_player, current_node, tree, tie_solver,
                              information_sets):
    """
    Recursively build the subtree for the Kuhn game where the hand is fixed.
    """

    num_players = tree.numOfPlayers
    if(current_player == num_players-1):
        next_player = 0
        next_round = current_round + 1
    else:
        next_player = current_player + 1
        next_round = current_round
        
    current_player_cards = remaining_cards[current_player].copy()

    # Create a leaf as a children of the last effective decision node (there is no decision for players that
    # have only their last card in hand)
    if(len(remaining_cards[current_player]) == 2 and len(remaining_cards[next_player]) == 1):
        for card in current_player_cards:
            actionName = "p" + str(current_node.player) + "c" + str(card)
            remaining_cards[current_player].remove(card)
            played_cards[current_player].append(card)
            final_played_cards = [played_cards[i] + remaining_cards[i] for i in range(len(played_cards))]
            l = tree.addLeaf(parent = current_node, utility = goofspiel_utility(hand, final_played_cards, tie_solver),
                             actionName = actionName)
            remaining_cards[current_player].append(card)
            played_cards[current_player].remove(card)
        return

    for card in current_player_cards:
        actionName = "p" + str(current_node.player) + "c" + str(card)

        node_known_info = (next_player, next_round, tuple(hand[:next_round+1]), tuple([tuple(c[:next_round]) for c in played_cards]))
        if node_known_info in information_sets:
            information_set = information_sets[node_known_info]
        else:
            information_set = -1

        n = tree.addNode(next_player, information_set, parent = current_node, actionName = actionName)

        if information_set == -1:
            information_sets[node_known_info] = n.information_set

        remaining_cards[current_player].remove(card)
        played_cards[current_player].append(card)
        build_goofspiel_hand_tree(hand, remaining_cards, played_cards, next_round, next_player, n, tree, tie_solver,
                                           information_sets)
        remaining_cards[current_player].append(card)
        played_cards[current_player].remove(card)

def build_all_possible_hands(num_players, ranks):
    """
    Build all the possible hands for the game of Goofspiel with a given number of players and a given set of cards.
    """

    perm = all_permutations(range(1, ranks+1))

    if(num_players == 0):
        return list(map(lambda el: [el], perm))

    hands = []
    smaller_hands = build_all_possible_hands(num_players-1, ranks)

    for p in perm:
        for hand in smaller_hands:
            hands.append(hand + [p])

    return hands

def goofspiel_utility(hand, moves, tie_solver = TieSolver.Accumulate):
    """
    Get the utility of a Goofspiel game given the hand and how the players have played.
    """

    num_players = len(moves)
    u = [0] * num_players
    additional_utility = 0

    for i in range(len(hand)):
        round_moves = [moves[p][i] for p in range(num_players)]
        winner = winner_player(round_moves, tie_solver)

        if(winner == -1):
            if tie_solver == TieSolver.Accumulate or tie_solver == TieSolver.CyclicUtility:
                additional_utility += hand[i]
        else:
            u[winner] += hand[i] + additional_utility
            additional_utility = 0

    if tie_solver == TieSolver.CyclicUtility:
        round_zero_moves = [moves[p][0] for p in range(num_players)]
        first_cards_equal = (max(round_zero_moves) == min(round_zero_moves))
        highest_card = max(hand)
        tot = 0
        for (i, uval) in enumerate(u):
            tot += uval * (i + 1)
        u = [0 for _ in u]
        u[tot % num_players] = 2 if first_cards_equal else 1

    return u

def winner_player(round_moves, tie_solver):
    """
    Calculate the winner player given the cards that were played in a round.
    """

    moves_dict = {}
    for p in range(len(round_moves)):
        move = round_moves[p]
        if(move in moves_dict):
            moves_dict[move].append(p)
        else:
            moves_dict[move] = [p]

    single_moves = list(filter(lambda el: len(el[1]) == 1, moves_dict.items()))

    if(len(single_moves) == 0):
        return -1

    if(len(single_moves) < len(round_moves) and tie_solver == TieSolver.DiscardAlways):
        # At least two players have played the same card, so under the DiscardAlways tie solver we have no winner
        return -1

    winner = max(single_moves, key = lambda el: el[0])[1][0]

    if(round_moves[winner] != max(round_moves) and tie_solver == TieSolver.DiscardIfHigh):
        # There was a tie on the higher card played, so under the DiscardIfHigh tie solver we have no winner
        return -1

    return winner