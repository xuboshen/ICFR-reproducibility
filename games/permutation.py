from data_structures.trees import Tree, Node
from games.utilities import all_permutations

def build_permutation_game_tree(n_players, branching_factor, utility_params):
	tree = Tree((n_players - 1) + n_players, 0)

	bottom_nodes = build_permutation_upper_tree(tree, tree.root, n_players)
	ordering_permutations = all_permutations(list(range(n_players - 1, 2 * n_players - 1)))
	last_infoset_id = max(bottom_nodes, key = lambda n: n.information_set).information_set + 2

	for i in range(len(bottom_nodes)):
		bottom_node = bottom_nodes[i]

		ordering = ordering_permutations[2 * i]
		node = tree.addNode(player = ordering[0], parent = bottom_node, 
							information_set = last_infoset_id + ordering[0] - n_players)
		build_permutation_lower_tree(tree, branching_factor, node, ordering[1:], 
									 utility_params, last_infoset_id, n_players, [])

		ordering = ordering_permutations[2 * i + 1]
		node = tree.addNode(player = ordering[0], parent = bottom_node, 
							information_set = last_infoset_id + ordering[0] - n_players)
		build_permutation_lower_tree(tree, branching_factor, node, ordering[1:], 
									 utility_params, last_infoset_id, n_players, [])

	return tree

def build_permutation_upper_tree(tree, current_node, n_actions):
	if n_actions < 3:
		return [ current_node ]

	bottom_nodes = []

	for _ in range(n_actions):
		node = tree.addNode(player = current_node.player + 1, parent = current_node)
		bottom_nodes += build_permutation_upper_tree(tree, node, n_actions - 1)

	return bottom_nodes

def build_permutation_lower_tree(tree, branching_factor, current_node, ordering, utility_params,
								 last_infoset_id, n_players, action_history):
	if len(ordering) == 0:
		for a in range(branching_factor):
			tree.addLeaf(current_node, get_permutation_utility(action_history + [ a ], utility_params, n_players))
		return

	for a in range(branching_factor):
		node = tree.addNode(player = ordering[0], information_set = last_infoset_id + ordering[0] - n_players,
							parent = current_node)
		build_permutation_lower_tree(tree, branching_factor, node, ordering[1:], utility_params,
									 last_infoset_id, n_players, action_history + [ a ])

def get_permutation_utility(action_history, utility_params, n_players):
	u = 0

	for (a1, a2) in zip(action_history, action_history[1:]):
		u += utility_params[a1][a2]

	return [u for _ in range((n_players - 1) + n_players)]