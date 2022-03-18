from cfr_code.cfr import CFR
from data_structures.cfr_trees import CFRJointStrategy
import time

def SolveWithReconstructionCFR(cfr_tree, iterations, perc = 10, show_perc = False, 
                               checkEveryIteration = -1, reconstructEveryIteration = 1,
                               check_callback = None, use_cfr_plus = False,
                               reconstructPlayersTogether = False,
                               reconstructWithOptimalPlan = True):
    
    jointStrategy = CFRJointStrategy()

    # Graph data
    graph_data = []

    start_time = time.time()
    reconstruction_time = 0
    last_checkpoint_time = start_time

    player_count = cfr_tree.numOfPlayers

    for i in range(1, iterations+1):
        if(show_perc and i % (iterations / 100 * perc) == 0):
            print(str(i / (iterations / 100 * perc) * perc) + "%")

        # Run CFR for each player
        for p in range(player_count):
            CFR(cfr_tree.root, p, [1] * player_count, use_cfr_plus)
            
        # Update the current strategy for each information set
        for infoset in cfr_tree.information_sets.values():
            infoset.updateCurrentStrategy()

        # Reconstruct a joint from the marginals and add it to the current joint strategy
        if (i % reconstructEveryIteration == 0):
            reconstruction_start_time = time.time()
            if reconstructPlayersTogether:
                jointStrategy.addJointDistribution(cfr_tree.buildJointFromMarginals_AllPlayersTogether())
            else:
                jointStrategy.addJointDistribution(cfr_tree.buildJointFromMarginals(select_optimal_plan = reconstructWithOptimalPlan))                
            reconstruction_time += (time.time() - reconstruction_start_time)

        if(checkEveryIteration > 0 and i % checkEveryIteration == 0):
            data = {'epsilon': cfr_tree.checkEquilibrium(jointStrategy),
                    'marginal_epsilon': cfr_tree.checkMarginalsEpsilon(),
                    'joint_support_size': len(jointStrategy.plans),
                    'iteration_number': i,
                    'duration': time.time() - last_checkpoint_time,
                    'reconstruction_time': reconstruction_time,
                    'utility': cfr_tree.getUtility(jointStrategy)}
            reconstruction_time = 0
            graph_data.append(data)

            if(check_callback != None):
                check_callback(data)
                
            last_checkpoint_time = time.time()
        
    return {'utility': cfr_tree.getUtility(jointStrategy), 'graph_data': graph_data, 'tot_time': time.time() - start_time, 'joint': jointStrategy}