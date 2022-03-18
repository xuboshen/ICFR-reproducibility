from functools import reduce
from data_structures.trees import Tree, Node, Leaf, randomTree
from data_structures.regret_minimizers import InternalRM, ExternalRM
import random
import math
import re
import time

class CFRTree:
    """
    Wrapper around an extensive-form tree for holding additional CFR-related code and data.
    """

    def __init__(self, base_tree):
        """
        Create a CFRTree starting from a base Tree.
        """

        self.root = CFRChanceNode(base_tree.root) if base_tree.root.isChance() else CFRNode(base_tree.root)
        self.information_sets = {}
        self.numOfActions = 0
        self.numOfPlayers = base_tree.numOfPlayers

        nodes_to_expand = [ self.root ]

        while(len(nodes_to_expand) > 0):
            node = nodes_to_expand.pop()

            if(node.isChance()):
                for child in node.children:
                    nodes_to_expand.append(child)
                continue

            iset_id = node.base_node.information_set
            if(iset_id < 0):
                # This is a leaf (or an error has occurred)
                continue

            for child in node.children:
                nodes_to_expand.append(child)
                self.numOfActions += 1

            if(iset_id in self.information_sets):
                node.information_set = self.information_sets[iset_id]
                node.information_set.addNode(node)
            else:
                iset = CFRInformationSet(iset_id, node.player, len(node.children), node.base_node.getSequence(node.player), self)
                iset.addNode(node)
                self.information_sets[iset_id] = iset
                node.information_set = iset

        self.infosets_by_player = []
        for p in range(self.numOfPlayers):
            p_isets = list(filter(lambda i: i.player == p, self.information_sets.values()))
            self.infosets_by_player.append(p_isets)

        for iset in self.information_sets.values():
            seq = iset.sequence

            for n in iset.nodes:
                if(n.base_node.getSequence(iset.player) != seq):
                    print("Sequences = ")
                    for node in iset.nodes:
                        print(node.base_node.getSequence(iset.player))
                    raise Exception("ERROR: This tree is not a game with perfect recall. Nodes of information set "
                                    + str(iset.id) + " (" + reduce(lambda acc, el: str(el.base_node.id) + ', ' + acc, iset.nodes, "") + \
                                    ") have different sequences.")

            # Setup children leaves and children infosets for this information set
            iset.children_infoset = []
            iset.children_leaves = []
            for a in range(iset.action_count):
                iset.children_infoset.append(list(iset.getChildrenInformationSets(a)))
                iset.children_leaves.append(list(iset.getChildrenLeaves(a)))

    def sampleActionPlan(self):
        """
        Sample a joint action plan from the tree (one action per each information set).
        """

        actionPlan = {}
        for id in self.information_sets:
            actionPlan[id] = self.information_sets[id].sampleAction()
        return actionPlan

    def getUtility(self, joint):
        """
        Get the utility obtained by the players when playing a given joint strategy over this tree.
        """

        utility = [0] * self.numOfPlayers

        for actionPlanString in joint.plans:
            # ?
            actionPlan = CFRJointStrategy.stringToActionPlan(actionPlanString)
            frequency = joint.plans[actionPlanString] / joint.frequencyCount

            leafUtility = self.root.utilityFromActionPlan(actionPlan, default = [0] * self.numOfPlayers)
            for i in range(len(utility)):
                utility[i] += leafUtility[i] * frequency

        return utility
# ?
    def checkEquilibrium(self, joint):

        epsilons = self.getUtility(joint)

        for p in range(self.numOfPlayers):
            self.root.clearMarginalizedUtility()

            for (actionPlanString, frequency) in joint.plans.items():
                self.root.marginalizePlayer(CFRJointStrategy.stringToActionPlan(actionPlanString),
                                            frequency / joint.frequencyCount, p)

            root_infosets = list(filter(lambda i: i.sequence == {}, self.infosets_by_player[p]))

            epsilons[p] -= sum(map(lambda i: i.V(), root_infosets))

        return epsilons
# ? 
    def checkMarginalsEpsilon(self):

        epsilons = self.root.getExpectedUtility()

        for p in range(self.numOfPlayers):
            self.root.clearMarginalizedUtility()
            self.root.marginalizePlayerFromBehaviourals(1, p)

            root_infosets = list(filter(lambda i: i.sequence == {}, self.infosets_by_player[p]))

            epsilons[p] -= sum(map(lambda i: i.V(), root_infosets))

        return epsilons

    def buildJointFromMarginals(self, select_optimal_plan = True):

        leaves = set()
        self.root.find_terminals(leaves)

        all_players_plan_distributions = []

        for p in range(self.numOfPlayers):
            self.root.buildRealizationForm(p, 1)
            player_plan_distribution = []

            nonZeroLeaf = True
            while nonZeroLeaf:
                # for l in leaves:
                #     print((l.id, l.base_node.getSequence(p), l.omega))

                best_plan = None
                best_plan_value = 0
                best_plan_leaf = None

                for l in leaves:
                    if l.omega == 0:
                        continue

                    (plan, val) = self.builSupportingPlan(l, p)
                    if val > best_plan_value:
                        best_plan = plan
                        best_plan_value = val
                        best_plan_leaf = l

                        if not select_optimal_plan:
                            break

                if best_plan == None:
                    for l in leaves:
                        print((l.id, l.base_node.getSequence(p), l.omega))
                    raise Exception("ERROR")

                for t in self.root.terminalsUnderPlan(p, best_plan):
                    t.omega -= best_plan_value

                nonZeroLeaf = False
                for l in leaves:
                    if l.omega > 0.001:
                        nonZeroLeaf = True
                        break

                player_plan_distribution.append((best_plan, best_plan_value))

            all_players_plan_distributions.append(player_plan_distribution)

        # Merge plans of all players into a single joint distribution (cross product)
        joint_distribution = all_players_plan_distributions[0]

        for p in range(1, self.numOfPlayers):
            new_joint_distribution = []
            for j in joint_distribution:
                for d in all_players_plan_distributions[p]:
                    joint_plan = {**j[0], **d[0]}
                    joint_probability = j[1] * d[1]
                    new_joint_distribution.append((joint_plan, joint_probability))
            joint_distribution = new_joint_distribution

        reduced_joint_distribution = []

        for (joint_plan, joint_probability) in joint_distribution:
            reduced_joint_plan = CFRJointStrategy.reduceActionPlan(joint_plan, self)
            reduced_joint_distribution.append((reduced_joint_plan, joint_probability))

        return reduced_joint_distribution

    def buildJointFromMarginals_AllPlayersTogether(self):

        leaves = set()
        self.root.find_terminals(leaves)

        self.root.buildRealizationForm(None, 1)
        plan_distribution = []

        nonZeroLeaf = True
        i = 0
        while nonZeroLeaf and i < 10:

            best_plan = None
            best_plan_value = 0
            best_plan_leaf = None

            for l in leaves:
                if l.omega == 0:
                    continue

                (plan, val) = self.builSupportingPlan(l, None)
                if val > best_plan_value:
                    best_plan = plan
                    best_plan_value = val
                    best_plan_leaf = l

            if best_plan == None:
                for l in leaves:
                    print((l.id, l.base_node.getSequence(None), l.omega))
                raise Exception("ERROR")

            for t in self.root.terminalsUnderPlan(None, best_plan):
                t.omega -= best_plan_value

            i += 1
            nonZeroLeaf = False
            for l in leaves:
                if l.omega > 0.001:
                    nonZeroLeaf = True
                    break

            plan_distribution.append((best_plan, best_plan_value))

        return plan_distribution

    def builSupportingPlan(self, leaf, targetPlayer):

        if targetPlayer != None:
            player_infosets = self.infosets_by_player[targetPlayer]
        else:
            player_infosets = list(self.information_sets.values())

        for iset in player_infosets:
            iset.supportingPlanInfo = None   

        plan = leaf.base_node.getSequence(targetPlayer)
        weight = leaf.omega

        for (iset_id, action) in plan.items():
            self.information_sets[iset_id].supportingPlanInfo = (action, leaf.omega)

        for iset in player_infosets:
            iset.updateSupportingPlan(targetPlayer)
            (a, w) = iset.supportingPlanInfo
            plan[iset.id] = a
            weight = min(weight, w)

        weight = min(self.root.terminalsUnderPlan(targetPlayer, plan), key = lambda t: t.omega).omega

        return (plan, weight)

class CFRNode:
    """
    Wrapper around an extensive-form node for holding additional CFR-related code and data.
    """

    def __init__(self, base_node, parent = None):
        """
        Create a CFRNode starting from a base Node.
        It recursively creates also all the CFRNodes from the children of the base Node, up to the leaves.
        """

        self.id = base_node.id
        self.parent = parent
        self.player = base_node.player
        self.children = []
        self.incoming_action = base_node.incoming_action
        # self.reachability = -1
        for child in base_node.children:
            n = CFRChanceNode(child, self) if child.isChance() else CFRNode(child, self)
            self.children.append(n)

# icfr tag
        # self.inRM = InternalRM()
        # self.exRM = {}
        # self.externalsigma = ""
        self.T = 0

        self.visits = 0
        self.base_node = base_node

        self.is_leaf = len(self.children) == 0
        self.utility = [0] * len(self.children)
        if(self.isLeaf()):
            self.utility = base_node.utility

    def isLeaf(self):
        return self.is_leaf

    def isChance(self):
        return False

    def getAllLeafVisits(self):
        if(self.isLeaf()):
            return self.visits
        else:
            return reduce(lambda x, y: x + y, map(lambda i: i.getAllLeafVisits(), self.children))

    def getLeafDistribution(self, norm_factor):
        """
        Returns the distribution over the leaves under this node, normalized by a given norm_factor.
        It uses the number of visits of the node stored by the execution of the CFR code.
        """

        if(self.isLeaf()):
            return str(self.visits / norm_factor) + ":" + str(self.base_node) + "\n"
        else:
            return reduce(lambda x, y: x + y,
                          map(lambda i: i.getLeafDistribution(norm_factor), self.children))
# ?
    def utilityFromActionPlan(self, actionPlan, default = None):
        """
        Return the utility from the leaf reached following actionPlan and starting from this node.
        If no leaf is reached, return the default value.
        """

        if(self.isLeaf()):
            return self.utility
        elif(self.information_set.id not in actionPlan):
            return default
        else:
            return self.children[actionPlan[self.information_set.id]].utilityFromActionPlan(actionPlan, default)

    def utilityFromJointSequence(self, js):
        """
        Return the expected utility when players follow the joint sequence 'js'. (Chance's actions are not considered in 'js')
        """
        if(self.isLeaf()):
            return self.utility
        elif(self.information_set.id not in js[self.player]):
            return tuple(0 for p in js)
        else:
            cur_player = self.player
            cur_infoset = self.information_set.id
            new_action = js[cur_player][cur_infoset]

            return self.children[new_action].utilityFromJointSequence(js)

    def find_terminals(self, terminals):
        if(self.isLeaf()):
            terminals.add(self)
        else:
            for child in self.children:
                child.find_terminals(terminals)

    def reachableTerminals(self, js):
        """
        returns the set of leaves reachable with the given joint sequences
        """
        if(self.isLeaf()):
            return {self.id}
        elif(self.information_set.id in js[self.player]):
            cur_player = self.player
            cur_infoset = self.information_set.id
            new_action = js[cur_player][cur_infoset]

            return self.children[new_action].reachableTerminals(js)

        return set()

    def utilityFromModifiedActionPlan(self, actionPlan, modification, default = None):
        """
        Return the utility from the leaf reached following a modification of actionPlan and starting from this node.
        Action listed in modification are followed first, if no one is found then actionPlan is followed.
        If no leaf is reached, return the default value.
        """

        if(self.isLeaf()):
            return self.utility

        id = self.information_set.id

        if(id in modification and modification[id] >= 0):
            # As if actionPlan[id] was overwritten
            return self.children[modification[id]].utilityFromModifiedActionPlan(actionPlan, modification, default)
        if(id in modification and modification[id] < 0):
            # As if actionPlan[id] was deleted
            return default
        if(id in actionPlan):
            return self.children[actionPlan[id]].utilityFromModifiedActionPlan(actionPlan, modification, default)

        return default

    def computeReachability(self, actionPlan, pi):
        """
        Computes the reachability of this node and its descendants under the given action plan, provided a vector
        pi containing the probability of reaching this node from the point of view of each player.
        """

        if(self.isLeaf() or sum(pi) == 0):
            return

        self.information_set.reachability = max(self.information_set.reachability, pi[self.player])

        sampled_action = actionPlan[self.information_set.id]

        for a in range(len(self.children)):
            if a == sampled_action:
                self.children[sampled_action].computeReachability(actionPlan, pi)
            else:
                self.children[a].computeReachability(actionPlan, pi[:self.player] + [ 0 ] + pi[self.player+1:])

    def buildRealizationForm(self, targetPlayer, p):
        """
        Builds the realization form, i.e. a distribution over the leaves of the tree that is
        equivalent to the current marginal strategy of targetPlayer.
        """

        if self.isLeaf():
            self.omega = p
            return

        if self.player != targetPlayer and targetPlayer != None:
            for node in self.children:
                node.buildRealizationForm(targetPlayer, p)
            return

        for a in range(len(self.children)):
            a_prob = self.information_set.current_strategy[a]
            self.children[a].buildRealizationForm(targetPlayer, p * a_prob)

    def terminalsUnderPlan(self, targetPlayer, plan):
        if self.isLeaf():
            return [ self ]

        terminals = []

        if targetPlayer == None or self.player == targetPlayer:
            action = plan[self.information_set.id]
            terminals = self.children[action].terminalsUnderPlan(targetPlayer, plan)
        else:
            for node in self.children:
                terminals += node.terminalsUnderPlan(targetPlayer, plan)

        return terminals

    def isActionPlanLeadingToInfoset(self, actionPlan, targetInfoset):
        """
        Returns true if the path obtained by the given action plan leads to the target information set.
        """

        if(self.information_set == targetInfoset):
            return True

        if(not self.information_set.id in actionPlan):
            return False

        action = actionPlan[self.information_set.id]

        if(action == -1 or self.children[action].isLeaf()):
            return False
        else:
            return self.children[action].isActionPlanLeadingToInfoset(actionPlan, targetInfoset)

    def clearMarginalizedUtility(self):
        """
        Clear the marginalized utility in the leaves.
        """

        if self.isLeaf():
            self.marginalized_utility = 0
        else:
            for child in self.children:
                child.clearMarginalizedUtility()
# ?
    def marginalizePlayer(self, actionPlan, frequency, marginalized_player):
        """
        Propagate up to the leaves the frequency of an action plan, ignoring the actions
        of the player to be marginalized (as he is the one for which we are searching a best reponse).
        """

        if self.isLeaf():
            self.marginalized_utility += frequency * self.utility[marginalized_player]
        elif self.player == marginalized_player:
            for child in self.children:
                child.marginalizePlayer(actionPlan, frequency, marginalized_player)
        else:
            self.children[actionPlan[self.information_set.id]].marginalizePlayer(actionPlan, frequency, marginalized_player)
# ?
    def marginalizePlayerFromBehaviourals(self, p, marginalized_player):
        """
        Propagate up to the leaves the current average behavioural strategies, ignoring the actions
        of the player to be marginalized (as he is the one for which we are searching a best reponse).
        """

        if self.isLeaf():
            self.marginalized_utility += p * self.utility[marginalized_player]
        elif self.player == marginalized_player:
            for child in self.children:
                child.marginalizePlayerFromBehaviourals(p, marginalized_player)
        else:
            s = self.distribution if self.isChance() else self.information_set.getAverageStrategy()
            for a in range(len(self.children)):
                self.children[a].marginalizePlayerFromBehaviourals(p * s[a], marginalized_player)

    def getChildrenInformationSets(self, action, player):
        """
        Get all the information sets of the given player directly reachable (e.g. no other infoset of the same player in between)
        by here when the given action was played in the parent information set of the given player.
        """

        if self.isLeaf():
            return set()

        if action < 0 and self.player == player:
            return set([self.information_set])
        
        if self.player == player:
            return self.children[action].getChildrenInformationSets(-1, player)
        else:
            res = set()
            for child in self.children:
                res.update(child.getChildrenInformationSets(action, player))
            return res

    def getChildrenLeaves(self, action, player):
        """
        Get all the leaves directly reachable (e.g. no other infoset of the same player in between)
        by here when the given action was played in the parent information set of the given player.
        """

        if self.isLeaf():
            return set([self])

        if action < 0 and self.player == player:
            return set()

        if self.player == player:
            return self.children[action].getChildrenLeaves(-1, player)
        else:
            res = set()
            for child in self.children:
                res.update(child.getChildrenLeaves(action, player))
            return res
# ?
    def getExpectedUtility(self):
        """
        Get the expected utility from this node on under the current average behavioural strategies.
        """

        if self.isLeaf():
            return self.utility

        u = None
        s = self.distribution if self.isChance() else self.information_set.getAverageStrategy()

        for a in range(len(self.children)):
            child_u = self.children[a].getExpectedUtility()

            if u == None:
                u = [cu * s[a] for cu in child_u]
            else:
                for p in range(len(child_u)):
                    u[p] += child_u[p] * s[a]

        return u

class CFRChanceNode(CFRNode):
    """
    Wrapper around an extensive-form chance node for holding additional CFR-related code and data.
    """

    def __init__(self, base_node, parent = None):
        CFRNode.__init__(self, base_node, parent)
        self.distribution = base_node.distribution

    def isChance(self):
        return True

    def sampleAction(self):
        """
        Sample an action from the static distribution of this chance node.
        """

        r = random.random()
        count = 0

        for i in range(len(self.distribution)):
            count += self.distribution[i]
            if(r < count):
                return i

    def computeReachability(self, actionPlan, pi):
        """
        Computes the reachability of this node and its descendants under the given action plan, provided a vector
        pi containing the probability of reaching this node from the point of view of each player.
        """

        for a in range(len(self.children)):
            self.children[a].computeReachability(actionPlan, pi)

    def buildRealizationForm(self, targetPlayer, p):
        """
        Builds the realization form, i.e. a distribution over the leaves of the tree that is
        equivalent to the current marginal strategy of targetPlayer.
        """

        for a in range(len(self.children)):
            self.children[a].buildRealizationForm(targetPlayer, p)  # Do not factorize chance in

    def utilityFromActionPlan(self, actionPlan, default = None):
        """
        Return the utility from the leaf reached following actionPlan and starting from this node.
        If no leaf is reached, return the default value.
        """

        u = default

        for i in range(len(self.children)):
            childUtility = self.children[i].utilityFromActionPlan(actionPlan, default)

            if(u == default):
                u = childUtility.copy()
                for p in range(len(childUtility)):
                    u[p] *= self.distribution[i]
            else:
                for p in range(len(childUtility)):
                    u[p] += childUtility[p] * self.distribution[i]

        return u

    def utilityFromJointSequence(self, js):
        """
        Returns the convex combination of expected utilities obtained from actions at the current chance node.
        """
        expected_utility = [0.0 for p in js]

        for child_id in range(len(self.children)):
            observed_utility = self.children[child_id].utilityFromJointSequence(js)
            for p in range(len(js)):
                expected_utility[p] += observed_utility[p] * self.distribution[child_id]

        return tuple(expected_utility)

    def find_terminals(self, terminals):
        for child_id in range(len(self.children)):
            self.children[child_id].find_terminals(terminals)

    def reachableTerminals(self, js):
        """
        returns the set of reachable terminals given the joint sequence 'js'.
        At chance nodes, we perform the union of terminals reachable through each of the chance moves
        """
        cum=set()
        for child in self.children:
            cum = cum.union(child.reachableTerminals(js))
        return cum


    def utilityFromModifiedActionPlan(self, actionPlan, modification, default = None):
        """
        Return the utility from the leaf reached following a modification of actionPlan and starting from this node.
        Action listed in modification are followed first, if no one is found then actionPlan is followed.
        If no leaf is reached, return the default value.
        """

        u = default

        for i in range(len(self.children)):
            childUtility = self.children[i].utilityFromModifiedActionPlan(actionPlan, modification, default)

            if(u == default):
                for p in range(len(childUtility)):
                    u[p] = childUtility[p] * self.distribution[i]
            else:
                for p in range(len(childUtility)):
                    u[p] += childUtility[p] * self.distribution[i]

        return u

    def isActionPlanLeadingToInfoset(self, actionPlan, targetInfoset):
        """
        Returns true if the path obtained by the given action plan leads to the target information set.
        """

        res = False
        for child in self.children:
            res = res or child.isActionPlanLeadingToInfoset(actionPlan, targetInfoset)
        return res

    def clearMarginalizedUtility(self):
        """
        Clear the marginalized utility in the leaves.
        """

        for child in self.children:
            child.clearMarginalizedUtility()

    def marginalizePlayer(self, actionPlan, frequency, marginalized_player):
        """
        Propagate up to the leaves the frequency of an action plan, ignoring the actions
        of the player to be marginalized (as he is the one for which we are searching a best reponse)
        """

        for (p, child) in zip(self.distribution, self.children):
            child.marginalizePlayer(actionPlan, frequency * p, marginalized_player)

class CFRInformationSet:
    """
    Represents an information set and all the code and data related to it when used for the CFR algorithm.
    """

    def __init__(self, id, player, action_count, sequence, cfr_tree, random_initial_strategy = False):
        """
        Create an information set with a given id, player, action_count (i.e. number of actions available in its nodes),
        sequence and cfr_tree it belongs to.
        If random_initial_strategy is True, it is initialized with a random local strategy; otherwise is uses the usual
        uniform distribution over actions.
        """

        self.id = id
        self.player = player
        self.action_count = action_count
        self.sequence = sequence
        self.nodes = []
       
        self.cfr_tree = cfr_tree

        self.reachability = -1
# icfr tag
        self.inRM = InternalRM()
        self.exRM = {}
        self.externalsigma = ""
        self.utility = [0] * action_count
        self.mu_T = [0] * action_count

        self.cumulative_regret = [0 for a in range(self.action_count)]
        self.cumulative_strategy = [0 for a in range(self.action_count)]
        self.current_strategy = [1 / self.action_count for a in range(self.action_count)]

        if(random_initial_strategy):
            self.current_strategy = [random.random() for a in range(self.action_count)]
            sum = reduce(lambda x, y: x + y, self.current_strategy, 0)
            self.current_strategy = [self.current_strategy[a] / sum for a in range(self.action_count)]

        self.cached_V = None

    def __str__(self):
        return "<InfoSet" + str(self.id) + " - Player" + str(self.player) + ">"

    def __repr__(self):
        return str(self)

    def addNode(self, node):
        self.nodes.append(node)

    def updateCurrentStrategy(self):
        """
        Recalculate the current strategy based on the cumulative regret.
        """

        sum = reduce(lambda x, y: x + max(0, y), self.cumulative_regret, 0)

        for a in range(0, self.action_count):
            if(sum > 0):
                self.current_strategy[a] = max(0, self.cumulative_regret[a]) / sum
            else:
                self.current_strategy[a] = 1 / self.action_count
# ?
    def getAverageStrategy(self):
        """
        Get the average strategy experienced so far.
        """

        # norm = reduce(lambda x, y: x + y, self.cumulative_strategy)
        # if(norm > 0):
        #     return [self.cumulative_strategy[a] / norm for a in range(self.action_count)]
        # else:
        #     return [1 / self.action_count for a in range(self.action_count)]
        return [i / self.cfr_tree.root.T for i in self.mu_T]

    def sampleAction(self):
        """
        Sample an action from the current strategy.
        """

        if(self.nodes[0].isChance()):
            return self.nodes[0].sampleAction()

        r = random.random()
        count = 0

        for i in range(len(self.current_strategy)):
            count += self.current_strategy[i]
            if(r < count):
                return i
# ? counterfactual value
    def V(self):
        v = [0 for a in range(self.action_count)]

        for a in range(self.action_count):
            v[a] += sum(map(lambda i: i.V(), self.children_infoset[a]))
            v[a] += sum(map(lambda l: l.marginalized_utility, self.children_leaves[a]))

        return max(v)

    def getChildrenOfPlayer(self, player):
        """
        Get all the information sets (including this one) of the given player and descendants of this information set.
        """

        children = set()
        for node in self.nodes:
            for child in node.children:
                if(not child.isLeaf()):
                    children.update(child.information_set.getChildrenOfPlayer(player))
        if(self.player == player):
            children.add(self)
        return children

    def getChildrenInformationSets(self, action):
        """
        Get all the information sets of the given player directly reachable (e.g. no other infoset of the same player in between)
        by this one when the given action was played in the parent information set of the given player.
        """
        
        res = set()
        for node in self.nodes:
            res.update(node.getChildrenInformationSets(action, self.player))
        return res

    def getChildrenLeaves(self, action):
        """
        Get all the leaves directly reachable (e.g. no other infoset of the same player in between)
        by this information set when the given action was played in the parent information set of the given player.
        """

        res = set()
        for node in self.nodes:
            res.update(node.getChildrenLeaves(action, self.player))
        return res

    def updateSupportingPlan(self, targetPlayer):
        # TODO: implement also the "targetPlayer == None" case

        if self.supportingPlanInfo != None:
            return

        action = -1

        for a in range(self.action_count):

            if targetPlayer != None:
                children_infosets = self.children_infoset[a]
                children_leaves = self.children_leaves[a]
            else:
                children_infosets = set()
                children_leaves = []

                for node in self.nodes:
                    child = node.children[a]
                    if child.isLeaf():
                        children_leaves.append(child)
                    else:
                        children_infosets.add(child.information_set)

                children_infosets = list(children_infosets)

            a_omega = 1
            for iset in children_infosets:
                iset.updateSupportingPlan(targetPlayer)
                (_, w) = iset.supportingPlanInfo
                a_omega = min(a_omega, w)
            for leaf in children_leaves:
                a_omega = min(a_omega, leaf.omega)

            if action == -1 or a_omega > omega:
                action = a
                omega = a_omega

        self.supportingPlanInfo = (action, omega)

    def computeReachability(self, actionPlan):

        self.reachability = 1
        sampled_action = actionPlan[self.id]

        for iset in self.children_infoset[sampled_action]:
            iset.computeReachability(actionPlan)

class CFRJointStrategy:
    """
    A joint strategy progressively built by the SCFR algorithm.
    """

    def __init__(self, maxPlanCount = -1):
        """
        Create a joint strategy able to hold a maximum of maxPlanCount plans.
        If the value is not given, it is able to hold an arbitrary number of plans.
        """

        self.maxPlanCount = maxPlanCount
        self.frequencyCount = 0
        self.plans = {}

        CFRJointStrategy.action_plans_cache = {}

    def addActionPlan(self, actionPlan, weight = 1):
        """
        Add an action plan (a dictionary from information set id to action) to the joint strategy.
        Optionally a weight can be provided, to insert non-uniformly sampled plans.
        """

        string = CFRJointStrategy.actionPlanToString(actionPlan)

        if(string in self.plans):
            self.plans[string] += weight
            self.frequencyCount += weight
        elif(self.maxPlanCount == -1 or len(self.plans) < self.maxPlanCount):
            self.plans[string] = weight
            self.frequencyCount += weight
        else:
            # Remove the least frequent plan
            plan = min(self.plans, key = lambda p: self.plans[p])
            self.frequencyCount -= self.plans[plan]
            del self.plans[plan]

            # Add the new one
            self.plans[string] = weight
            self.frequencyCount += weight

    def addJointDistribution(self, jointDistribution):
        """

        """

        for (plan, prob) in jointDistribution:
            self.addActionPlan(plan, prob)

    def actionPlanToString(actionPlan):
        """
        Transform an action plan in dictionary representation to the corresponding string representation.
        """

        string = ""

        for infoset in actionPlan:
            string += "a" + str(infoset) + "." + str(actionPlan[infoset])

        return string

    action_plans_cache = {}

    def stringToActionPlan(string):
        """
        Transform an action plan in string representation to the corresponding dictionary representation.
        """

        if(string in CFRJointStrategy.action_plans_cache):
            return CFRJointStrategy.action_plans_cache[string]

        actions = string.split("a")[1:]
        actionPlan = {}

        for a in actions:
            (infoset, action) = a.split(".")
            actionPlan[int(infoset)] = int(action)

        CFRJointStrategy.action_plans_cache[string] = actionPlan

        return actionPlan

    def reduceActionPlan(actionPlan, tree):
        """
        Transform an action plan into a reduced one, in the given tree.
        """

        reducedActionPlan = {}

        for iset in tree.information_sets.values():
            iset.reachability = 0

        #tree.root.computeReachability(actionPlan, [1 for _ in range(tree.numOfPlayers)])

        for iset in tree.information_sets.values():
            if len(iset.sequence) == 0:
                iset.computeReachability(actionPlan)

        for (id, iset) in tree.information_sets.items():
            # reachability = max(map(lambda n: n.reachability, iset.nodes))
            if(iset.reachability > 0):
                reducedActionPlan[id] = actionPlan[id]

        return reducedActionPlan
