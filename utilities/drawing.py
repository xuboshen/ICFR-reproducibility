import matplotlib.pyplot as plt
import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout

from data_structures.cfr_trees import CFRTree

def draw_tree(tree, title = 'Tree'):
	# Set width and height for the matplotlib figure
	old_figsize = plt.rcParams["figure.figsize"]
	plt.rcParams["figure.figsize"] = (20, 10)

	def get_node_id(node):
		return node.id

	def add_nodes_to_graph(graph, node):
		if node.isLeaf():
			graph.add_node(get_node_id(node), utility = node.utility)
		else:
			graph.add_node(get_node_id(node))
		
		for child in node.children:
			add_nodes_to_graph(graph, child)
			graph.add_edge(get_node_id(node), get_node_id(child))

	def add_infoset_edges_to_graph(graph, tree):
		cfr_tree = CFRTree(tree)

		for infoset in cfr_tree.information_sets.values():
			nodes = infoset.nodes
			nodes.sort(key = lambda el: get_node_id(el.base_node))

			for i in range(0, len(nodes) - 1):
				graph.add_edge(get_node_id(nodes[i]), get_node_id(nodes[i+1]))

	G = nx.Graph()
	add_nodes_to_graph(G, tree.root)

	plt.title(title)
	pos = graphviz_layout(G, prog='dot')
	
	add_infoset_edges_to_graph(G, tree)

	nx.draw(G, pos, with_labels = True)
	
	# Print utilities under leaves
	for p in pos:
		node = G.node.get(p)
		if 'utility' in node:
			(x, y) = (pos[p][0] - 15, pos[p][1] - 10)
			plt.text(x, y, node['utility'])
	nx.draw_networkx_labels(G, pos)

	plt.rcParams["figure.figsize"] = old_figsize
	plt.savefig("tree.png", dpi = 200)