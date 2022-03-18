from functools import reduce
import time

def CFR(node, player, pi, use_cfr_plus = False):
    """
    Vanilla CFR algorithm.
    """

    n_players = len(pi)
    node.visits += reduce(lambda x, y: x * y, pi, 1)

    if node.isChance():
        res = 0
        for (p, child) in zip (node.distribution, node.children):
            res += CFR(child, player, pi, use_cfr_plus) * p
        return res
    
    if(node.isLeaf()):
        return node.utility[player]
    
    iset = node.information_set
    v = 0
    v_alt = [0 for a in node.children]
    
    for a in range(len(node.children)):
        
        old_pi = pi[iset.player]
        pi[iset.player] *= iset.current_strategy[a]
        v_alt[a] = CFR(node.children[a], player, pi)        
        pi[iset.player] = old_pi
            
        v += v_alt[a] * iset.current_strategy[a]
    
    if(iset.player == player):
        pi_other = 1
        for i in range(len(pi)):
            if(i != player):
                pi_other *= pi[i]

        for a in range(len(node.children)):
            if use_cfr_plus:
                #iset.cumulative_regret[a] += pi[player] * max(0, (v_alt[a] - v)) # CFR+
                iset.cumulative_regret[a] = max(iset.cumulative_regret[a] + pi_other * (v_alt[a] - v), 0)
            else:
                #iset.cumulative_regret[a] += pi[player] * (v_alt[a] - v)
                iset.cumulative_regret[a] += pi_other * (v_alt[a] - v)
            iset.cumulative_strategy[a] += pi[player] * iset.current_strategy[a]
    
    return v

def SolveWithCFR(cfr_tree, iterations, perc = 10, show_perc = True, checkEveryIteration = -1, 
                 check_callback = None, use_cfr_plus = False):
    # Graph data
    graph_data = []

    start_time = time.time()
    last_checkpoint_time = start_time

    player_count = cfr_tree.numOfPlayers

    for i in range(1, iterations + 1):
        if(show_perc and i % (iterations / 100 * perc) == 0):
            print(str(i / (iterations / 100 * perc) * perc) + "%")

        # Run CFR for each player
        for p in range(player_count):
            CFR(cfr_tree.root, p, [1] * player_count, use_cfr_plus)
            
        # Update the current strategy for each information set
        for infoset in cfr_tree.information_sets.values():
            infoset.updateCurrentStrategy()

        if(checkEveryIteration > 0 and i % checkEveryIteration == 0):
            data = {'epsilon': cfr_tree.checkMarginalsEpsilon(),
                    'iteration_number': i,
                    'duration': time.time() - last_checkpoint_time,
                    'utility': cfr_tree.root.getExpectedUtility()}
            graph_data.append(data)

            if(check_callback != None):
                check_callback(data)
                
            last_checkpoint_time = time.time()
        # print('test:', time.time() - start_time)
    return {'utility': cfr_tree.root.getExpectedUtility(), 'graph_data': graph_data, 'tot_time': time.time() - start_time}
