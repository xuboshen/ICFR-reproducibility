from data_structures.trees import Tree, Node, ChanceNode

def build_kuhn_tree(num_players, rank):
    """
    Build a tree for the game of Kuhn with a given number of players and a given number of ranks in the deck (i.e. how
    many cards).
    """

    root = ChanceNode(0)
    
    tree = Tree(num_players, 0, root)
    
    hands = build_all_possible_hands(num_players, list(range(rank)))
    print(hands)
    hand_probability = 1 / len(hands)
    for hand in hands:
        n = tree.addNode(0, parent = root, probability = hand_probability, actionName = str(hand))
        build_kuhn_hand_tree(hand, ['n'] * num_players, 0, n, tree, "")
        
    for i in range(len(hands)):
        for j in range(i+1, len(hands)):
            players_to_merge = []
            for p in range(num_players):
                if(hands[i][p] == hands[j][p]):
                    players_to_merge.append(p)
            create_information_sets(root.children[i], root.children[j], players_to_merge)
            
    return tree

def create_information_sets(node1, node2, players_to_merge):
    """
    Takes two identically shaped trees (rooted at node1 and node2) and put all the nodes
    belonging to players in players_to_merge in pairwise information sets.
    """

    if(node1.isLeaf()):
        return
    
    if(node1.player in players_to_merge):
        iset_id = min(node1.information_set, node2.information_set)
        node1.information_set = iset_id
        node2.information_set = iset_id
    
    for i in range(len(node1.children)):
        create_information_sets(node1.children[i], node2.children[i], players_to_merge)

def build_kuhn_hand_tree(hand, previous_moves, current_player, current_node, tree, seq: str):
    """
    Recursively build the subtree for the Kuhn game where the hand is fixed.
    """
    current_node.seq = str(hand[current_player] + 1) + seq

    actionPrefix = 'p' + str(current_player)
    num_players = len(hand)
    
    next_player = (current_player + 1) % num_players
    while(previous_moves[next_player] in ['b', 'f']):
        next_player = (next_player + 1) % num_players
    
    # There was a bet, so I can only call or fold
    if('b' in previous_moves):
        # If the current and the next player are the same, we are at the last decision node of the game
        if(current_player == next_player):
            previous_moves[current_player] = 'b'
            tree.addLeaf(current_node, kuhn_utility(hand, previous_moves), actionName = actionPrefix + 'b')
            
            previous_moves[current_player] = 'f'
            tree.addLeaf(current_node, kuhn_utility(hand, previous_moves), actionName = actionPrefix + 'f')
            
            return
        
        callNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'b')
        previous_moves[current_player] = 'b'
        build_kuhn_hand_tree(hand, previous_moves.copy(), next_player, callNode, tree, seq + 'B')
        
        foldNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'f')
        previous_moves[current_player] = 'f'
        build_kuhn_hand_tree(hand, previous_moves.copy(), next_player, foldNode, tree, seq + 'P')
    
    else: # No bet yet, so I can check or bet
        previous_moves[current_player] = 'c'
        if(len(list(filter(lambda el: el == 'c', previous_moves))) == num_players):
            tree.addLeaf(current_node, kuhn_utility(hand, previous_moves), actionName = actionPrefix + 'c')
        else:        
            checkNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'c')
            build_kuhn_hand_tree(hand, previous_moves.copy(), next_player, checkNode, tree, seq + 'P')
            
        betNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'b')
        previous_moves[current_player] = 'b'
        build_kuhn_hand_tree(hand, previous_moves.copy(), next_player, betNode, tree, seq + 'B')

def kuhn_utility(hand, moves):
    """
    Get the utility of a Kuhn game given the hand and how the players have played.
    """

    num_players = len(hand)
    
    pot = num_players + len(list(filter(lambda el: el == 'b', moves)))
    showdown_participants = [p for p in range(num_players) if moves[p] != 'f']
    winner = max(showdown_participants, key = lambda el: hand[el])
    
    utility = [-1] * num_players
    for p in range(num_players):
        if(p == winner):
            utility[p] += pot
        if(moves[p] == 'b'):
            utility[p] -= 1
            
    return utility

def build_all_possible_hands(num_players, ranks):
    """
    Build all the possible hands for the game of Kuhn with a given number of players and a given set of cards.
    """

    if(num_players <= 0):
        return [[]]
    
    smaller_hands = build_all_possible_hands(num_players-1, ranks)
    hands = []
    
    for hand in smaller_hands:
        remaining_ranks = list(filter(lambda el: el not in hand, ranks))
        for r in remaining_ranks:
            hands.append(hand + [r])
            
    return hands