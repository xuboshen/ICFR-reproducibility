from data_structures.trees import Tree, Node

from random import randint

def build_coordination_game_tree(n_players, branching_factor):
	tree = Tree(n_players, 0)

	build_coordination_game_subtree(tree, tree.root, 1, branching_factor, [])

	return tree

def build_coordination_game_subtree(tree, current_node, current_player, branching_factor, action_history):
	if current_player >= tree.numOfPlayers:
		for a in range(branching_factor):
			u = get_coordination_utility(action_history + [ a ], tree.numOfPlayers)
			leaf = tree.addLeaf(current_node, u)
		return

	for a in range(branching_factor):
		node = tree.addNode(player = current_player, information_set = current_player, parent = current_node)
		build_coordination_game_subtree(tree, node, current_player + 1, branching_factor, action_history + [ a ])

def get_coordination_utility(action_history, n_players):
	u = [0 for _ in range(n_players)]

	if max(action_history) == min(action_history):
		x = randint(1, 5)
		u = [x for _ in range(n_players)]

	return u