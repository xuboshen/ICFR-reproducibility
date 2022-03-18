from functools import reduce
import itertools
from data_structures.cfr_trees import CFRTree
from data_structures.trees import Tree, Node, ChanceNode
import ast

def tree_to_colgen_dat_file(tree, compressSequenceNames = True):
    """
    Given a tree, build a string representing a dat file for the colgen algorithm ampl implementation.
    If compressSequenceNames is True, all sequences are replaced by unique ids (to save disk space); otherwise,
    sequences are generated as a string containing all the id of the information sets and relative actions.
    """

    cfr_tree = CFRTree(tree)

    root = cfr_tree.root

    s = ""

    max_sequence_id = 0
    sequence_string_to_id = {}

    def sequence_to_string(sequence, player):
        if(len(sequence) == 0):
            string = "empty_seq_" + str(player)
        else:
            string = reduce(lambda x, y: x + y, map(lambda seq: 'a' + str(seq[0]) + "." + str(seq[1]), sequence.items()))

        if(not compressSequenceNames):
            return string

        if(string in sequence_string_to_id):
            return str(sequence_string_to_id[string])
        else:
            nonlocal max_sequence_id
            sequence_string_to_id[string] = max_sequence_id
            max_sequence_id += 1
            return str(max_sequence_id - 1)

    all_nodes = reduce(lambda x, y: x + y.nodes, cfr_tree.information_sets.values(), [])
    all_leaves = list(filter(lambda n: n.isLeaf(), reduce(lambda x, y: x + y.children, all_nodes, [])))
    all_nodes = all_nodes + all_leaves

    Q_holder = []

    for p in range(cfr_tree.numOfPlayers):

        # --------------------------
        # Print sequences
        # --------------------------
        Q_raw = list(filter(lambda q: q != {}, map(lambda n: n.base_node.getSequence(p), all_nodes)))

        # Remove duplicates
        Q = [{}] + [dict(t) for t in {tuple(d.items()) for d in Q_raw}]
        Q_holder.append(Q)

        s += "#|Q" + str(p+1) + "| = " + str(len(Q)) + "\n\n"

        s += "set Q" + str(p+1) + " ="
        for q in Q:
            s += " " + sequence_to_string(q, p)
        s += ";\n\n"

        # --------------------------
        # Print information sets
        # --------------------------
        H = cfr_tree.infosets_by_player[p]

        s += "#|H" + str(p+1) + "| = " + str(len(H) + 1) + "\n\n"

        s += "set H" + str(p+1) + " = empty_is_" + str(p+1) + " " + reduce(lambda x, y: x + " " + str(y.id), H, "") + ";\n\n"

        # --------------------------
        # Print F matrix and f vector
        # --------------------------
        s += "param F" + str(p+1) + ":\n"

        for q in Q:
            s += sequence_to_string(q, p) + " "
        s += ":=\nempty_is_" + str(p+1) + " 1" + (" 0" * (len(Q)-1)) + "\n"
        for h in H:
            s += str(h.id) + " "
            h_seq = h.nodes[0].base_node.getSequence(p)
            h_next_sequences = []
            for a in range(h.action_count):
                seq_copy = h_seq.copy()
                seq_copy[h.id] = a
                h_next_sequences.append(seq_copy)
            for q in Q:
                if(q == h_seq):
                    s += "-1 "
                elif(q in h_next_sequences):
                    s += "1 "
                else:
                    s += "0 "
            s += "\n"
        s += ";\n\n"

        s += "param f" + str(p+1) + " :=\nempty_is_" + str(p+1) + " 1\n"
        for h in H:
            s += str(h.id) + " 0\n"
        s += ";\n\n"

    all_joint_sequences=[]
    cartesian = itertools.product(*Q_holder)
    all_joint_sequences = list(cartesian)

    def __js_len(js):
        len_js = 0
        for p in range(len(js)):
            len_js += len(js[p])
        return len_js


    minimal_sequences = {}
    for js in all_joint_sequences:
        terminals = root.reachableTerminals(js)
        len_js = __js_len(js)
        for terminal in terminals:
            if terminal not in minimal_sequences:
                minimal_sequences[terminal] = js
            else:
                if(len_js < __js_len(minimal_sequences[terminal])):
                    minimal_sequences[terminal] = js

    # --------------------------
    # Print utilities
    # --------------------------
    # for player in range(cfr_tree.numOfPlayers):
    #     s += "param U" + str(player+1) + " :=\n"
    #     for js in all_joint_sequences:
    #         expected_utility = 0.0
    #         if js in minimal_sequences.values():
    #             expected_utility = root.utilityFromJointSequence(js)[player]
    #         for p in range(cfr_tree.numOfPlayers):
    #             s += sequence_to_string(js[p], p) + " "
    #         s += str(expected_utility) + "\n"
    #     s += ";\n\n"
    for player in range(cfr_tree.numOfPlayers):
        s += "param U" + str(player+1) + " default 0 :=\n"
        for js in minimal_sequences.values():
            expected_utility = root.utilityFromJointSequence(js)[player]
            for p in range(cfr_tree.numOfPlayers):
                s += sequence_to_string(js[p], p) + " "
            s += str(expected_utility) + "\n"
        s += ";\n\n"


    return s

def serialize_tree(tree):
    def serialize_subtree(node):
        # print("Starting " + str(node))
        if node.isLeaf():
            return 'l ' + str(node.utility)[1:-1].replace(',', '') + '\n'
        
        if node.isChance():
            res = 'c ' + str(len(node.children))
        else:
            chance_probability = ''
            if node.parent != None and node.parent.isChance():
                chance_probability = ' ' + str(node.parent.distribution[node.incoming_action])
            res = 'n ' + str(len(node.children)) + ' ' + str(node.player) + ' ' + \
                    str(node.information_set) + chance_probability

        res += '\n'

        for child in node.children:
            res += serialize_subtree(child)
        # print("Ending " + str(node))
        # print(res)
        # print('----------')
        return res

    header = str(tree.numOfPlayers) + ' ' + str(tree.root.player) + '\n'

    return header + serialize_subtree(tree.root)

def deserialize_tree(string):
    def deserialize_subtree(tree, parent_node, lines):
        line = lines[0]
        lines = lines[1:]
        line_elements = line.split(' ')

        if line[0] == 'l':
            utility = ast.literal_eval('[' + line[2:].replace(' ', ',') + ']')
            tree.addLeaf(parent_node, utility)
        elif line[0] == 'n':
            num_children = int(line_elements[1])
            player = int(line_elements[2])
            information_set = int(line_elements[3])
            chance_probability = -1
            if len(line_elements) > 4:
                chance_probability = line_elements[4]

            node = tree.addNode(player, information_set, parent_node, chance_probability)

            for i in range(num_children):
                lines = deserialize_subtree(tree, node, lines)
        elif line[0] == 'c':
            num_children = int(line_elements[1])

            chance_node = tree.addChanceNode(parent_node)

            for i in range(num_children):
                lines = deserialize_subtree(tree, chance_node, lines)

        return lines

    lines = string.split('\n')
    header_line = lines[0]
    header_elements = header_line.split(' ')

    num_players = int(header_elements[0])
    first_player = int(header_elements[1])

    root_line = lines[1]
    root_elements = root_line.split(' ')

    root_num_children = int(root_elements[1])
    if root_line[0] == 'n':
        root_player = int(root_elements[2])
        root_information_set = int(root_elements[3])

        root = Node(root_player, 0, root_information_set)
    elif root_line[0] == 'c':
        root = ChanceNode(0)

    tree = Tree(num_players, first_player, root)

    lines = lines[2:]
    for i in range(root_num_children):
        lines = deserialize_subtree(tree, tree.root, lines)

    return tree