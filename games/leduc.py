from data_structures.trees import Tree, Node, ChanceNode
import copy

def build_leduc_tree(num_players, num_of_suits, num_of_ranks, betting_parameters):
    """
    Build a tree for the game of Leduc with a given number of players, suits, ranks and betting parameters.
    """

    root = ChanceNode(0)
    
    tree = Tree(num_players, 0, root)
    
    hands = build_all_possible_hands(num_players, [c for c in range(1,num_of_ranks+1) for _ in range(num_of_suits)])
    hand_probability = 1 / len(hands)
    all_nodes = []

    for hand in hands:
        n = tree.addNode(0, parent = root, probability = hand_probability, actionName = str(hand))
        all_nodes.append(n)
        empty_previous_moves = [['n' for _ in range(num_players)], ['n' for _ in range(num_players)]]
        all_nodes += build_leduc_hand_tree(hand, empty_previous_moves, 0, 0, n, betting_parameters, tree)
        
    # Merge nodes into infosets based on the available information at each node
    for i in range(len(hands)):
        for j in range(i+1, len(hands)):
            create_information_sets(root.children[i], root.children[j])
            
    return tree

def build_leduc_hand_tree(hand, previous_moves, current_player, current_round, current_node, betting_parameters, tree):
    """
    Recursively build the subtree for the Leduc game where the hand is fixed.
    """

    if(current_round == 0):
        current_node.known_information = (hand[current_player], -1)
    else:
        current_node.known_information = (hand[current_player], hand[len(hand) - 1])

    actionPrefix = 'p' + str(current_player)
    num_players = len(hand)-1
    
    next_player = (current_player + 1) % num_players

    while(previous_moves[current_round][next_player] in ['b', 'f'] or (current_round == 1 and previous_moves[0][next_player] == 'f')):
        next_player = (next_player + 1) % num_players

    nodes = []
    
    # There was a bet, so I can only call or fold
    if('b' in previous_moves[current_round]):
        # If the current and the next player are the same, we are at the last decision node of this round
        if(current_player == next_player):
            if(current_round == 0):
                last_player = current_player

                # ---------------------------------------------
                # CASE 1: the last player of round 1 calls
                # ---------------------------------------------
                non_folded_players = [p for p in range(num_players) if previous_moves[0][p] != 'f']
                current_player = non_folded_players[0]
                next_player = non_folded_players[1]
                current_round = 1
                actionPrefix = 'p' + str(current_player)

                previous_moves[0][last_player] = 'b'
                lastCallNode = tree.addNode(current_player, parent = current_node, actionName = actionPrefix + 'b')
                lastCallNode.known_information = (hand[current_player], hand[len(hand) - 1])
                nodes.append(lastCallNode)

                previous_moves[current_round][current_player] = 'c'  
                checkNode1 = tree.addNode(next_player, parent = lastCallNode, actionName = actionPrefix + 'c')
                nodes.append(checkNode1)
                nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, checkNode1, betting_parameters, tree)

                previous_moves[current_round][current_player] = 'b'
                betNode1 = tree.addNode(next_player, parent = lastCallNode, actionName = actionPrefix + 'b')
                nodes.append(betNode1)
                nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, betNode1, betting_parameters, tree)

                # ---------------------------------------------
                # CASE 2: the last player of round 1 folds
                # ---------------------------------------------

                previous_moves[1][current_player] = 'n' # Clear data from CASE 1
                if(len(non_folded_players) == 2):
                    # I am one of the two played that have not folded during the first round, so if I fold the game is over
                    previous_moves[0][last_player] = 'f'
                    foldLeaf = tree.addLeaf(current_node, leduc_utility(hand, previous_moves, betting_parameters), actionName = actionPrefix + 'f')
                else:
                    if(last_player == non_folded_players[0]):
                        current_player = non_folded_players[1]
                        next_player = non_folded_players[2]
                    elif(last_player == non_folded_players[1]):
                        next_player = non_folded_players[2]

                    previous_moves[0][last_player] = 'f'
                    lastFoldNode = tree.addNode(current_player, parent = current_node, actionName = actionPrefix + 'f')
                    lastFoldNode.known_information = (hand[current_player], hand[len(hand) - 1])
                    nodes.append(lastFoldNode)

                    previous_moves[current_round][current_player] = 'c'
                    checkNode2 = tree.addNode(next_player, parent = lastFoldNode, actionName = actionPrefix + 'c')
                    nodes.append(checkNode2)
                    nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, checkNode2, betting_parameters, tree)
                    
                    previous_moves[current_round][current_player] = 'b'
                    betNode2 = tree.addNode(next_player, parent = lastFoldNode, actionName = actionPrefix + 'b')
                    nodes.append(betNode2)
                    nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, betNode2, betting_parameters, tree)

            else:
                # We are at the last move of the last round, so generate leaves
                previous_moves[current_round][current_player] = 'b'
                l = tree.addLeaf(current_node, leduc_utility(hand, previous_moves, betting_parameters), actionName = actionPrefix + 'b')
                nodes.append(l)

                previous_moves[current_round][current_player] = 'f'
                l = tree.addLeaf(current_node, leduc_utility(hand, previous_moves, betting_parameters), actionName = actionPrefix + 'f')
                nodes.append(l)
            
            return nodes
        
        callNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'b')
        nodes.append(callNode)
        previous_moves[current_round][current_player] = 'b'
        nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, callNode, betting_parameters, tree)
        
        foldNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'f')
        nodes.append(foldNode)
        previous_moves[current_round][current_player] = 'f'
        nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, foldNode, betting_parameters, tree)
    
    else: # No bet yet, so I can check or bet
        previous_moves[current_round][current_player] = 'c'
        num_players_that_checked = len(list(filter(lambda el: el == 'c', previous_moves[current_round])))
        num_players_in_game = len(list(filter(lambda el: el != 'f', previous_moves[0]))) if current_round == 1 else num_players
        if(num_players_that_checked == num_players_in_game):
            if(current_round == 0):

                lastCheckNode = tree.addNode(0, parent = current_node, actionName = actionPrefix + 'c')
                lastCheckNode.known_information = (hand[0], hand[len(hand) - 1])
                nodes.append(lastCheckNode)

                # This is the start of the second betting round, so we restart from the check/bet choice of the first player
                new_current_player = 0
                new_next_player = 1
                new_current_round = 1
                new_actionPrefix = 'p' + str(new_current_player)
                previous_moves[new_current_round][new_current_player] = 'c'  
                checkNode = tree.addNode(new_next_player, parent = lastCheckNode, actionName = new_actionPrefix + 'c')
                nodes.append(checkNode)
                nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), new_next_player, new_current_round, checkNode, betting_parameters, tree)
                    
                previous_moves[new_current_round][new_current_player] = 'b'
                betNode = tree.addNode(new_next_player, parent = lastCheckNode, actionName = new_actionPrefix + 'b')
                nodes.append(betNode)
                nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), new_next_player, new_current_round, betNode, betting_parameters, tree)

                previous_moves[new_current_round][new_current_player] = 'n' # Cleanup for the code after the end of the if
            else:
                l = tree.addLeaf(current_node, leduc_utility(hand, previous_moves, betting_parameters), actionName = actionPrefix + 'c')
                nodes.append(l)
        else:        
            checkNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'c')
            nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, checkNode, betting_parameters, tree)
            nodes.append(checkNode)
            
        betNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'b')
        nodes.append(betNode)
        previous_moves[current_round][current_player] = 'b'
        nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, betNode, betting_parameters, tree)

    return nodes

def create_information_sets(node1, node2):
    """
    Takes two identically shaped trees (rooted at node1 and node2) and put all the nodes
    belonging to the same player and having access to the same information in pairwise information sets.
    """

    if(node1.isLeaf()):
        return
    
    if(node1.player == node2.player and node1.known_information == node2.known_information):
        iset_id = min(node1.information_set, node2.information_set)
        node1.information_set = iset_id
        node2.information_set = iset_id
    
    for i in range(len(node1.children)):
        create_information_sets(node1.children[i], node2.children[i])

def build_all_possible_hands(num_players, cards):
    """
    Build all the possible hands for the game of Leduc with a given number of players and a given set of cards.
    Returns a list of lists, where each inner list has one card per player plus one public card.
    """

    unique_cards = list(set(cards))

    if(num_players <= 0):
        return [[card] for card in unique_cards]
    
    smaller_hands = build_all_possible_hands(num_players-1, cards)
    hands = []
    
    for hand in smaller_hands:

        for card in hand:
            cards.remove(card)

        unique_remaining_cards = list(set(cards))

        for card in unique_remaining_cards:
            hands.append(hand + [card])

        for card in hand:
            cards.append(card)
            
    return hands

def leduc_utility(hand, previous_moves, betting_parameters):
    """
    Get the utility of a Leduc game given the hand, how the players have played and the betting parameters.
    """

    num_players = len(hand) - 1
    public_card = hand[num_players]

    pot = num_players + len(list(filter(lambda el: el == 'b', previous_moves[0]))) * betting_parameters[0] + \
                        len(list(filter(lambda el: el == 'b', previous_moves[1]))) * betting_parameters[1]
    showdown_participants = [p for p in range(num_players) if previous_moves[0][p] != 'f' and previous_moves[1][p] != 'f']
    winners = list(filter(lambda p: hand[p] == public_card, showdown_participants))

    if(len(winners) == 0):
        max_card = max([hand[i] for i in showdown_participants])
        winners = list(filter(lambda p: hand[p] == max_card, showdown_participants))

    utility = [-1] * num_players
    for p in range(num_players):
        if previous_moves[0][p] == 'b':
            utility[p] -= betting_parameters[0]        
        if previous_moves[1][p] == 'b':
            utility[p] -= betting_parameters[1]
        if(p in winners):
            utility[p] += pot / len(winners)

    return utility