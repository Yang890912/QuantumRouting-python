from .Node import Node
import random
import math

class Link:
    
    def __init__(self, topo, n1: Node, n2: Node, s1: bool, s2: bool, id: int, l: float):
        self.id, self.n1, self.n2, self.s1, self.s2, self.alpha = id, n1, n2, s1, s2, topo.alpha
        self.assigned = False
        self.entangled = False
        self.p = math.exp(-self.alpha * l)
        self.lifetime = 0

    def theOtherEndOf(self, n: Node): 
        if (self.n1 == n): 
            tmp = self.n2
        elif (self.n2 == n): 
            tmp = self.n1 
        return tmp
    def contains(self, n: Node):  
        return self.n1 == n or self.n2 == n
    def swappedAt(self, n: Node): 
        return (self.n1 == n and self.s1 or self.n2 == n and self.s2)
    def swappedAtTheOtherEndOf(self, n: Node):  
        return (self.n1 == n and self.s2 or self.n2 == n and self.s1)
    def swapped(self):  
        return self.s1 or self.s2
    def notSwapped(self):  
        return not self.swapped()


    def assignQubits(self):
        # prevState = self.assigned
        self.assigned = True
        self.n1.remainingQubits -= 1
        self.n2.remainingQubits -= 1
  
    def clearEntanglement(self):
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
        b = (self.assigned and self.p >= random.random()) or self.entangled
        self.entangled = b
        return b
  
    def assignable(self): 
        return not self.assigned and self.n1.remainingQubits > 0 and self.n2.remainingQubits > 0
