import random

class Node:
    def __init__(self, id, loc, nQubits, topo):
        """
        Initialize Node class

        :param id: node id
        :type id: `int`
        :param loc: location of node
        :type loc: `tuple`
        :param nQubits: number of qubits on node
        :type nQubits: `int`
        :param topo: the topology
        :type topo: `Topo`
        """
        self.id = id
        self.loc = loc
        self.remainingQubits = int(nQubits)
        self.q = topo.q
        self.internalLinks = []
        self.neighbors = [] 
        self.links = [] 

    def attemptSwapping(self, l1, l2): 
        """
        Attampt swapping on node

        :return: True if swapping success
        :rtype: `bool`
        :param l1: link 1 on node attampts swapping
        :type l1: `Link`
        :param l2: link 2 on node attampts swapping
        :type l2: `Link`
        """
        if l1.n1 == self:    
            l1.s1 = True
        else:       
            l1.s2 = True
        
        if l2.n1 == self:    
            l2.s1 = True
        else: 
            l2.s2 = True
        
        b = random.random() <= self.q
        if b:
            self.internalLinks.append((l1, l2))
            
        return b

    def assignIntermediate(self): 
        """
        Assign a qubit on node

        """
        self.remainingQubits -= 1

    def clearIntermediate(self):
        """
        Release a qubit on node

        """
        self.remainingQubits += 1
        