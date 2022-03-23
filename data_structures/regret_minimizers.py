from cv2 import norm
import numpy as np
from scipy.linalg import null_space


class RegretMinimizer:
    '''
    member:
        regretSum: cumulative regret
        utility: a vector of utility with length of N actions.
    method:
        recommend(): returns a specific action according to the observed utilities
        observe(self, utility): renew utility of this regretminimizers
    '''
    def __init__(self, actionNumbers = 2):
        self.actionNumbers = actionNumbers
        self.regretSum = np.zeros(actionNumbers)
        self.strategySum = np.zeros(actionNumbers)
        self.utility = np.zeros(actionNumbers)
        self.recommended_action = -1
    
    def recommend(self):
        '''
            returns the recommended action index, from 1 to actionNumber
        '''
        strategy = self.getStrategy()
        action = self.getAction(strategy)
        self.recommended_action = action
        return self.recommended_action

    def observe(self, utility):
        self.utility = np.array(utility)
        regret = self.utility - self.utility[self.recommended_action]
        self.regretSum = self.regretSum + regret
 
    def getStrategy(self):
        pass

    def getAverageStrategy(self):
        normalizingAverageStrategy = np.sum(self.strategySum)
        if (normalizingAverageStrategy > 0):
            averageStrategy = self.strategySum / normalizingAverageStrategy
        else:
            averageStrategy = np.ones(self.actionNumbers) /self.actionNumbers
        return averageStrategy
    
    def getAction(self, strategy):
        preSumStrategy = np.zeros(strategy.size + 1)
        for i in range(1, strategy.size + 1):
            preSumStrategy[i] = preSumStrategy[i - 1] + strategy[i - 1]
        left = 0
        right = strategy.size
        r = np.random.random()
        while (left < right): 
            mid = (left + right) //2
            if (preSumStrategy[mid] >= r):
                right = mid
            else:
                left = mid + 1
        return right - 1

class InternalRM(RegretMinimizer):
    def __init__(self, actionNumbers = 2):
        self.actionNumbers = actionNumbers
        self.regretSum = np.zeros((actionNumbers, actionNumbers))
        self.strategySum = np.zeros((actionNumbers, actionNumbers))
        self.utility = np.zeros((actionNumbers, actionNumbers))
        self.recommended_action = -1 
        self.rcmd_action = np.zeros(actionNumbers, dtype=int)
        self.p = None
    # ?
    def observe(self, utility):
        for i in range(self.actionNumbers):
            self.utility[i] = self.p[i] * utility
            # self.regretSum[i] = self.regretSum[i] + self.utility[i] - self.utility[i][self.recommended_action]
            # print(self.rcmd_action[i])
            self.regretSum[i] = self.regretSum[i] + self.utility[i] - self.utility[i][self.rcmd_action[i]]
    
    def getStrategy(self):
        AN_strategy = np.maximum(self.regretSum, 0)
        normalizingStrategy = np.sum(AN_strategy, 1)
        for i in range(AN_strategy.shape[0]):
            if (normalizingStrategy[i] > 0):
                AN_strategy[i] = AN_strategy[i] / normalizingStrategy[i]
            else:
                AN_strategy[i] = np.ones(AN_strategy.shape[0]) / self.actionNumbers
            self.rcmd_action[i] = self.getAction(AN_strategy[i])
        self.strategySum = self.strategySum + AN_strategy
# https://github.com/scipy/scipy/issues/10284
        p = null_space(AN_strategy.T - np.eye(AN_strategy.shape[0]))
        if (p[0] < 0):
            p = -p
        self.p = p / np.sum(p)
        return self.p

class ExternalRM(RegretMinimizer):
    def __init__(self, action_count):
        super().__init__(action_count)
   
    def getStrategy(self):
        strategy = np.maximum(self.regretSum, 0)
        normalizingStrategy = np.sum(strategy)
        if (normalizingStrategy > 0):
            strategy = strategy / normalizingStrategy
        else:
            strategy = np.ones(self.actionNumbers) / self.actionNumbers
        self.strategySum = self.strategySum + strategy
        return strategy

