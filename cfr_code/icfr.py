from functools import reduce
from random import sample
from re import L
from venv import create
from data_structures.regret_minimizers import InternalRM, ExternalRM
import time
import random
import matplotlib.pyplot as plt
import numpy as np
from utilities.drawing import draw_tree

from data_structures.cfr_trees import CFRJointStrategy
# ok

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
    fig.savefig("ddebug.png", dpi=200)
# ok
def Merge(d1, d2):
    # if (d1 is None):
    #     return d2
    # elif (d2 is None):
    #     return d1
    # else:
    d2.update(d1)
    return d2
# not ok --> ok
def addMerge(d1, d2):
    for k in d2.keys():
        if (k in d1.keys()):
            d1[k] += d2[k]
        else:
            d1[k] = d2[k]
    return d1
# ok
def getEpsilon(node, p, action_plan):
    epsilon = {}
    if (node.isChance()):
        for a in range(len(node.children)):
            epsilon = addMerge(epsilon, getEpsilon(node.children[a], p * node.distribution[a], action_plan))
        # epsilon = addMerge(epsilon, getEpsilon(node.children[node.action], p * node.distribution[node.action], action_plan))
        return epsilon
    if (node.isLeaf()):
        return {}
    iset = node.information_set
    player = iset.player
    num_mu = 10
    eps = -1
    while (num_mu):
        r = random.random()
        mu = [r, 1 - r]
        eps = max(p * node.getEpsilon(action_plan, mu, player), eps)
        num_mu -= 1
    epsilon[iset.id] = eps
    for a in range(len(node.children)):
        epsilon = addMerge(epsilon, getEpsilon(node.children[a], p * node.information_set.getAverageStrategy()[a], action_plan))
    return epsilon
# ok
def init(node):
    if (node.isChance()):
        for child in node.children:
            init(child)
        return
    if (node.isLeaf()):
        return
    iset = node.information_set
    iset.externalsigma = ""
    iset.tag = False
    iset.update = False
    iset.action = -1
    iset.reachability = -1
    # iset.utility = [0] * len(node.children)
    iset.utility = np.zeros(len(node.children))
    for a in range(len(node.children)):
        init(node.children[a])
# ok
def createExternalRM(node, exiset):
    if (node.isLeaf()):
        return
    iset = node.information_set
    if exiset.player == iset.player:
        iset.reachability = 0
        iset.externalsigma = exiset.externalsigma
        if (exiset.externalsigma + '.' + str(iset.id) not in iset.exRM.keys()):
            iset.exRM[exiset.externalsigma + '.' + str(iset.id)] = ExternalRM(iset.action_count)
    for a in range(len(node.children)):
        createExternalRM(node.children[a], exiset)
# ok
def ICFR_sampling(node):
    """
    ICFR sampling algorithm.
    """
    # {infomationset_id: sqampleAction}
    action_plan = {}
    if node.isChance():
        # print("begins", node.id, node.isChance())
        for child in node.children:
            action_plan = Merge(action_plan, ICFR_sampling(child)[0])
        # action = node.sampleAction()
        # action_plan = Merge(action_plan, ICFR_sampling(node.children[action]))
            
        return action_plan
    
    if (node.isLeaf()):
        return {}, node
    # print("normal node", node.id, node.isChance())
    iset = node.information_set
    # print(iset, iset.nodes[0].id, iset.nodes[1].id, len(iset.nodes))
    if (iset.reachability == 1):
        action_plan[iset.id] = iset.action
        # for a in range(len(node.children)):
        #     if (a != iset.action):
        #         createExternalRM(node.children[a], iset)
        for a in range(len(node.children)):
            ac, leaf = ICFR_sampling(node.children[a])
            iset.visits[leaf] += 1
            action_plan = Merge(action_plan, ac)
        return action_plan

    elif (iset.reachability == -1):
        iset.reachability = 1
        # print(iset.id, iset.reachability)
        sampledAction = iset.inRM.recommend()
        iset.action = sampledAction
        # print(iset.inRM.regretSum)
        iset.externalsigma = str(iset.id) + '.' + str(sampledAction)
        for a in range(len(node.children)):
            if (a != sampledAction):
                createExternalRM(node.children[a], iset)
    else:
        if (not iset.tag):
            # print(iset.id, iset.reachability)
            sampledAction = iset.exRM[iset.externalsigma + '.' + str(iset.id)].recommend()
            iset.action = sampledAction
        
        # print(iset.exRM[iset.externalsigma + '.' + str(iset.id)].regretSum)
    if (not iset.tag):
        action_plan[iset.id] = sampledAction
        iset.action = sampledAction
        # iset.mu_T[sampledAction] = iset.mu_T[sampledAction] + 1
        iset.tag = True
    # print("mu_T:{} of infoset:{}".format(iset.mu_T, iset.id))

    for a in range(len(node.children)):
        ac, leaf = ICFR_sampling(node.children[a])
        if (iset.reachability is not 0):
            iset.visits[leaf] += 1
        action_plan = Merge(action_plan, ac)
    return action_plan, leaf
# ???
def ICFR_Observe(node, action_plan):
    if (node.isChance()):
        for child in node.children:
            ICFR_Observe(child, action_plan)
        # ICFR_Observe(node.children[node.action], action_plan)
        return
    if (node.isLeaf()):
        return
    iset = node.information_set
    sampledAction = action_plan[iset.id]
    for a in range(len(node.children)):
        action_plan[iset.id] = a
        # ???
        iset.utility[a] += node.icfrutilityFromActionPlan(action_plan, iset)[iset.player]
        action_plan[iset.id] = sampledAction
        ICFR_Observe(node.children[a], action_plan)
# ???
def ICFR_Update(node):
    if (node.isChance()):
        for child in node.children:
            ICFR_Update(child)
        # ICFR_Update(node.children[node.action])
        return
    if (node.isLeaf()):
        return
    iset = node.information_set
    if (iset.update is False):
        if (iset.reachability):
            iset.inRM.observe(iset.utility)
        else:
            iset.exRM[iset.externalsigma + '.' + str(iset.id)].observe(iset.utility)
        iset.update = True
        for a in range(len(node.children)):
            ICFR_Update(node.children[a])
    else:
        for a in range(len(node.children)):
            ICFR_Update(node.children[a])
# ok
def SolveWithICFR(icfr_tree, iterations, perc = 10, show_perc = True, checkEveryIteration = -1, 
                 check_callback = None):
    # Graph data
    graph_data = []

    start_time = time.time()
    last_checkpoint_time = start_time

    # player_count = icfr_tree.numOfPlayers

    for i in range(1, iterations + 1):
        cnt = 0
        if(show_perc and i % (iterations / 100 * perc) == 0):
            print(str(i / (iterations / 100 * perc) * perc) + "%")
        init(icfr_tree.root)
        # Run ICFR for each player
        # to sample internal for each infomation set for each player
        action_plan, _ = ICFR_sampling(icfr_tree.root) # node.id : sampled_action
        # print(action_plan, len(action_plan))
        ICFR_Observe(icfr_tree.root, action_plan)
        ICFR_Update(icfr_tree.root)
        # Update the current strategy for each information set
        # for infoset in icfr_tree.information_sets.values():
        #     infoset.updateCurrentStrategy()
        # graph_data += [np.max(icfr_tree.root.getEpsilon(action_plan, mu))]        
        eps = getEpsilon(icfr_tree.root, 1, action_plan)
        graph_data += [max(eps.values())]
        if(checkEveryIteration > 0 and i % checkEveryIteration == 0):
            icfr_tree.root.T = i
            data = {'epsilon': icfr_tree.checkMarginalsEpsilon(),
                    'iteration_number': i,
                    'duration': time.time() - last_checkpoint_time,
                    'utility': icfr_tree.root.getExpectedUtility()}
            # graph_data.append(data)
            print('utility:', icfr_tree.root.getExpectedUtility())
            # print('epsilon:', eps)

            if(check_callback != None):
                check_callback(data)
                
            last_checkpoint_time = time.time()
        # print('test:', time.time() - start_time)
    # print("epsilon:",  graph_data)
    drawing(graph_data, iterations)
    d = icfr_tree.information_sets
    # for id in d:
        # print(d[id].mu_T / np.sum(d[id].mu_T))
    # draw_tree(icfr_tree)
    # print(len(graph_data), iterations)
    return {'utility': icfr_tree.root.getExpectedUtility(), 'graph_data': graph_data, 'tot_time': time.time() - start_time}