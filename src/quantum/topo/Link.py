from .Node import Node
import random
import math

class Link:
    def __init__(self, topo, n1, n2, s1, s2, id, l):
        """
        Initialize Link class

        :param topo: the topology
        :type topo: `Topo`
        :param n1: node 1 on link
        :type n1: `Node`
        :param n2: node 2 on link
        :type n2: `Node`
        :param s1: node 1 on link whether swapped
        :type s1: `bool`
        :param s2: node 2 on link whether swapped
        :type s2: `bool`
        :param id: link id
        :type id: `int`
        :param l: length of link
        :type l: `float`
        """
        self.id, self.n1, self.n2, self.s1, self.s2, self.alpha = id, n1, n2, s1, s2, topo.alpha
        self.assigned = False
        self.entangled = False
        self.p = math.exp(-self.alpha * l)
        self.lifetime = 0

    def theOtherEndOf(self, n):
        """
        Return the other end node on link

        :return: the other end node
        :rtype: `Node`
        :param n: the node we know
        :type n: `Node`
        """
        if (self.n1 == n): 
            tmp = self.n2
        elif (self.n2 == n): 
            tmp = self.n1 

        return tmp

    def contains(self, n):
        """
        Return whether node n is on link

        :return: whether node n is on link
        :rtype: `bool`
        :param n: the node we know
        :type n: `Node`
        """ 
        return self.n1 == n or self.n2 == n

    def swappedAt(self, n): 
        """
        Return whether node n on link swapped

        :return: whether node n on link swapped
        :rtype: `bool`
        :param n: the node we know
        :type n: `Node`
        """ 
        return (self.n1 == n and self.s1 or self.n2 == n and self.s2)

    def swappedAtTheOtherEndOf(self, n):  
        """
        Return whether the other node on link swapped 

        :return: whether the other node on link swapped 
        :rtype: `bool`
        :param n: the node we know
        :type n: `Node`
        """ 
        return (self.n1 == n and self.s2 or self.n2 == n and self.s1)

    def swapped(self):
        """
        Return link whether swapped 

        :return: link whether swapped 
        :rtype: `bool`
        """ 
        return self.s1 or self.s2

    def notSwapped(self):
        """
        Return link whether not swapped 

        :return: link whether not swapped 
        :rtype: `bool`
        """ 
        return not self.swapped()

    def assignQubits(self):
        """
        Assign Qubits for nods on link

        """ 
        self.assigned = True
        self.n1.remainingQubits -= 1
        self.n2.remainingQubits -= 1
  
    def clearEntanglement(self):
        """
        Clear entanglement on link

        """ 
        preState = self.assigned
        self.s1 = False
        self.s2 = False
        self.assigned = False
        self.entangled = False
        self.lifetime = 0

        for internalLink in self.n1.internalLinks:
            if self in internalLink:
                self.n1.internalLinks.remove(internalLink)

        for internalLink in self.n2.internalLinks:
            if self in internalLink:
                self.n2.internalLinks.remove(internalLink)

        if preState:
            self.n1.remainingQubits += 1
            self.n2.remainingQubits += 1
    
    def clearPhase4Swap(self):
        """
        Clear Swap on link

        """ 
        self.s1 = False
        self.s2 = False
        self.entangled = False
        self.lifetime = 0

        for internalLink in self.n1.internalLinks:
            if self in internalLink:
                self.n1.internalLinks.remove(internalLink)

        for internalLink in self.n2.internalLinks:
            if self in internalLink:
                self.n2.internalLinks.remove(internalLink)
    
    def tryEntanglement(self):
        """
        Try entanglement on link

        :return: entanglement whether success
        :rtype: `bool`
        """ 
        b = (self.assigned and self.p >= random.random()) or self.entangled
        self.entangled = b
        
        return b
  
    def assignable(self):
        """
        Return whether the link is assignable

        :return: whether the link is assignable
        :rtype: `bool`
        """  
        return not self.assigned and self.n1.remainingQubits > 0 and self.n2.remainingQubits > 0
