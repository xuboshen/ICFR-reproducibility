import random
from enum import Enum

class Tree:
    """
    Tree representation of an extensive-form game.
    Supports an arbitrary number of players, including chance.
    """

    def __init__(self, numOfPlayers = 2, first_player = 0, root = None):
        """
        Create a tree with a specified root node (or with a new node as root if None is given)
        """

        if(root == None):
            root = Node(first_player, 0, 0)
        self.root = root
        self.node_count = 1
        self.infoset_count = 1
        self.max_infoset = 0 # ?
        self.numOfPlayers = numOfPlayers
        self.max_depth = 0
        
    def addNode(self, player, information_set = -1, parent = None, probability = -1, actionName = None):
        """
        Add a decision node for a given player to the tree.
        If no information set is given, a new unique id is generated.
        If no parent is given, the parent is set to be the root.
        If the node is a children of a chance node, the probability to play the action leading to this node must be given.
        If no action name is given, a default string is generated.
        """

        if(self.root == None):
            print("ERROR: root should not be None")
            return None
        
        if(information_set == -1):
            information_set = self.infoset_count
            self.infoset_count += 1
        self.max_infoset = max(self.max_infoset, information_set)
        
        if(parent == None):
            parent = self.root
        
        node = Node(player, self.node_count, information_set, parent)
        self.max_depth = max(self.max_depth, node.depth)
        
        if(parent.isChance()):
            parent.addChild(node, probability, actionName)
        else:
            parent.addChild(node, actionName)
        self.node_count += 1
        
        return node
    
    def addLeaf(self, parent, utility, actionName = None):
        """
        Add a leaf node with a given utility to the tree.
        If no action name is given, a default string is generated.
        """

        if(len(utility) != self.numOfPlayers):
            print("ERROR: trying to create a leaf with a utility vector of the wrong size.")
            return
        
        leaf = Leaf(self.node_count, utility, parent)
        self.max_depth = max(self.max_depth, leaf.depth)
        parent.addChild(leaf, actionName)
        self.node_count += 1
        return leaf
    
    def addChanceNode(self, parent = None, actionName = None):
        """
        Add a chance node to the tree.
        If no parent is given, the parent is set to be the root.
        If no action name is given, a default string is generated.
        """

        if(self.root == None):
            print("ERROR: root should not be None")
            return None
        
        if(parent == None):
            parent = self.root
        
        chanceNode = ChanceNode(self, self.node_count, parent, actionName)
        self.max_depth = max(self.max_depth, chanceNode.depth)
        parent.addChild(chanceNode)
        self.node_count += 1
        
        return chanceNode
    
    def display(self):
        print(self.root)
        self.root.displayChildren()

class Node:
    """
    Represents a decision node for a given player in an extensive-form tree.
    """

    def __init__(self, player, id, information_set, parent = None):
        """
        Create a decision node for a given player, with a given id and a given information set.
        """

        self.id = id
        self.parent = parent
        self.player = player
        self.depth = 0
        if parent != None:
            self.depth = parent.depth + 1
        self.children = []
        self.actionNames = [] # [0.0, 0.1, 0.2]
        self.information_set = information_set # begins with 0
        self.incoming_action = None
        self.incoming_action_name = None

    def __str__(self):
        return self.__repr__()
    
    def __repr__(self):
        s = "Player " + str(self.player) +             " - Infoset " + str(self.information_set) +             " - Node " + str(self.id) 
        if(self.parent != None):
            s += " (children of Node" + str(self.parent.id) + " via Action " +                    str(self.incoming_action_name) + ")"
        return s
        
    def addChild(self, child, actionName = None):
        """
        Add a child node.
        If no action name is passed, a default one is generated.
        """

        self.children.append(child)
        child.parent = self
        if(actionName == None):
            actionName = str(self.information_set) + "." + str(len(self.children) - 1) # 0.0 / 0.1 / thisnode.children
        self.actionNames.append(actionName)
        child.incoming_action = len(self.children) - 1 # 0
        child.incoming_action_name = actionName # 0.0
            
    def getChild(self, action):
        return self.action_to_child_dict[action]
        
    def isLeaf(self):
        return False
    
    def isChance(self):
        return False
    
    def getSequence(self, player):
        """
        Returns the sequence (dict:{infoid: subsequent action}) of actions (for a given player) that leads to this node.
        """

        if(self.parent == None):
            return {}
        if(self.parent.player != player and player != None):
            return self.parent.getSequence(player)
        
        sequence = self.parent.getSequence(player) 
        sequence[self.parent.information_set] = self.incoming_action
        return sequence
    
    def displayChildren(self):
        for child in self.children:
            print(child)
        for child in self.children:
            child.displayChildren()
            
    def getActionLeadingToNode(self, targetNode):
        """
        Returns the action (of this node) in the path from this node to the target node.
        """

        if(targetNode.parent == None):
            return None
        if(targetNode.parent == self):
            return targetNode.incoming_action
        return self.getActionLeadingToNode(targetNode.parent)

    def getNodeFollowJointSequence(self, joint_sequence): 
        # [sequence1, sequence2, sequence3],
        # sequence1 = {infoid: action}
        """
        Returns the leaf reached when following the given joint sequence.
        """

        if(self.isLeaf()):
            return self
        
        sequence = joint_sequence[self.player]

        if(self.information_set not in sequence):
            return self

        action = sequence[self.information_set] # 0 / 1 / 2
        
        return self.children[action].getNodeFollowJointSequence(joint_sequence)

class Leaf(Node):
    """
    Represents a leaf node in an extensive-form tree.
    """

    def __init__(self, id, utility, parent):
        Node.__init__(self, -1, id, -1 , parent)
        self.utility = utility
        
    def __repr__(self):
        s = "Leaf" + str(self.id) 
        if(self.parent != None):
            s += " (children of Node" + str(self.parent.id) + " via Action " + str(self.incoming_action_name) + ") - " +                    " utility is " + str(self.utility)
        return s
    
    def isLeaf(self):
        return True

class ChanceNode(Node):
    """
    Represents a chance node in an extensive-form tree.
    """

    def __init__(self, id, parent = None):
        Node.__init__(self, -42, id, -42, parent)
        self.distribution = []
    
    def isChance(self):
        return True
    
    def addChild(self, child, probability, actionName = None):
        """
        Add a child node, that is reached by a given (fixed) probability.
        If no action name is passed, a default one is generated.
        """

        self.children.append(child)
        self.distribution.append(probability)
        child.parent = self
        child.incoming_action = len(self.children) - 1
        if(actionName == None):
            actionName = "c." + str(len(self.children) - 1)
        self.actionNames.append(actionName)
        child.incoming_action_name = actionName
        
# --------------------------------------------------------------------------------

class PlayerSwapMethod(Enum):
    Random = 0
    RoundRobin = 1
    RandomWithoutSame = 2

def randomTree(depth, branching_factor = 2, info_set_probability = 1, player_count = 2,
               first_player = -1, min_utility = 0, max_utility = 100, int_utility = True, swap_method = PlayerSwapMethod.RoundRobin):
    """
    Create a random extensive-form tree.
    depth = the depth of the tree.
    branching_factor = how many actions each node has.
    info_set_probability = the probability that a newly added node will be added to an already existing information set.
    player_count = the number of players.
    first_player = the first player to play (if no one is given, it is chosen randomly).
    min_utility = the minimum utility achievable by each player.
    max_utility = the maximum utility achievable by each player.
    int_utility = wether the utility is a random integer or not.
    swap_method = how to alternate players during the game (either round robin or random).
    """
    
    # Player swap subroutine
    def swapPlayers(current_player, player_count, swap_method):
        if(swap_method == PlayerSwapMethod.RoundRobin):
            return (current_player + 1) % player_count
        if(swap_method == PlayerSwapMethod.Random):
            return random.randint(0, player_count - 1)
        if(swap_method == PlayerSwapMethod.RandomWithoutSame):
            p = random.randint(0, player_count - 2)
            if(p >= current_player):
                p += 1
            return p
    
    # Randomly choose first player if it is not already set
    if(first_player < 0 or first_player >= player_count):    
        player = random.randint(0, player_count - 1)
    else:
        player = first_player
        
    # Initialize the tree
    tree = Tree(player_count, player)
    nodes_to_expand = [ tree.root ]
    information_set = 0
    
    for d in range(0, depth - 1):
        # Change player
        player = swapPlayers(player, player_count, swap_method)
        
        new_nodes_to_expand = []
        for parent in nodes_to_expand:
            # Change information set (children of different nodes always are in different information sets)
            # -- because of perfect recall
            information_set += 1
                
            # Generate a new node for each action
            for a in range(branching_factor):
                node = tree.addNode(player, information_set, parent)
                if(a != branching_factor - 1 and random.random() <= info_set_probability):
                    information_set += 1
                
                new_nodes_to_expand.append(node)
                
        nodes_to_expand = new_nodes_to_expand
        
    # Nodes in nodes_to_expand have only leaves as children at this point
    for node in nodes_to_expand:
        for a in range(branching_factor):
            if(int_utility):
                utility = [random.randint(min_utility, max_utility) for p in range(player_count)]
            else:
                utility = [random.uniform(min_utility, max_utility) for p in range(player_count)]
            tree.addLeaf(node, utility)
        
    return tree