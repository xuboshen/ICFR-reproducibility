from functools import reduce
import math
from random import sample
from re import L
from tkinter.tix import DirTree
from venv import create

from cv2 import norm
from cfr_code.cfr import CFR
from data_structures.regret_minimizers import InternalRM, ExternalRM
import time
import random
import matplotlib.pyplot as plt
import numpy as np
# from utilities.drawing import draw_tree

from data_structures.cfr_trees import CFRInformationSet, CFRJointStrategy, CFRNode, CFRTree
# ok

def drawing(results, iterations):
    fig, ax = plt.subplots()
    ax.plot(iterations, results)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Epsilon(delta(mu_T))")
    # ax.set_ylim(bottom = 1e-7, top = 1e-1)
    ax.set_xscale('log')
    ax.set_yscale('log')
    # ax.legend("K34")
    ax.legend("K33")
    # ax.set_yticks([1, 1e-1, 1e-2, 1e-3, 1e-4, 1e-5])
    
    ax.set_xlim([1, 1e4])
    ax.set_ylim([1e-4, 1])
    # fig.savefig("K3_4_ylog_epsilon_results3.png", dpi=200)
    fig.savefig("KuhnPoker_3_3.png", dpi=200)
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
        if (k in d1.keys() and d2[k] > d1[k]):
            d1[k] = d2[k]
        else:
            d1[k] = d2[k]
    return d1
# ok
"""
# def getEpsilon(root, node, t):
#     epsilon = {}
#     if (node.isChance()):
#         for a in range(len(node.children)):
#             epsilon = addMerge(epsilon, getEpsilon(root, node.children[a], t))
#         # epsilon = addMerge(epsilon, getEpsilon(node.children[node.action], p * node.distribution[node.action], action_plan))
#         return epsilon
#     if (node.isLeaf()):
#         return {}
#     iset = node.information_set
#     player = iset.player
#     for a in range(len(node.children)):
#         num_mu = 5
#         eps = -1
#         while (num_mu):
#             eps = max(node.getEpsilon(root, t, a, player), eps)
#             num_mu -= 1
#         epsilon[iset.id] = eps
#         epsilon = addMerge(epsilon, getEpsilon(root, node.children[a], t))
#     return epsilon
"""
def getEpsilon(tree: CFRTree, node: CFRNode, t):
    epsilon = {}
    if (node.isChance()):
        for a in range(len(node.children)):
            epsilon = addMerge(epsilon, getEpsilon(tree, node.children[a], t))
        return epsilon

    iset = node.information_set
    player = iset.player
    eps = -1
    for a in range(len(node.children)):
        LatteU = node.getLatter(t, tree, a, player)
        num_mu = 5
        while (num_mu):
            normalizingsum = random.random()
            for string in tree.actionPlan:
                r = random.random()
                tree.actionPlan[string][1] = r
                normalizingsum += r
            for string in tree.actionPlan:
                tree.actionPlan[string][1] /= normalizingsum
            eps = max(node.getExpectedDeviatedUtility(t, a, tree, player) - LatteU, eps)
            num_mu -= 1
    epsilon[iset.id] = eps
    return epsilon
# ok
def init(node, player_count: int):
    PLAYER_COUNT = player_count
    if (node.isChance()):
        for child in node.children:
            init(child, player_count)
        return
    if (node.isLeaf()):
        node.reachability = [False] * PLAYER_COUNT
        return
    iset = node.information_set
    iset.externalsigma = ""
    iset.tag = False
    iset.update = False
    iset.action = -1
    iset.reachability = -1
    # iset.utility = [0] * len(node.children)
    iset.utility = np.zeros(len(node.children))
    iset.imm_utility = np.zeros(len(node.children))
    for a in range(len(node.children)):
        init(node.children[a], player_count)
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
    action_plan = {}
    if node.isChance():
        for child in node.children:
            ac = ICFR_sampling(child)
            action_plan = Merge(action_plan, ac)
        return action_plan
    
    if (node.isLeaf()):
        return {}
    iset = node.information_set
    if (iset.reachability == 1):
        action_plan[iset.id] = iset.action
        for a in range(len(node.children)):
            ac = ICFR_sampling(node.children[a])
            action_plan = Merge(action_plan, ac)
        return action_plan

    elif (iset.reachability == -1):
        iset.reachability = 1
        sampledAction = iset.inRM.recommend()
        iset.action = sampledAction
        iset.externalsigma = str(iset.id) + '.' + str(sampledAction)
        for a in range(len(node.children)):
            if (a != sampledAction):
                createExternalRM(node.children[a], iset)
    else:
        if (not iset.tag):
            sampledAction = iset.exRM[iset.externalsigma + '.' + str(iset.id)].recommend()
            iset.action = sampledAction
        
    if (not iset.tag):
        action_plan[iset.id] = sampledAction
        iset.action = sampledAction
        iset.mu_T[sampledAction] = iset.mu_T[sampledAction] + 1
        iset.tag = True

    for a in range(len(node.children)):
        ac = ICFR_sampling(node.children[a])
        action_plan = Merge(action_plan, ac)
    return action_plan

def calcReachability(node: CFRNode, reachability: list):
    if node.isLeaf():
        node.reachability = reachability.copy()
        return
    if node.isChance():
        for child in node.children:
            calcReachability(child, reachability.copy())
        return

    iset = node.information_set
    for a in range(len(node.children)):
        if a == iset.action:
            calcReachability(node.children[a], reachability.copy())
        else:
            new_reachablity = reachability.copy()
            new_reachablity[iset.player] = False
            calcReachability(node.children[a], new_reachablity)

def sampleAction(s):
    r = random.random()
    count = 0
    for i in range(len(s)):
        count += s[i]
        if (r < count):
            return i

# def ICFR_trigger(node):
#     action_plan = {}
#     if (node.isChance()):
#         for child in node.children:
#             action_plan = Merge(action_plan, ICFR_trigger(child))
#         return action_plan
#     if (node.isLeaf()):
#         return {}
#     iset = node.information_set
#     r = random.random()
#     mu = [r, 1 - r]
#     action_plan[iset.id] = sampleAction(mu)
#     for a in range(len(node.children)):
#         action_plan = Merge(action_plan, ICFR_trigger(node.children[a]))
#     return action_plan

'''
def renewVisits(node, action_plan):
    if (node.isChance()):
        for child in node.children:
            renewVisits(child, action_plan)
        return
    if (node.isLeaf()):
        return node
    iset = node.information_set
    leaf = renewVisits(node.children[action_plan[iset.id]], action_plan)
    if (leaf in iset.visits[action_plan[iset.id]].keys()):
        iset.visits[action_plan[iset.id]][leaf] += 1
    else:
        iset.visits[action_plan[iset.id]][leaf] = 0
'''
# ???
# def ICFR_Observe(node, action_plan):
#     if (node.isChance()):
#         for child in node.children:
#             ICFR_Observe(child, action_plan)
#         # ICFR_Observe(node.children[node.action], action_plan)
#         return
#     if (node.isLeaf()):
#         return
#     iset = node.information_set
#     sampledAction = action_plan[iset.id]
#     for a in range(len(node.children)):
#         action_plan[iset.id] = a
#         # ???
#         iset.utility[a] += node.icfrutilityFromActionPlan(action_plan, iset)[iset.player]
#         action_plan[iset.id] = sampledAction
#         ICFR_Observe(node.children[a], action_plan)
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


def get_imm_utility(tree: CFRTree):
    for iset_id in tree.information_sets: # iset: CFRInformationset
        iset = tree.information_sets[iset_id]
        for a in range(iset.action_count):
            leaves = iset.getChildrenLeaves(a)
            for leaf in leaves:
                assert leaf.isLeaf()
                reachability = leaf.reachability.copy()
                reachability[iset.player] = True
                if reduce(lambda x,y : x and y, reachability, True):
                    iset.imm_utility[a] += leaf.utility[iset.player] / len(tree.root.children)

def get_cum_utility(iset: CFRInformationSet, action: int, action_plan: dict):
    utility = iset.imm_utility[action]
    childInfosets = iset.getChildrenInformationSets(action)
    for childInfoset in childInfosets:
        utility += get_cum_utility(childInfoset, action_plan[iset.id], action_plan)
    return utility

def get_utility(tree: CFRTree, action_plan: dict):
    get_imm_utility(tree)
    for iset_id in tree.information_sets: # iset: CFRInformationset
        iset = tree.information_sets[iset_id]
        for a in range(iset.action_count):
            iset.utility[a] += get_cum_utility(iset, a, action_plan)

# ok
def SolveWithICFR(icfr_tree: CFRTree, iterations, perc = 10, show_perc = True, checkEveryIteration = -1, 
                 check_callback = None):
    TEST = True
    # Graph data
    cnt = 0
    graph_data = []
    x_axis = [1]
    precision = checkEveryIteration / iterations
    prob_sum = 0
    px = 0
    max_iter_log = math.log10(iterations)
    while prob_sum < 1:
        x_axis.append(int(10**(prob_sum*max_iter_log)))
        prob_sum += precision
    x_axis.append(iterations)
    x_axis = sorted(list(set(x_axis)))
    print(x_axis)
    start_time = time.time()
    last_checkpoint_time = start_time

    player_count = icfr_tree.numOfPlayers

    for i in range(1, iterations + 1):
        if(show_perc and i % (iterations / 100 * perc) == 0):
            print(str(i / (iterations / 100 * perc) * perc) + "%")
        init(icfr_tree.root, player_count)
        # Run ICFR for each player
        # to sample internal for each infomation set for each player                                                                             
        action_plan = ICFR_sampling(icfr_tree.root) # node.id : sampled_action
        calcReachability(icfr_tree.root, [True] * player_count)
        get_utility(icfr_tree, action_plan)
        # trigger_plan = ICFR_trigger(icfr_tree.root)
        if (CFRJointStrategy.actionPlanToString(action_plan) in icfr_tree.actionPlan.keys()):
            icfr_tree.actionPlan[CFRJointStrategy.actionPlanToString(action_plan)][0] += 1
        else:
            icfr_tree.actionPlan[CFRJointStrategy.actionPlanToString(action_plan)] = [1, random.random()]
        
        # if (CFRJointStrategy.actionPlanToString(trigger_plan) in icfr_tree.triggerplan.keys()):
        #     icfr_tree.triggerplan[CFRJointStrategy.actionPlanToString(trigger_plan)] += 1
        # else:
        #     icfr_tree.triggerplan[CFRJointStrategy.actionPlanToString(trigger_plan)] = 1
        # ICFR_Observe(icfr_tree.root, action_plan)
        ICFR_Update(icfr_tree.root)        
        if px < len(x_axis) and i == x_axis[px]:
            if TEST:
                eps = getEpsilon(icfr_tree, icfr_tree.root, i)
                graph_data += [max(eps.values())]
                cnt += 1
                px += 1
                # x_axis.append(i)
                print("i:{} eps:{}".format(i, graph_data[-1]))
        if(checkEveryIteration > 0 and i % checkEveryIteration == 0):
            # if TEST:
            #     eps = getEpsilon(icfr_tree, icfr_tree.root, i)
            #     graph_data += [max(eps.values())]
            #     cnt += 1
                # print(getEpsilon(icfr_tree, icfr_tree.root, i))
            icfr_tree.root.T = i
            data = {#'epsilon': icfr_tree.checkMarginalsEpsilon(),
                    'iteration_number': i,
                    'duration': time.time() - last_checkpoint_time,
                    #'utility': icfr_tree.root.getExpectedUtility()
                    }
            # graph_data.append(data)
            # print('utility:', icfr_tree.root.getExpectedUtility())
            # print('epsilon:', eps)

            if(check_callback != None):
                check_callback(data)
                
            last_checkpoint_time = time.time()
        # print('test:', time.time() - start_time)
    # print("epsilon:",  graph_data)   

    ans = []
    for id in icfr_tree.information_sets:
        # print(icfr_tree.information_sets[id].nodes[0].base_node.seq, icfr_tree.information_sets[id].inRM.getStrategy().reshape(-1).tolist())
        ans.append('{:>4s}'.format(icfr_tree.information_sets[id].nodes[0].base_node.seq) + ' ' + 
            str([icfr_tree.information_sets[id].nodes[0].base_node.actionNames[i] for i in range(icfr_tree.information_sets[id].action_count)]) + ' ' + str(
            ['{:.2f}'.format(mu / sum(icfr_tree.information_sets[id].mu_T)) for mu in icfr_tree.information_sets[id].mu_T]))
    for i in sorted(ans):
        print(i)

    if TEST:              
        drawing(graph_data, x_axis)
    # s = 0
    # for string in icfr_tree.actionPlan:
    #     ap = CFRJointStrategy.stringToActionPlan(string)
    #     # if (ap[17] == 0):
    #     #     s += icfr_tree.actionPlan[string][0]
    #     #     print('actionplan_count:{}'.format(
    #     #         icfr_tree.actionPlan[string][0]
    #     #         ))
    #     print("count: ", icfr_tree.actionPlan[string][0])
    # print("s : ", s)
    # d = icfr_tree.information_sets
    # for id in d:
        # print(d[id].mu_T / np.sum(d[id].mu_T))
    # draw_tree(icfr_tree)
    # print(len(graph_data), iterations)
    return {'utility': icfr_tree.root.getExpectedUtility(), 'graph_data': graph_data, 'tot_time': time.time() - start_time}