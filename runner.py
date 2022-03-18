from games.kuhn import build_kuhn_tree
from games.leduc import build_leduc_tree
from games.goofspiel import build_goofspiel_tree, TieSolver
from games.hanabi import build_hanabi_tree, UtilitySplitter

from data_structures.trees import randomTree
from data_structures.cfr_trees import CFRTree
from cfr_code.sample_cfr import SolveWithSampleCFR
from cfr_code.cfr import SolveWithCFR
from cfr_code.reconstruction_cfr import SolveWithReconstructionCFR
from cfr_code.icfr import SolveWithICFR
from utilities.serialization import tree_to_colgen_dat_file

import time
import json
import argparse
from functools import reduce
import os

parser = argparse.ArgumentParser(description='runner parser')

parser.add_argument('game', type=str, help='type of game instance (random, kuhn, leduc, goofspiel, hanabi)', choices=['kuhn','leduc','goofspiel','random','hanabi'])

parser.add_argument('--players', '-p', type=int, default=3, help='number of players')
parser.add_argument('--rank', '-r', type=int, default=3, help='rank of the game')
parser.add_argument('--suits', '-s', type=int, default=3, help='number of suits (only for leduc')
parser.add_argument('--betting_parameters', '-bp', type=int, default=[2,4], nargs='*', help='betting parameters (only for leduc')
parser.add_argument('--tie_solver', '-ts', type=str, default='accumulate', help='strategy for solving ties (only for goofspiel)',
                    choices=['accumulate','discard_if_all','discard_if_high','discard_always'])
parser.add_argument('--branching_factor', '-bf', type=int, default=2, help='branching factor of the tree (only for random)')
parser.add_argument('--depth', '-d', type=int, default=4, help='depth of the tree (only for random)')
parser.add_argument('--iset_probability', '-ip', type=float, default=1, help='information set probability (only for random)')

parser.add_argument('--cards_per_player', '-cpp', type=int, default=1, help='how many cards are dealt to each player (only for hanabi')
parser.add_argument('--starting_clue_tokens', '-sct', type=int, default=1, help='how many clue tokens are available at the beginning of the game (only for hanabi)')
parser.add_argument('--color_distribution', '-cd', type=int, default=[1,1], nargs='*', help='distribution of card values inside of a single color/suit (only for hanabi')
parser.add_argument('--hanabi_utility_splitter', '-hus', type=str, default='uniform', help='way to split utility between player in hanabi',
                    choices=['uniform', 'competitive'])

parser.add_argument('--number_iterations', '-t', type=int, default=100000, help='number of iterations to run')
parser.add_argument('--bootstrap_iterations', '-bt', type=int, default=0, help='number of iterations to run without sampling')
parser.add_argument('--check_every_iteration', '-ct', type=int, default=10000, help='every how many iterations to check the epsilon')
parser.add_argument('--bound_joint_size', '-bjs', const=True, nargs='?', help='bound or not the limit of the resulting joint strategy')
parser.add_argument('--reconstruct_every_iteration', '-rei', type=int, default=1, help='every how many iterations to reconstruct a joint from the marginals')
parser.add_argument('--reconstruct_not_optimal_plan', '-rnop', const=True, nargs='?', help='do not try to find the optimal plan to reconstruct at each reconstruction iteration')

parser.add_argument('--algorithm', '-a', type=str, default='cfr', choices=['icfr', 'cfr-s', 'cfr', 'cfr+', 'cfr-jr'], help='algorithm to be used')

parser.add_argument('--logfile', '-log', type=str, default=(str(int(time.time())) + "log.log"), help='file in which to log events and errors')
parser.add_argument('--results', '-res', type=str, default='results/', help='folder where to put the results (must contain subfolders for each game')

parser.add_argument('--build_datfile', '-dat', const=True, nargs='?', help='output the corresponding datfile')

args = parser.parse_args()
parameters_dict = vars(args)

game = args.game

num_players = args.players
rank = args.rank
num_of_suits = args.suits
betting_parameters = args.betting_parameters
tie_solver = {'accumulate':TieSolver.Accumulate,'discard_if_all':TieSolver.DiscardIfAll,'discard_if_high':TieSolver.DiscardIfHigh,
              'discard_always':TieSolver.DiscardAlways}[args.tie_solver]
cards_per_player = args.cards_per_player
starting_clue_tokens = args.starting_clue_tokens
color_distribution = args.color_distribution
utility_splitter = {'uniform':UtilitySplitter.Uniform,'competitive':UtilitySplitter.Competitive}[args.hanabi_utility_splitter]

number_iterations = args.number_iterations
bootstrap_iterations = args.bootstrap_iterations
check_every_iteration = args.check_every_iteration
bound_joint_size = args.bound_joint_size != None
reconstructEveryIteration = args.reconstruct_every_iteration
reconstructWithOptimalPlan = args.reconstruct_not_optimal_plan == None

log_file_name = args.logfile
results_directory = args.results

build_datfile = args.build_datfile

def log_line(string):
    log_file = open(log_file_name, "a")
    log_file.write(time.strftime("%Y.%m.%d %H:%M:%S: ") + string + "\n")
    log_file.flush()
    log_file.close()
    print(string)
    
# if build_datfile and game != "random":
#     log_line("ERROR: datfile are currently supported only for random games")
#     exit()

def log_result_point_callback(results_file_name):
    # whenever it is called, execute the __callback function
    def __callback(datapoint):
        results_file = open(results_file_name, "r")
        old_data = json.load(results_file)
        results_file.close()
        old_data['data'].append(datapoint)
        results_file = open(results_file_name, "w+")
        results_file.write(json.dumps(old_data))
        results_file.close()
    return __callback

def solve_function(cfr_tree, results_file_name):
    if args.algorithm == 'cfr-s':
        return SolveWithSampleCFR(cfr_tree, number_iterations, bootstrap_iterations = bootstrap_iterations,
                             checkEveryIteration = check_every_iteration, bound_joint_size = bound_joint_size,
                             check_callback = log_result_point_callback(results_file_name))
    if args.algorithm == 'cfr' or args.algorithm == 'cfr+':
        return SolveWithCFR(cfr_tree, number_iterations, checkEveryIteration = check_every_iteration,
                            check_callback = log_result_point_callback(results_file_name), use_cfr_plus = args.algorithm == 'cfr+')
    if args.algorithm == 'cfr-jr':
        return SolveWithReconstructionCFR(cfr_tree, number_iterations, checkEveryIteration = check_every_iteration,
                                          reconstructEveryIteration = reconstructEveryIteration,
                                          reconstructWithOptimalPlan = reconstructWithOptimalPlan,
                                          check_callback = log_result_point_callback(results_file_name))
    if args.algorithm == 'icfr':
        return SolveWithICFR(cfr_tree, number_iterations, checkEveryIteration = check_every_iteration,
                             check_callback = log_result_point_callback(results_file_name))

def count_sequences(cfr_tree):
    all_nodes = reduce(lambda x, y: x + y.nodes, cfr_tree.information_sets.values(), [])
    all_leaves = list(filter(lambda n: n.isLeaf(), reduce(lambda x, y: x + y.children, all_nodes, [])))
    all_nodes = all_nodes + all_leaves
    
    count = 0

    for p in range(cfr_tree.numOfPlayers):
        Q_raw = list(filter(lambda q: q != {}, map(lambda n: n.base_node.getSequence(p), all_nodes)))
        Q = [{}] + [dict(t) for t in {tuple(d.items()) for d in Q_raw}]
        count += len(Q)
        
    return count

# ----------------------------------------
# Install handler to detect crashes
# ----------------------------------------
import sys
import logging
import traceback

def log_except_hook(*exc_info):
    text = "".join(traceback.format_exception(*exc_info))
    logging.error("Unhandled exception: %s", text)
    log_line("\n\n------Unhandled exception:------\n\n" + text)

sys.excepthook = log_except_hook
# ----------------------------------------

def run_experiment(cfr_tree, results_file_name, parameters_dict, args, number_iterations):
    results_file_name += ".result"
    results_file = open(results_file_name, "w+")
    parameters_dict['nodes_amount'] = sum(map(lambda i: len(i.nodes), cfr_tree.information_sets.values()))
    leaves = set()
    cfr_tree.root.find_terminals(leaves)
    parameters_dict['leaves_amount'] = len(leaves)
    parameters_dict['infoset_amount'] = len(cfr_tree.information_sets)
    parameters_dict['sequences_amount'] = count_sequences(cfr_tree)
    results_file.write(json.dumps({"parameters": parameters_dict, "data": []}))
    results_file.close()

    try:
        res = solve_function(cfr_tree, results_file_name)
    except:
        log_line("\n\n --- AN ERROR HAS OCCURRED WHILE SOLVING --- \n\n")
        sys.excepthook(*sys.exc_info())

    log_line("Finished solving with " + args.algorithm + ".")
    print(res)
    log_line("Time elapsed = " + str(res['tot_time']) + " seconds.\n")

    results_file = open(results_file_name, "r")
    old_data = json.load(results_file)
    results_file.close()
    old_data["total_duration"] = res['tot_time']
    old_data["average_iterations_per_second"] = number_iterations / res['tot_time']
    old_data["utility"] = res['utility']
    results_file = open(results_file_name, "w+")
    results_file.write(json.dumps(old_data))
    results_file.close()

def make_filename_unique(file_path):
    while os.path.isfile(file_path):
        file_path += '_'
    return file_path

if game == 'kuhn':
    game_name = "kuhn_" + str(num_players) + "_" + str(rank)
    log_line("Building a " + game_name + " tree")
    kuhn_tree = build_kuhn_tree(num_players, rank)
    log_line("Built a " + game_name + " tree")
    cfr_tree = CFRTree(kuhn_tree)
    results_file_name = results_directory + "kuhn/" + str(int(time.time())) + "_" + str(num_players) + "_" + str(rank)
    results_file_name = make_filename_unique(results_file_name)
    
    run_experiment(cfr_tree, results_file_name, parameters_dict, args, number_iterations)

if game == 'leduc':
    game_name = "leduc_" + str(num_players) + "_" + str(num_of_suits) + "_" + str(rank)
    log_line("Building a " + game_name + " tree")
    leduc_tree = build_leduc_tree(num_players, num_of_suits, rank, betting_parameters)
    log_line("Built a " + game_name + " tree")
    cfr_tree = CFRTree(leduc_tree)

    results_file_name = results_directory + "leduc/" + str(int(time.time())) + "_" + str(num_players) + "_" + str(num_of_suits) + "_" + str(rank)
    results_file_name = make_filename_unique(results_file_name)
    
    run_experiment(cfr_tree, results_file_name, parameters_dict, args, number_iterations)

if game == 'goofspiel':
    game_name = "goofspiel_" + str(num_players) + "_" + str(rank) + "_" + tie_solver.name
    log_line("Building a " + game_name + " tree")
    goofspiel_tree = build_goofspiel_tree(num_players, rank, tie_solver)
    log_line("Built a " + game_name + " tree")
    cfr_tree = CFRTree(goofspiel_tree)

    results_file_name = results_directory + "goofspiel/" + str(int(time.time())) + \
                        "_" + str(num_players) + "_" + str(rank) + '_' + tie_solver.name
    results_file_name = make_filename_unique(results_file_name)

    run_experiment(cfr_tree, results_file_name, parameters_dict, args, number_iterations)

if game == 'random':
    game_name = "random_" + str(num_players) + "_" + str(args.depth) + "_" + str(args.branching_factor)
    log_line("Building a " + game_name + " tree")
    random_tree = randomTree(args.depth, args.branching_factor, args.iset_probability, num_players,
                             min_utility = 0, max_utility = 1, int_utility = False)
    log_line("Built a " + game_name + " tree")
    cfr_tree = CFRTree(random_tree)

    results_file_name = results_directory + "random/" + str(int(time.time())) + "_" + str(num_players) + "_" + str(args.depth) + \
                                "_" + str(args.branching_factor)
    results_file_name = make_filename_unique(results_file_name)

    if build_datfile:
        with open(results_file_name + '.dat', 'w') as f:
            f.write(tree_to_colgen_dat_file(random_tree))
        log_line("Dat file created (for random tree).")

    run_experiment(cfr_tree, results_file_name, parameters_dict, args, number_iterations)

if game == 'hanabi':
    string_description = str(num_players) + '_' + str(num_of_suits) + '_' + \
                         str(color_distribution).replace(' ','').replace(',','_') + '_' + \
                         str(cards_per_player) + '_' + str(starting_clue_tokens) + '_' + utility_splitter.name
    game_name = "hanabi_" + string_description
    log_line("Building a " + game_name + " tree")
    hanabi_tree = build_hanabi_tree(num_players, num_of_suits, color_distribution, 
                                    cards_per_player, starting_clue_tokens, utility_splitter = utility_splitter)
    log_line("Built a " + game_name + " tree")
    cfr_tree = CFRTree(hanabi_tree)

    results_file_name = results_directory + "hanabi/" + str(int(time.time())) + "_" + string_description
    results_file_name = make_filename_unique(results_file_name)

    run_experiment(cfr_tree, results_file_name, parameters_dict, args, number_iterations)