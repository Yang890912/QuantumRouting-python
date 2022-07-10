from dataclasses import dataclass
import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase
from AlgorithmBase import PickedPath
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from random import sample
import copy

@dataclass
class RecoveryPath:
    path: list
    width: int
    taken: int 
    available: int

class FER(AlgorithmBase):

    def __init__(self, topo, allowRecoveryPaths = True):
        super().__init__(topo)
        self.pathsSortedDynamically = []
        self.name = "FER"
        self.majorPaths = []            # [PickedPath, ...]
        self.recoveryPaths = {}         # {PickedPath: [PickedPath, ...], ...}
        self.pathToRecoveryPaths = {}   # {PickedPath : [RecoveryPath, ...], ...}
        self.allowRecoveryPaths = allowRecoveryPaths
        self.requests = []
        self.totalTime = 0
        self.totalUsedQubits = 0
        self.totalNumOfReq = 0
    
    def prepare(self):
        self.totalTime = 0
        self.requests.clear()

    # P2
    def p2(self):
        self.majorPaths.clear()
        self.recoveryPaths.clear()
        self.pathToRecoveryPaths.clear()

        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            self.requests.append((src, dst, self.timeSlot))
        
        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1

        while True: 
            candidates = self.calCandidates(self.requests) # candidates -> [PickedPath, ...]   
            candidates = sorted(candidates, key=lambda x: x.weight)
            if len(candidates) == 0:
                break
            pick = candidates[-1]   # pick -> PickedPath 

            print('-----')
            for c in candidates:
                print('[', self.name, '] Path:', [x.id for x in c.path])
                print('[', self.name, '] EXT:', c.weight)
                print('[', self.name, '] width:', c.width)
            
            print('[', self.name, '] pick: ', [x.id for x in pick.path])
            print('-----')

            if pick.weight > 0.0: 
                self.pickAndAssignPath(pick)
            else:
                break
    
        for req in self.requests:
            pick = False
            for pathWithWidth in self.majorPaths:
                p = pathWithWidth.path
                if (p[0], p[-1], pathWithWidth.time) == req:
                    pick = True
                    break
                    
            if not pick:
                self.result.idleTime += 1
         
    # 對每個SD-pair找出候選路徑，目前不確定只會找一條還是可以多條
    def calCandidates(self, requests: list): # pairs -> [(Node, Node), ...]
        candidates = [] 
        for req in requests:

            candidate = []
            (src, dst, time) = req
            maxM = min(src.remainingQubits, dst.remainingQubits)
            if maxM == 0:   # not enough qubit
                continue

            for w in range(maxM, 0, -1): # w = maxM, maxM-1, maxM-2, ..., 1
                failNodes = []

                # collect failnodes (they dont have enough Qubits for SDpair in width w)
                for node in self.topo.nodes:
                    if node.remainingQubits < 2 * w and node != src and node != dst:
                        failNodes.append(node)

                edges = {}  # edges -> {(Node, Node): [Link, ...], ...}

                # collect edges with links 
                for link in self.topo.links:
                    # if link.n2.id < link.n1.id:
                    #     link.n1, link.n2 = link.n2, link.n1
                    if not link.assigned and link.n1 not in failNodes and link.n2 not in failNodes:
                        if not edges.__contains__((link.n1, link.n2)):
                            edges[(link.n1, link.n2)] = []
                        edges[(link.n1, link.n2)].append(link)

                neighborsOf = {node: [] for node in self.topo.nodes} # neighborsOf -> {Node: [Node, ...], ...}

                # filter available links satisfy width w
                for edge in edges:
                    links = edges[edge]
                    if len(links) >= w:
                        neighborsOf[edge[0]].append(edge[1])
                        neighborsOf[edge[1]].append(edge[0])

                                             
                if (len(neighborsOf[src]) == 0 or len(neighborsOf[dst]) == 0):
                    continue

                prevFromSrc = {}   # prevFromSrc -> {cur: prev}

                def getPathFromSrc(n): 
                    path = []
                    cur = n
                    while (cur != self.topo.sentinel): 
                        path.insert(0, cur)
                        cur = prevFromSrc[cur]
                    return path
                
                E = {node.id : [-sys.float_info.max, [0.0 for _ in range(0,w+1)]] for node in self.topo.nodes}  # E -> {Node id: [Int, [double, ...]], ...}
                q = []  # q -> [(E, Node, Node), ...]

                E[src.id] = [sys.float_info.max, [0.0 for _ in range(0,w+1)]]
                q.append((E[src.id][0], src, self.topo.sentinel))
                q = sorted(q, key=lambda q: q[0])

                # Dijkstra by EXT
                while len(q) != 0:
                    contain = q.pop(-1) # pop the node with the highest E
                    u, prev = contain[1], contain[2]
                    if u in prevFromSrc.keys():
                        continue
                    prevFromSrc[u] = prev

                    # If find the dst add path to candidates
                    if u == dst:        
                        candidate.append(PickedPath(E[dst.id][0], w, getPathFromSrc(dst), time))
                        break
                    
                    # Update neighbors by EXT
                    for neighbor in neighborsOf[u]:
                        tmp = copy.deepcopy(E[u.id][1])
                        p = getPathFromSrc(u)
                        p.append(neighbor)
                        e = self.topo.e(p, w, tmp)
                        newE = [e, tmp]
                        oldE = E[neighbor.id]

                        if oldE[0] < newE[0]:
                            E[neighbor.id] = newE
                            q.append((E[neighbor.id][0], neighbor, u))
                            q = sorted(q, key=lambda q: q[0])
                # Dijkstra end

                # 假如此SD-pair在width w有找到path則換找下一個SD-pair 目前不確定是否為此機制
                if len(candidate) > 0:
                    candidates += candidate
                    break
            # for w end      
        # for pairs end
        return candidates

    def pickAndAssignPath(self, pick: PickedPath, majorPath: PickedPath = None):
        if majorPath != None:
            self.recoveryPaths[majorPath].append(pick)
        else:
            self.majorPaths.append(pick)
            self.recoveryPaths[pick] = list()
            
        width = pick.width

        for i in range(0, len(pick.path) - 1):
            links = []
            n1, n2 = pick.path[i], pick.path[i+1]

            for link in n1.links:
                if link.contains(n2) and not link.assigned:
                    links.append(link)
            links = sorted(links, key=lambda q: q.id)

            for i in range(0, width):
                self.totalUsedQubits += 2
                links[i].assignQubits()
                # links[i].tryEntanglement() # just display

    def p4(self):
        for pathWithWidth in self.majorPaths:
            width = pathWithWidth.width
            majorPath = pathWithWidth.path
            time = pathWithWidth.time
            oldNumOfPairs = len(self.topo.getEstablishedEntanglements(majorPath[0], majorPath[-1]))

            # for w-width major path, treat it as w different paths
            for w in range(1, width + 1):
                
                acc = majorPath
                nodes = []
                prevLinks = []
                nextLinks = [] 

                # swap (select links)
                for i in range(1, len(acc) - 1):
                    prev = acc[i-1]
                    curr = acc[i]
                    next = acc[i+1]
                    prevLink = []
                    nextLink = []  
                 
                    for link in curr.links:
                        if link.entangled and (link.n1 == prev and not link.s2 or link.n2 == prev and not link.s1):
                            prevLink.append(link)
                            break

                    for link in curr.links:
                        if link.entangled and (link.n1 == next and not link.s2 or link.n2 == next and not link.s1):
                            nextLink.append(link)
                            break

                    if len(prevLink) == 0 or len(nextLink) == 0:
                        break
                    
                    nodes.append(curr)
                    prevLinks.append(prevLink[0])
                    nextLinks.append(nextLink[0])

                # swap 
                if len(nodes) == len(acc) - 2 and len(acc) > 2:
                    for (node, l1, l2) in zip(nodes, prevLinks, nextLinks):                    
                        node.attemptSwapping(l1, l2)

            succ = len(self.topo.getEstablishedEntanglements(acc[0], acc[-1])) - oldNumOfPairs
            
            if succ > 0 or len(acc) == 2:
                find = (acc[0], acc[-1], time)
                if find in self.requests:
                    self.totalTime += self.timeSlot - time
                    self.requests.remove(find)
        # for pathWithWidth end
        
        remainTime = 0
        for req in self.requests:
            # self.result.unfinishedRequest += 1
            remainTime += self.timeSlot - req[2]

        self.topo.clearAllEntanglements()
        self.result.remainRequestPerRound.append(len(self.requests)/self.totalNumOfReq)   
        self.result.waitingTime = (self.totalTime + remainTime) / self.totalNumOfReq + 1
        self.result.usedQubits = self.totalUsedQubits / self.totalNumOfReq

        print('[', self.name, '] waiting time:', self.result.waitingTime)
        print('[', self.name, '] idle time:', self.result.idleTime)

        return self.result

if __name__ == '__main__':

    topo = Topo.generate(100, 0.9, 5, 0.0001, 6)
    s = FER(topo)

    for i in range(0, 200):
        if i < 10:
            a = sample(topo.nodes, 2)
            s.work([(a[0],a[1])], i)
        else:
            s.work([], i)
