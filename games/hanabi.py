from data_structures.trees import Tree, Node, ChanceNode
from functools import reduce
from games.utilities import all_permutations, pair_to_number, number_to_pair, list_to_tuple
from copy import deepcopy
from enum import Enum

class UtilitySplitter(Enum):
    Uniform = 0
    Competitive = 1

class HanabiState:
    def __init__(self, remaining_deck, player_hands, cards_in_play, discarded_cards, clue_tokens_available, 
                 clue_history, player_clued_hands, action_history, highest_card_number, remaining_turns_after_deck_end = -1):
        self.remaining_deck = remaining_deck
        self.player_hands = player_hands
        self.cards_in_play = cards_in_play
        self.discarded_cards = discarded_cards
        self.clue_tokens_available = clue_tokens_available
        self.clue_history = clue_history
        self.player_clued_hands = player_clued_hands
        self.action_history = action_history
        self.remaining_turns_after_deck_end = remaining_turns_after_deck_end
        self.highest_card_number = highest_card_number

        # TODO: maybe clue history is not needed now that we have action history??

    def toPlayerState(self, player):
        player_visible_hands = self.player_hands[:player] + [self.player_clued_hands[player]] + \
                                self.player_hands[player+1:]
        return list_to_tuple((player_visible_hands, self.cards_in_play, self.discarded_cards, 
                        self.clue_tokens_available, self.clue_history, self.action_history,
                        self.player_clued_hands))

    def getLegalActions(self, player):
        actions = set() # Use a set to remove duplicates (in particular, duplicate clue actions)

        for i in range(len(self.player_hands[player])):
            card = self.player_hands[player][i]
            if card == 0 or card == (0, 0):    # 0 and (0, 0) indicate empty slot
                continue

            actions.add('p.' + str(i) + '-P' + str(player))    # add action to play i-th card
            actions.add('d.' + str(i) + '-P' + str(player))    # add action to discard i-th card

        if self.clue_tokens_available > 0:
            # In only one number/color is left in the cards in the remaining deck and in the hands of the
            # players, then do not allow to give that clue (it would be useless)
            all_numbers_left = set()
            all_colors_left = set()
            for card in self.remaining_deck:
                if type(card) == int:
                    card = number_to_pair(card)
                all_numbers_left.add(card[0])
                all_colors_left.add(card[1])
            for hand in self.player_hands:
                for card in hand:
                    if type(card) == int:
                        card = number_to_pair(card)
                    all_numbers_left.add(card[0])
                    all_colors_left.add(card[1])
            give_number_clues = len(all_numbers_left) > 1
            give_colors_clues = len(all_colors_left) > 1

            for other_player in range(len(self.player_hands)):
                if other_player == player:
                    continue

                for card_index in range(len(self.player_hands[other_player])):
                    card = self.player_hands[other_player][card_index]
                    
                    if type(card) == int:
                        card = number_to_pair(card)
                    
                    if card == (0, 0):    # (0, 0) indicate empty slot
                        continue
                    
                    already_given_clues = self.player_clued_hands[other_player][card_index]
                    if already_given_clues[0] == 0 and give_number_clues:
                        actions.add('c' + str(other_player) + '.n' + str(card[0]) + '-P' + str(player))   # clue number
                    if already_given_clues[1] == 0 and give_colors_clues:
                        actions.add('c' + str(other_player) + '.c' + str(card[1]) + '-P' + str(player))   # clue color

        actions = sorted(list(actions)) # Sort actions so that they are in the same order in each node
        return actions

    def getChildState(self, action):
        player = int(action.split('-')[1][1])
        action = action.split('-')[0]

        ################# PLAY ACTION #################
        if action[0] == 'p':
            card_index = int(action.split('.')[1])
            card = self.player_hands[player][card_index]

            if type(card) == int:
                card = number_to_pair(card)

            if self.cards_in_play[card[1] - 1] != card[0] - 1:  # The card cannot be played, so lose (or lose a life)
                return (self.cards_in_play, self.action_history)   # Return the cards in play and the action history so that the utility can be computed
            if self.remaining_turns_after_deck_end == 1:    # Available turns are finished, game ends
                cards_in_play = self.cards_in_play.copy()
                action_history = self.action_history.copy()
                cards_in_play[card[1] - 1] += 1    # Play the card ('cause it was playable)
                action_history.append('p.' + str(card))
                return (cards_in_play, action_history)   # Return the cards in play so that the utility can be computed

            child_state = self.copy()
            child_state.cards_in_play[card[1] - 1] += 1    # Play the card

            if min(child_state.cards_in_play) == self.highest_card_number:  # Win and end
                return (self.cards_in_play, self.action_history)   # Return the cards in play and the action history so that the utility can be computed

            if card[0] == self.highest_card_number: # Give one more tokens each time a "pile" is completed
                child_state.clue_tokens_available += 1

            if len(child_state.remaining_deck) > 0:
                new_card = child_state.remaining_deck.pop(0)
            else:
                new_card = (0, 0)
                if child_state.remaining_turns_after_deck_end == -1:
                    child_state.remaining_turns_after_deck_end = len(self.player_hands) - 1
                else:
                    child_state.remaining_turns_after_deck_end -= 1

            child_state.player_hands[player][card_index] = new_card
            child_state.player_clued_hands[player][card_index] = (0, 0)
            child_state.action_history.append('p.' + str(card))

            return child_state

        ################# DISCARD ACTION #################
        elif action[0] == 'd':
            card_index = int(action.split('.')[1])
            card = self.player_hands[player][card_index]

            if type(card) == int:
                card = number_to_pair(card)

            if self.remaining_turns_after_deck_end == 1:    # Available turns are finished, game ends
                return (self.cards_in_play, self.action_history)   # Return the cards in play and the action history so that the utility can be computed

            child_state = self.copy()
            child_state.discarded_cards.append(card)    # Discard the card

            if len(child_state.remaining_deck) > 0:
                new_card = child_state.remaining_deck.pop(0)
            else:
                new_card = (0, 0)
                if child_state.remaining_turns_after_deck_end == -1:
                    child_state.remaining_turns_after_deck_end = len(self.player_hands) - 1
                else:
                    child_state.remaining_turns_after_deck_end -= 1

            child_state.clue_tokens_available += 1
            child_state.player_hands[player][card_index] = new_card
            child_state.player_clued_hands[player][card_index] = (0, 0)
            child_state.action_history.append('d.' + str(card))

            return child_state

        ################# CLUE ACTION #################
        elif action[0] == 'c':
            target_player = int(action[1])
            clue_type = action[3]
            clue_value = int(action[4])

            if self.remaining_turns_after_deck_end == 1:    # Available turns are finished, game ends
                return (self.cards_in_play, self.action_history)   # Return the cards in play and the action history so that the utility can be computed

            child_state = self.copy()
            child_state.clue_tokens_available -= 1  # Consume a clue token

            for card_index in range(len(child_state.player_hands[target_player])):
                card = self.player_hands[target_player][card_index]

                if type(card) == int:
                    card = number_to_pair(card)

                old_clue = child_state.player_clued_hands[target_player][card_index]
                
                if clue_type == 'n' and card[0] == clue_value:    # Clue number
                    new_clue = (clue_value, old_clue[1])
                    child_state.player_clued_hands[target_player][card_index] = new_clue
                elif clue_type == 'c' and card[1] == clue_value:    # Clue color
                    new_clue = (old_clue[0], clue_value)
                    child_state.player_clued_hands[target_player][card_index] = new_clue

                if child_state.remaining_turns_after_deck_end > 0:
                    child_state.remaining_turns_after_deck_end -= 1 # Consume a turn

                child_state.clue_history.append(action + '-P' + str(player))
                child_state.action_history.append(action)

            return child_state

    def print(self):
        print("--- Hanabi State ---")
        print("Player hands = " + str(self.player_hands))
        print("Remaining deck = " + str(self.remaining_deck))
        print("Cards in play (highest per color) = " + str(self.cards_in_play))
        print("Discarded cards = " + str(self.discarded_cards))
        print("Clue tokens available = " + str(self.clue_tokens_available))
        print("Clue history = " + str(self.clue_history))
        print("Player clued hands = " + str(self.player_clued_hands))
        print("Action history = " + str(self.action_history))
        if self.remaining_turns_after_deck_end >= 0:
            print("Remaining turns after deck end = " + str(self.remaining_turns_after_deck_end))
        print("--- Hanabi State ---")

    def copy(self):
        return HanabiState(deepcopy(self.remaining_deck), deepcopy(self.player_hands), deepcopy(self.cards_in_play), 
                           deepcopy(self.discarded_cards), deepcopy(self.clue_tokens_available), 
                           deepcopy(self.clue_history), deepcopy(self.player_clued_hands), 
                           deepcopy(self.action_history), deepcopy(self.highest_card_number),
                           deepcopy(self.remaining_turns_after_deck_end))

    def createBaseState(deck, num_players, cards_per_player, num_colors, starting_tokens):
        deck = deck.copy()

        player_hands = []
        for p in range(num_players):
            player_hands.append(deck[:cards_per_player])
            deck = deck[cards_per_player:]

        highest_card_number = max(deck, key = lambda c: number_to_pair(c)[0] if type(c) == int else c[0])

        return HanabiState(remaining_deck = deck, player_hands = player_hands, 
                           cards_in_play = [0 for _ in range(num_colors)], discarded_cards = [], 
                           clue_tokens_available = starting_tokens, clue_history = [], action_history = [],
                           highest_card_number = highest_card_number,
                           player_clued_hands = [[(0, 0) for _ in range(cards_per_player)] for _ in range(num_players)])                           

def build_hanabi_tree(num_players, num_colors, color_distribution, num_cards_per_player, starting_tokens = 1,
                      compress_card_representation = False, display_progress = False,
                      utility_splitter = UtilitySplitter.Uniform):
    """
    Build a tree for the game of Hanabi with a given number of players, a given number of cards in each player's
    hand, given cards colors and with a given distribution of cards inside each color (e.g. [3, 2, 2, 2, 1] is 
    the common/regular one, with three 1s, two 2s etc for each color).
    If compress_card_representation is set to True, each card is represented by a single integer number instead
    of a tuple (number, color).
    """

    root = ChanceNode(0)

    tree = Tree(num_players, 0, root)

    all_cards = []
    for i in range(len(color_distribution)):
        for _ in range(color_distribution[i]):
            for c in range(num_colors):
                card = (i + 1, c + 1)
                if compress_card_representation:
                    card = pair_to_number(card[0], card[1])
                all_cards.append(card)

    deck_permutations = all_permutations(all_cards)
    deck_probability = 1 / len(deck_permutations)
    information_sets = {}

    i = 1
    for deck in deck_permutations:
        if display_progress:
            print("--- Processing deck " + str(deck) + " (" + str(i) + "/" + str(len(deck_permutations)) + ") ---")
        i += 1

        baseState = HanabiState.createBaseState(deck, num_players, num_cards_per_player, num_colors, starting_tokens)

        node_known_infos = baseState.toPlayerState(0)
        if node_known_infos in information_sets:
            information_set = information_sets[node_known_infos]
        else:
            information_set = -1

        node = tree.addNode(player = 0, parent = root, probability = deck_probability, 
                         actionName = str(deck), information_set = information_set)

        if information_set == -1:
            information_sets[node_known_infos] = node.information_set

        build_hanabi_state_tree(baseState, tree, information_sets, node, 0, utility_splitter)

    return tree

def build_hanabi_state_tree(hanabiState, tree, information_sets, parent_node, current_player, utility_splitter):
    actions = hanabiState.getLegalActions(current_player)
    next_player = (current_player + 1) % tree.numOfPlayers

    for action in actions:
        childState = hanabiState.getChildState(action)

        if type(childState) != HanabiState: # The game has ended, create a leaf
            (cards_in_play, action_history) = childState # In this case, childState contains the final board and the action history
            utility = build_hanabi_utility(tree.numOfPlayers, utility_splitter, cards_in_play, action_history)    
            tree.addLeaf(parent = parent_node, utility = utility, actionName = str(action))
            continue

        node_known_infos = childState.toPlayerState(next_player)
        if node_known_infos in information_sets:
            information_set = information_sets[node_known_infos]
        else:
            information_set = -1

        node = tree.addNode(player = next_player, parent = parent_node, 
                            actionName = str(action), information_set = information_set)

        if information_set == -1:
            information_sets[node_known_infos] = node.information_set

        build_hanabi_state_tree(childState, tree, information_sets, node, next_player, utility_splitter)

def build_hanabi_utility(num_players, utility_splitter, cards_in_play, action_history):
    if utility_splitter == UtilitySplitter.Uniform:
        return [sum(cards_in_play) / num_players for _ in range(num_players)]

    utility = [0 for _ in range(num_players)]

    for (c, r) in enumerate(cards_in_play):
        c += 1
        if r == 0:
            continue

        first_player = action_history.index('p.' + str((r, c))) % num_players
        utility[first_player] += r

    return utility

# Some possible deck structures:
#
#       1 color and [3, 2, 2, 2, 1] distribution (real one - but single color) -> 75600  deck permutations
#
#       1 color and [2, 1] distribution       -> 3  deck permutations
#       1 color and [3, 2] distribution       -> 10  deck permutations
#       1 color and [2, 2, 1] distribution    -> 30  deck permutations
#       1 color and [2, 2, 1, 1] distribution -> 180  deck permutations
#       1 color and [3, 2, 1] distribution    -> 60  deck permutations
#       1 color and [3, 2, 2] distribution    -> 210  deck permutations
#       1 color and [3, 2, 2, 1] distribution -> 1680 deck permutations
#       1 color and [4, 2, 2] distribution    -> 420  deck permutations
#
#       2 colors and [2, 1] distribution -> 180 deck permutations
#       2 colors and [1, 1, 1] distribution -> 720 deck permutations
#       2 colors and [3, 1] distribution -> 1120 deck permutations
#       2 colors and [2, 2] distribution -> 2520 deck permutations
#
#       3 colors and [1, 1] distribution -> 720 deck permutations
#
#       5 colors and [3, 2, 2, 2, 1] distribution (real one) -> roughly e+56 deck permutations
#                                 (119362714169794152069667854714196512499836511150699184128 deck permutations)