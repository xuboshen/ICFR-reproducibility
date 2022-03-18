from data_structures.cfr_trees import CFRJointStrategy
from functools import reduce
import time

def sampleCFR(node, player, pi, action_plan):
    """
    SCFR algorithm.
    node = the current node the algorithm is in.
    player = the player for which the algorithm is being run.
    pi = a probability vector containing, for each player, the probability to reach the current node.
    action_plan = the sampled action plan.
    """

    n_players = len(pi)
    node.visits += reduce(lambda x, y: x * y, pi, 1)
    
    if(node.isChance()):
        return sampleCFR(node.children[node.sampleAction()], player, pi, action_plan)
    
    if(node.isLeaf()):
        return node.utility[player]        
    
    iset = node.information_set
    v = 0
    v_alt = [0 for a in node.children]
    
    sampled_action = action_plan[iset.id]
    
    if(max(pi) == 0):
        return sampleCFR(node.children[sampled_action], player, pi, action_plan)
    
    for a in range(len(node.children)):
        if(a == sampled_action):
            v_alt[a] = sampleCFR(node.children[a], player, pi, action_plan)
        else:
            old_pi = pi[iset.player]
            pi[iset.player] = 0
            v_alt[a] = sampleCFR(node.children[a], player, pi, action_plan)
            pi[iset.player] = old_pi
        
    v = v_alt[sampled_action]
    
    if(iset.player == player):
        pi_other = 1
        for i in range(len(pi)):
            if(i != player):
                pi_other *= pi[i]

        for a in range(len(node.children)):
            ##### CFR+ #####
            iset.cumulative_regret[a] = max(iset.cumulative_regret[a] + pi_other * (v_alt[a] - v), 0)
            
            ##### This is useless for NFCCE #####
            iset.cumulative_strategy[a] += pi[player] * iset.current_strategy[a]
    
    return v

def SolveWithSampleCFR(cfr_tree, iterations, perc = 10, show_perc = False, checkEveryIteration = -1,
                       bootstrap_iterations = 0, bound_joint_size = True, check_callback = None):
    """
    Find a NFCCE in a given extensive-form tree with the SCFR algorithm, run for a given amount of iterations.
    If show_perc is True, every perc% of the target iterations are done a message is shown on the console.
    checkEveryIteration is the frequency to collect convergence data, such as the epsilon or the elapsed time.
    If bound_joint_size is True the joint strategy is created with space for at most 2 * |A| plans, otherwise it is
    created with an unbounded space.
    """

    if(bound_joint_size):
        jointStrategy = CFRJointStrategy(cfr_tree.numOfActions * 2)
    else:
        jointStrategy = CFRJointStrategy(-1)
    player_count = cfr_tree.numOfPlayers
    
    # Graph data
    graph_data = []

    start_time = time.time()
    last_checkpoint_time = start_time
    
    for i in range(1, iterations+bootstrap_iterations+1):
        t = i - bootstrap_iterations

        if((t+1) > 0 and show_perc and (t+1) % (iterations / 100 * perc) == 0):
            print(str((t+1) / (iterations / 100 * perc) * perc) + "%")
            
        # Sample a joint action plan from the current strategies
        action_plan = cfr_tree.sampleActionPlan()
            
        # Run CFR for each player
        for p in range(player_count):
            sampleCFR(cfr_tree.root, p, [1] * player_count, action_plan)
            
        # Update the current strategy for each information set
        for infoset in cfr_tree.information_sets.values():
            infoset.updateCurrentStrategy()
            
        if(i <= bootstrap_iterations):
            continue # Neither update the joint, nor check the equilibrium

        jointStrategy.addActionPlan(CFRJointStrategy.reduceActionPlan(action_plan, cfr_tree))
        
        if(checkEveryIteration > 0 and t % checkEveryIteration == 0):
            data = {'epsilon': cfr_tree.checkEquilibrium(jointStrategy),
                    'absolute_joint_size': jointStrategy.frequencyCount,
                    'joint_support_size': len(jointStrategy.plans),
                    'relative_joint_size': jointStrategy.frequencyCount / t,
                    'max_plan_frequency': max(jointStrategy.plans.values()),
                    'iteration_number': t,
                    'duration': time.time() - last_checkpoint_time,
                    'utility': cfr_tree.getUtility(jointStrategy)}
            graph_data.append(data)

            if(check_callback != None):
                check_callback(data)

            last_checkpoint_time = time.time()
        
    return {'utility': cfr_tree.getUtility(jointStrategy), 'joint': jointStrategy, 'graph_data': graph_data,
            'tot_time': time.time() - start_time}