import sys
import random
import heapq
import math
from queue import PriorityQueue
from tkinter.tix import AUTO
import networkx as nx
from .Node import Node
from .Link import Link
from random import sample


class TopoConnectionChecker:
    def setTopo(self, topo):
        """
        Set TopoConnectionChecker

        :param topo: the topology
        :type topo: `Topo`
        """
        self.topo = topo

    def checkConnected(self):
        """
        Return Topo whether connect

        :return: Topo whether connect
        :rtype topo: `bool`
        """
        self.visited = {node : False for node in self.topo.nodes}
        self.DFS(self.topo.nodes[0])
        for node in self.topo.nodes:
            if not self.visited[node]:
                return False
        return True

    def DFS(self, currentNode):
        self.visited[currentNode] = True
        for link in currentNode.links:
            nextNode = link.theOtherEndOf(currentNode)
            if not self.visited[nextNode]:
                self.DFS(nextNode)

class socialGenerator:
    def setTopo(self, topo):
        """
        Set social nerwork

        :param topo: the topology
        :type topo: `Topo`
        """
        self.topo = topo
        self.topo.socialRelationship = {node: [] for node in self.topo.nodes} 

    def genSocialRelationship(self):
        print('Generate Social Table ...')
        userNum = 20
        node2user = {}
        self.genSocialNetwork(userNum, self.topo.density)
        users = [i for i in range(userNum)]
        for i in range(len(self.topo.nodes)):
            user = sample(users, 1)
            node2user[i] = user[0]
        
        # n * n
        for i in range(len(self.topo.nodes)):
            for j in range(i+1, len(self.topo.nodes)):
                user1 = node2user[i]
                user2 = node2user[j]     
                if user1 in self.topo.SN[user2]:
                    n1 = self.topo.nodes[i]
                    n2 = self.topo.nodes[j]
                    self.topo.socialRelationship[n1].append(n2)
                    self.topo.socialRelationship[n2].append(n1)
                    # print('[system] Construct social relationship: node 1 ->', n1.id, ', node 2 ->', n2.id)

    def genSocialNetwork(self, userNum, density):
        """
        Generate social network

        :param userNum: number of users
        :type userNum: `int`
        :param density: density of network
        :type density: `float`
        """
        community1 = [0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 2, 2, 2, 2, 3, 2, 2, 2, 3, 2]  # 0.25
        community2 = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1]  # 0.50
        community3 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]  # 0.75
        community4 = [0 for _ in range(20)]                                        # 1.00
        community = {0.25 : community1, 0.50 : community2, 0.75 : community3, 1.00 : community4}

        self.topo.SN = {i: [] for i in range(userNum)}  # user to user
        community = community[density]
        for i in range(userNum):
            for j in range(i, userNum):
                # p = random.random()
                # if p <= density:
                #     self.topo.SN[i].append(j)
                #     self.topo.SN[j].append(i)
                if community[i] == community[j]:
                    self.topo.SN[i].append(j)
                    self.topo.SN[j].append(i)

class Topo:
    def __init__(self, G, q, a, degree, density, L):
        """
        Initialize Topo class

        :param G: the topology
        :type G: `networkx.waxman_graph`
        :param q: probability of swapping
        :type q: `float`
        :param a: alpha
        :type a: `float`
        :param degree: the least degree 
        :type degree: `int`
        :param density: for nexwork param
        :type density: `float`
        :param L: for nexwork param
        :type L: `float`
        """
        _nodes, _edges, _positions = G.nodes(), list(G.edges()), nx.get_node_attributes(G, 'pos')
        self.nodes = []
        self.links = []
        self.edges = [] 
        self.q = q
        self.alpha = a
        self.L = L
        self.density = density
        self.sentinel = Node(-1, (-1.0, -1.0), -1, self)
        #---
        self.socialRelationship = {}    # {n: []}
        self.shortestPathTable = {}     # {(src, dst): (path, weight, p)}
        self.expectTable = {}           # {(path1, path2) : expectRound}
        self.SN = {}
        #---

        # Construct neighbor table by int type
        _neighbors = {_node: [] for _node in _nodes}
        for _node in _nodes:
            (p1, p2) = _positions[_node]
            _positions[_node] = (p1 * 2000, p2 * 2000)
            _neighbors[_node] = list(nx.neighbors(G,_node))
          
        # Construct Node 
        for _node in _nodes:
            self.nodes.append(Node(_node, _positions[_node], random.random()*5+10 , self))  # 15~20
            usedNode = []
            usedNode.append(_node) 
            
            # Make the number of neighbors approach degree  
            if len(_neighbors[_node]) < degree - 1:  
                for _ in range(0, degree - 1 - len(_neighbors[_node])):
                    curNode = -1
                    curLen = sys.maxsize
                    for _node2 in _nodes:
                        # print(_positions[_node], _positions[_node2])
                        dis = self.distance(_positions[_node], _positions[_node2])
                        if _node2 not in usedNode and _node2 not in _neighbors[_node] and dis < curLen: # no duplicate
                            # print(_positions[_node], _positions[_node2], self.distance(_positions[_node], _positions[_node2]))
                            curNode = _node2
                            curLen = dis

                    if curNode >= 0:
                        _neighbors[_node].append(curNode)
                        _neighbors[curNode].append(_node)
                        _edges.append((_node, curNode))
                        usedNode.append(curNode)
                        #print(usedNode)

        # Construct node's neighbor list in Node struct
        for node in self.nodes:
            for neighbor in _neighbors[node.id]:
                node.neighbors.append(self.nodes[neighbor])

        # Construct Link
        linkId = 0
        length = 0
        times = 0
        for _edge in _edges:
            times += 1
            length += self.distance(_positions[_edge[0]], _positions[_edge[1]])
            self.edges.append((self.nodes[_edge[0]], self.nodes[_edge[1]]))
            rand = int(random.random()*5+3) # 5~9
            for _ in range(0, rand):
                link = Link(self, self.nodes[_edge[0]], self.nodes[_edge[1]], False, False, linkId, self.distance(_positions[_edge[0]], _positions[_edge[1]])) 
                self.links.append(link)
                self.nodes[_edge[0]].links.append(link)
                self.nodes[_edge[1]].links.append(link)
                linkId += 1
        
        print('Average Length:', length / times)

    def generate(n, q, a, degree, density, L):
        """
        Generate Topo object

        :return: the topology
        :rtype: `Topo`
        :param n: number of nodes
        :type n: `int`
        :param q: probability of swapping
        :type q: `float`
        :param a: alpha
        :type a: `float`
        :param degree: the least degree 
        :type degree: `int`
        :param density: for nexwork param
        :type density: `float`
        :param L: for nexwork param
        :type L: `float`
        """
        checker = TopoConnectionChecker()
        while True:
            G = nx.waxman_graph(n, beta=0.85, alpha=0.02, domain=(0, 0, 1, 2))
            topo = Topo(G, q, a, degree, density, L)
            checker.setTopo(topo)
            if checker.checkConnected():
                break
            else:
                print("Topo is not connected", file = sys.stderr)

        # Generator Social network
        generator = socialGenerator()
        generator.setTopo(topo)
        generator.genSocialRelationship()

        return topo

    def trans(self, p):
        return self.L*p / (self.L*p - p + 1)

    def weight(self, p):
        return -1 * math.log(self.trans(p)) 

    def distance(self, pos1, pos2): 
        """
        Calculate the distance between two nodes

        :return: the distance between two nodes
        :rtype: `float`
        :param pos1: position of node 1
        :type pos1: `tuple`
        :param pos2: position of node 2
        :type pos2: `tuple`
        """
        d = 0
        for a, b in zip(pos1, pos2):
            d += (a-b) ** 2
        return d ** 0.5

    def widthPhase2(self, path):
        curMinWidth = min(path[0].remainingQubits, path[-1].remainingQubits)

        # Check min qubits in path
        for i in range(1, len(path) - 1):
            if path[i].remainingQubits / 2 < curMinWidth:
                curMinWidth = path[i].remainingQubits // 2

        # Check min links in path
        for i in range(0, len(path) - 1):
            n1 = path[i]
            n2 = path[i+1]
            t = 0
            for link in n1.links:
                if link.contains(n2) and not link.assigned:
                    t += 1

            if t < curMinWidth:
                curMinWidth = t

        return curMinWidth
        
    def shortestPath(self, src, dst, Type, edges=None):
        """
        Route the shortest path for SD by Dijkstra Algorithm

        :return: the shortest path for SD
        :rtype: `list`
        :param src: src
        :type src: `Node`
        :param dst: dst
        :type dst: `Node`
        :param Type: type of link weight
        :type Type: `str`
        :param edges: ???
        :type edges: `list`
        """
        # Construct state metric (weight) table for edges
        fStateMetric = {}   # {edge: fstate}
        fStateMetric.clear()
        if edges != None:
            fStateMetric = {edge : self.distance(edge[0].loc, edge[1].loc) for edge in edges} 
        elif Type == 'Hop' and edges == None:   # Hop
            fStateMetric = {edge : 1 for edge in self.edges}
        elif Type == "New" and edges == None:   # New
            fStateMetric = {edge : self.weight(math.exp(-self.alpha * self.distance(edge[0].loc, edge[1].loc))) for edge in self.edges}
        elif Type == "Test" and edges == None:  # Test
            fStateMetric = {edge : -(math.log(self.q)) + self.weight(math.exp(-self.alpha * self.distance(edge[0].loc, edge[1].loc))) for edge in self.edges}
        else:   # Distance
            fStateMetric = {edge : self.distance(edge[0].loc, edge[1].loc) for edge in self.edges}

        # Construct neightor & weight table for nodes
        neighborsOf = {node: {} for node in self.nodes}    # {Node: {Node: weight, ...}, ...}
        if edges == None:
            for edge in self.edges:
                n1, n2 = edge
                neighborsOf[n1][n2] = fStateMetric[edge]
                neighborsOf[n2][n1] = fStateMetric[edge]
        else:
            for edge in edges:
                n1, n2 = edge
                neighborsOf[n1][n2] = fStateMetric[edge]
                neighborsOf[n2][n1] = fStateMetric[edge]

        D = {node.id : sys.float_info.max for node in self.nodes}   # {int: [int, int, ...], ...}
        q = []  # [(weight, curr, prev)]

        D[src.id] = 0.0
        prevFromSrc = {}   # {cur: prev}

        q.append((D[src.id], src, self.sentinel))
        q = sorted(q, key=lambda q: q[0])

        # Dijkstra 
        while len(q) != 0:
            q = sorted(q, key=lambda q: q[0])
            contain = q.pop(0)
            w, prev = contain[1], contain[2]
            if w in prevFromSrc.keys():
                continue
            prevFromSrc[w] = prev

            # If find the dst return D & path 
            if w == dst:
                path = []
                cur = dst
                while cur != self.sentinel:
                    path.insert(0, cur)
                    cur = prevFromSrc[cur]          
                return (D[dst.id], path)
            
            # Update neighbors of w  
            for neighbor in neighborsOf[w]:
                weight = neighborsOf[w][neighbor]
                newDist = D[w.id] + weight
                oldDist = D[neighbor.id]

                if oldDist > newDist:
                    D[neighbor.id] = newDist
                    q.append((D[neighbor.id], neighbor, w))
        
        return (sys.float_info.max, [])
        
    def hopsAway(self, src, dst, Type):
        path = self.shortestPath(src, dst, Type)
        return len(path[1]) - 1

    def genShortestPathTable(self, Type):
        # n * n
        print('Generate Path Table, Type:', Type)
        for n1 in self.nodes:
            for n2 in self.nodes:
                if n1 != n2:   
                    weight, path = self.shortestPath(n1, n2, Type)       
                    p = self.Pr(path)
                    self.shortestPathTable[(n1, n2)] = (path, weight, p)
                    # print([x.id for x in path])
                    if len(path) == 0:
                        quit()
                else:
                    self.shortestPathTable[(n1, n2)] = ([], 0, 0)

    def genExpectTable(self):
        # n * n * k
        print('Generate Expect Table ...')
        for n1 in self.nodes:
            for k in self.socialRelationship[n1]:
                for n2 in self.nodes:
                    if n1 != n2 and k != n2:
                        self.expectTable[((n1, k), (k, n2))] = self.expectedRound(self.shortestPathTable[(n1, k)][2], self.shortestPathTable[(k, n2)][2])

    def expectedRound(self, p1, p2):
        """
        Law of large numbers

        :return: average number of rounds
        :rtype: `float`
        :param p1: probability 1
        :type p1: `float`
        :param p2: probability 2
        :type p2: `float`
        """
        times = 145 
        roundSum = 0

        for _ in range(times):
            roundSum += self.Round(p1, p2)

        return roundSum / times
    
    def Round(self, p1, p2):
        """
        Run the samples

        :return: number of rounds
        :rtype: `int`
        :param p1: probability 1
        :type p1: `float`
        :param p2: probability 2
        :type p2: `float`
        """
        # State with 0, 1, 2
        state = 0 
        maxRound = 1000
        currentRound = 0
        currentMaintain = 0

        if p1 < (1 / maxRound) or p2 < (1 / maxRound):
            return maxRound

        while state != 2:
            if currentRound >= maxRound:
                break
            currentRound += 1
            if state == 0:
                if random.random() <= p1:
                    state = 1
            elif state == 1:
                currentMaintain += 1
                if currentMaintain > self.L:
                    state = 0
                    currentMaintain = 0
                elif random.random() <= p2:
                    state = 2

        return currentRound

    def Pr(self, path):
        P = 1
        for i in range(len(path) - 1):
            n1 = path[i]
            n2 = path[i+1]
            d = self.distance(n1.loc, n2.loc)
            p = self.trans(math.exp(-self.alpha * d))
            P *= p
   
        return P * (self.q**(len(path) - 2))

    def e(self, path, width, oldP):
        """
        Calculate e for QCAST Algorithm

        :return: e
        :rtype: `float`
        :param path: the path
        :type path: `list`
        :param width: path width
        :type width: `int`
        :param oldP: old numbers
        :type oldP: `list`
        """
        s = len(path) - 1
        P = [0.0 for _ in range(0,width+1)]
        p = [0 for _ in range(0, s+1)]  # Entanglement percentage
        
        for i in range(0, s):
            l = self.distance(path[i].loc, path[i+1].loc)
            p[i+1] = math.exp(-self.alpha * l)

        start = s
        if sum(oldP) == 0:
            for m in range(0, width+1):
                oldP[m] = math.comb(width, m) * math.pow(p[1], m) * math.pow(1-p[1], width-m)
                start = 2
        
        for k in range(start, s+1):
            for i in range(0, width+1):
                exactlyM = math.comb(width, i) *  math.pow(p[k], i) * math.pow(1-p[k], width-i)
                atLeastM = exactlyM

                for j in range(i+1, width+1):
                    atLeastM += (math.comb(width, j) * math.pow(p[k], j) * math.pow(1-p[k], width-j))

                acc = 0
                for j in range(i+1, width+1):
                    acc += oldP[j]
                
                P[i] = oldP[i] * atLeastM + exactlyM * acc
            
            for i in range(0, width+1):
                oldP[i] = P[i]
        
        acc = 0
        for m in range(1, width+1):
            acc += m * oldP[m]
        
        return acc * math.pow(self.q, s-1)
    
    def getEstablishedEntanglements(self, n1, n2):
        stack = []
        stack.append((None, n1)) 
        result = []

        while stack:
            (incoming, current) = stack.pop()
            # if incoming != None:
            #     print(incoming.n1.id, incoming.n2.id, current.id)

            if current == n2:
                path = []
                path.append(n2)
                inc = incoming
                while inc.n1 != n1 and inc.n2 != n1:
                    if inc.n1 == path[-1]:
                        prev = inc.n2
                    elif inc.n2 == path[-1]:
                        prev = inc.n1
                        
                    #inc = prev.internalLinks.first { it.contains(inc) }.otherThan(inc)
                    for internalLinks in prev.internalLinks:
                        # if inc in internalLinks:
                        #     for links in internalLinks:
                        #         if inc != links:
                        #             inc = links
                        #             break
                        #         else:
                        #             continue
                        #     break
                        # else:
                        #     continue
                        (l1, l2) = internalLinks
                        if l1 == inc:
                            inc = l2
                            break
                        elif l2 == inc:
                            inc = l1
                            break

                    path.append(prev)

                path.append(n1)
                path.reverse()
                result.append(path)
                continue

            outgoingLinks = []
            if incoming is None:
                for links in current.links:
                    if links.entangled and not links.swappedAt(current):
                        outgoingLinks.append(links)
            else:
                for internalLinks in current.internalLinks:
                    # for links in internalLinks:
                    #     if incoming != links:
                    #         outgoingLinks.append(links)
                    (l1, l2) = internalLinks
                    if l1 == incoming:
                        outgoingLinks.append(l2)
                    elif l2 == incoming:
                        outgoingLinks.append(l1)
                    
            
            for l in outgoingLinks:
                if l.n1 == current:
                    stack.append((l, l.n2))
                elif l.n2 == current:
                    stack.append((l, l.n1))

        return result

    def clearAllEntanglements(self):
        for link in self.links:
            link.clearEntanglement()

    def updateLinks(self):
        for link in self.links:
            l = self.distance(link.n1.loc, link.n2.loc)
            link.alpha = self.alpha
            link.p = math.exp(-self.alpha * l)
    
    def updateNodes(self):
        for node in self.nodes:
            node.q = self.q

    def setAlpha(self, alpha):
        self.alpha = alpha
        self.updateLinks()
        self.updateNodes()

    def setQ(self, q):
        self.q = q
        self.updateLinks()
        self.updateNodes()

    def setL(self, L):
        self.L = L

    def setDensity(self, density):
        self.density = density
        generator = socialGenerator()
        generator.setTopo(self)
        generator.genSocialRelationship()
