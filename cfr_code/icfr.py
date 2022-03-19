from functools import reduce
from random import sample
from data_structures.regret_minimizers import InternalRM, ExternalRM
import time
import random
import matplotlib.pyplot as plt
import numpy as np

from data_structures.cfr_trees import CFRJointStrategy

def drawing(results, iterations):
    fig, ax = plt.subplots()
    ax.plot(range(1, iterations + 1), results)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Epsilon(delta(mu_T))")
    # ax.set_ylim(bottom = 1e-7, top = 1e-1)
    ax.set_xscale('log')
    ax.set_yscale('log')
    # ax.legend("K34")
    ax.legend("K33")
    # ax.set_yticks([1, 1e-1, 1e-2, 1e-3, 1e-4, 1e-5])
    
    # fig.savefig("K3_4_ylog_epsilon_results3.png", dpi=200)
    fig.savefig("ddebug", dpi=200)

def Merge(d1, d2):
    # if (d1 is None):
    #     return d2
    # elif (d2 is None):
    #     return d1
    # else:
    d2.update(d1)
    return d2

def getEpsilon(node, p, action_plan):
    epsilon = 0
    if (node.isChance()):
        for a in range(len(node.children)):
            epsilon = np.maximum(epsilon, getEpsilon(node.children[a], p * node.distribution[a], action_plan))
        return epsilon
    if (node.isLeaf()):
        return 0
    iset = node.information_set
    player = iset.player
    r = random.random()
    mu = [r, 1 - r]

    epsilon = p * node.getEpsilon(action_plan, mu, player)
    for a in range(len(node.children)):
        epsilon = np.maximum(epsilon, getEpsilon(node.children[a], p * node.information_set.getAverageStrategy()[a], action_plan))
    return epsilon

def init(node):
    if (node.isChance()):
        for child in node.children:
            init(child)
        return
    if (node.isLeaf()):
        return
    iset = node.information_set
    iset.externalsigma = ""
    iset.reachability = -1
    iset.utility = [0] * len(node.children)
    for a in range(len(node.children)):
        init(node.children[a])

def createExternalRM(node, exiset):
    if (node.isLeaf()):
        return
    iset = node.information_set
    iset.rechability = 0
    if exiset.player == iset.player:
        iset.externalsigma = exiset.externalsigma
        if (exiset.externalsigma + '.' + str(iset.id) not in iset.exRM.keys()):
            iset.exRM[exiset.externalsigma + '.' + str(iset.id)] = ExternalRM()
    for a in range(len(node.children)):
        createExternalRM(node.children[a], exiset)

def ICFR_sampling(node):
    """
    ICFR sampling algorithm.
    """
    # {infomationset_id: sqampleAction}
    action_plan = {}
    if node.isChance():
        # print("begins", node.id, node.isChance())
        for child in node.children:
            action_plan = Merge(action_plan, ICFR_sampling(child))
            
        return action_plan
    
    if (node.isLeaf()):
        return {}
    # print("normal node", node.id, node.isChance())
    iset = node.information_set
    # print(iset, iset.nodes[0].id, iset.nodes[1].id, len(iset.nodes))
    
    if (iset.reachability in [1, -1]):
        iset.reachability = 1
        sampledAction = iset.inRM.recommend()
        iset.externalsigma = str(iset.id) + '.' + str(sampledAction)
        for a in range(len(node.children)):
            if (a != sampledAction):
                createExternalRM(node.children[a], iset)
    else:
        sampledAction = iset.exRM[iset.externalsigma + '.' + str(iset.id)].recommend()
    iset.mu_T[sampledAction] = iset.mu_T[sampledAction] + 1

    action_plan[iset.id] = sampledAction

    for a in range(len(node.children)):
        action_plan = Merge(action_plan, ICFR_sampling(node.children[a]))
    return action_plan

def ICFR_Observe(node, action_plan):
    if (node.isChance()):
        for child in node.children:
            ICFR_Observe(child, action_plan)
        return
    if (node.isLeaf()):
        return
    iset = node.information_set
    sampledAction = action_plan[iset.id]
    for a in range(len(node.children)):
        action_plan[iset.id] = a
        iset.utility[a] = node.utilityFromActionPlan(action_plan)[iset.player]
        action_plan[iset.id] = sampledAction
        ICFR_Observe(node.children[a], action_plan)

def ICFR_Update(node):
    if (node.isChance()):
        for child in node.children:
            ICFR_Update(child)
        return
    if (node.isLeaf()):
        return
    iset = node.information_set
    if (iset.reachability):
        iset.inRM.observe(iset.utility)
    else:
        iset.exRM[iset.externalsigma + '.' + str(iset.id)].observe(iset.utility)
    for a in range(len(node.children)):
        ICFR_Update(node.children[a])

def SolveWithICFR(icfr_tree, iterations, perc = 10, show_perc = True, checkEveryIteration = -1, 
                 check_callback = None):
    # Graph data
    graph_data = []

    start_time = time.time()
    last_checkpoint_time = start_time

    # player_count = icfr_tree.numOfPlayers

    for i in range(1, iterations + 1):
        if(show_perc and i % (iterations / 100 * perc) == 0):
            print(str(i / (iterations / 100 * perc) * perc) + "%")
        init(icfr_tree.root)
        # Run ICFR for each player
        # to sample internal for each infomation set for each player
        action_plan = ICFR_sampling(icfr_tree.root) # node.id : sampled_action
        # print(action_plan, len(action_plan))
        ICFR_Observe(icfr_tree.root, action_plan)
        ICFR_Update(icfr_tree.root)
        # Update the current strategy for each information set
        # for infoset in icfr_tree.information_sets.values():
        #     infoset.updateCurrentStrategy()
        # temp_iteration = 5
        # temp_max = 0
        # while (temp_iteration):
        #     r = random.random()
        #     mu = [r, 1 - r]
        #     temp_max = np.maximum(temp_max, np.max(icfr_tree.root.getEpsilon(action_plan, mu)))
        #     temp_iteration -= 1
        # graph_data += [np.max(icfr_tree.root.getEpsilon(action_plan, mu))]        
        eps = getEpsilon(icfr_tree.root, 1, action_plan)
        graph_data += [eps]
        if(checkEveryIteration > 0 and i % checkEveryIteration == 0):
            icfr_tree.root.T = i
            data = {'epsilon': icfr_tree.checkMarginalsEpsilon(),
                    'iteration_number': i,
                    'duration': time.time() - last_checkpoint_time,
                    'utility': icfr_tree.root.getExpectedUtility()}
            # graph_data.append(data)
            print('utility:', icfr_tree.root.getExpectedUtility())
            print('epsilon:', eps)

            if(check_callback != None):
                check_callback(data)
                
            last_checkpoint_time = time.time()
        # print('test:', time.time() - start_time)
    print("epsilon:",  graph_data)
    drawing(graph_data, iterations)
    # print(len(graph_data), iterations)
    return {'utility': icfr_tree.root.getExpectedUtility(), 'graph_data': graph_data, 'tot_time': time.time() - start_time}