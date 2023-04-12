import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase, Request, Path
from AlgorithmBase import PickedPath
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from random import sample
import copy

class QCAST(AlgorithmBase):
    def __init__(self, topo):
        super().__init__(topo)
        self.name = "QCAST"
        self.requests = []

        self.totalTime = 0
        self.totalUsedQubits = 0
        self.totalNumOfReq = 0
    
    def prepare(self):
        self.totalTime = 0
        self.requests.clear()

    # P2
    def p2(self):
        # Pre-prepare and initialize
        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            request = Request(src, dst, self.timeSlot, src)
            self.requests.append(request)

        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1

        self.canEntangled = False

        if self.timeSlot % self.topo.L == 0:
            self.canEntangled = True
            while True: 
                candidates = self.calCandidates(self.requests) # candidates -> [PickedPath, ...]   
                candidates = sorted(candidates, key=lambda x: x.weight)
                if len(candidates) == 0:
                    break
                pick = candidates[-1]   # pick -> PickedPath 

                if pick.weight > 0.0: 
                    self.pickAndAssignPath(pick)
                else:
                    break
    
        print('[', self.name, '] P2 End')

    # Calculate the candidate path for each requests 
    def calCandidates(self, requests: list): # pairs -> [(Node, Node), ...]
        candidates = [] 
        for req in requests:
            candidate = []
            src, dst, time = req.src, req.dst, req.time
            maxM = min(src.remainingQubits, dst.remainingQubits)
            if maxM == 0:   # not enough qubit
                continue
            
            if req.state != 0:   # If the req has binding links, continue
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
                    contain = q.pop(-1) # Pop the node with the highest E
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

                # IF this SD-pair find a path, go on solving the next SD-pair 
                if len(candidate) > 0:
                    candidates += candidate
                    break
            # for w end      
        # for pairs end
        return candidates

    def pickAndAssignPath(self, pick: PickedPath, majorPath: PickedPath = None):
     
        width = pick.width
        time = pick.time
        request = None
        for req in self.requests:
            if req.src == pick.path[0] and req.dst == pick.path[-1] and req.time == time:
                request = req
                break

        # Assign Qubits for links in path 
        for _ in range(0, width):
            path = Path()
            path.path = pick.path
            p = path.path
            for s in range(0, len(p) - 1):
                n1 = p[s]
                n2 = p[s+1]
                for link in n1.links:
                    if link.contains(n2) and (not link.assigned):
                        self.totalUsedQubits += 2
                        link.assignQubits()
                        path.links.append(link)
                        break  
                                       
            request.paths.append(path)
 
    def swapped(self, path, links):
        # Calculate the continuous all succeed links 
        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            if not prevLink.entangled:
                return path[0]

        if len(path) == 2:  # If path just 2 length 
            if not links[0].entangled:
                return path[0]
            else:
                return path[1]
              
        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            if prevLink.entangled and not prevLink.swappedAt(path[n]) and nextLink.entangled and not nextLink.swappedAt(path[n]):
                if not path[n].attemptSwapping(prevLink, nextLink): # Swap failed than clear the link state
                    for link in links:
                        if link.swapped():
                            link.clearPhase4Swap() 
                    return path[0]  # Forward 0 hop
                else:       
                    if n == len(path)-2:    # Swap succeed and the next hop is terminal than forward to it
                        return path[-1]
                    else:   
                        return path[0]  # Forward 0 hop
            elif prevLink.entangled and prevLink.swappedAt(path[n]) and nextLink.entangled and nextLink.swappedAt(path[n]):
                continue
    
    def trySwapped(self):
        # Swapped 
        finished = []
        for req in self.requests:
            paths = req.paths
            if len(paths) != 0:
                req.state = 1
            
            if req.state == 0:
                continue

            for path in paths:
                p = path.path
                links = path.links
                arrive = self.swapped(p, links)

                if req.dst == arrive:
                    finished.append(req)
                
                    if not req.CImark:
                        req.CImark = True
                        # Calculate the rate of intermediate
                        for s in range(1, len(p) - 2):
                            self.totalNumOfNormalNodeOnPath += 1
                            if p[s] in self.topo.socialRelationship[req.src]:
                                self.totalNumOfIntermediate += 1

        # Delete the finished request
        for req in finished:
            if req in self.requests:
                print('[', self.name, '] Finished Requests:', req.src.id, req.dst.id, req.time)
                self.totalTime += self.timeSlot - req.time
                if req.broken:
                    self.totalNumOfBrokenReq += 1
                self.totalNumOfFinishedReq += 1
                self.totalNumOfSecureReq = self.totalNumOfFinishedReq - self.totalNumOfBrokenReq
                self.requests.remove(req)

            paths = req.paths
            # Delete used links and clear entanglement for finished SD-pairs 
            for path in paths:
                links = path.links
                for link in links:
                    link.clearEntanglement()

    def p4(self):

        # Update links' lifetime       
        for req in self.requests:
            paths = req.paths
            for path in paths: 
                links = path.links
                for link in links:
                    if link.entangled == True:
                        link.lifetime += 1
                    # time out
                    if link.lifetime > self.topo.L or self.timeSlot % self.topo.L == self.topo.L - 1:
                        # link is swapped
                        if link.swapped():
                            for link2 in links:
                                if link2.swapped():
                                    link2.clearPhase4Swap()
                        link.entangled = False
                        link.lifetime = 0

        """             
            Recode experiment   
        """  
        # Calculate the idle time for all requests
        for req in self.requests:
            if req.state == 0:
                self.result.idleTime += 1

        # Calculate the remaining time for unfinished SD-pairs
        remainTime = 0
        print('[', self.name, '] Remain Requests:', len(self.requests))
        for remainReq in self.requests:
            remainTime += self.timeSlot - remainReq.time

        # self.topo.clearAllEntanglements()
        self.result.remainRequestPerRound.append(len(self.requests)/self.totalNumOfReq)   
        self.result.waitingTime = (self.totalTime + remainTime) / self.totalNumOfReq + 1
        self.result.usedQubits = self.totalUsedQubits / self.totalNumOfReq

        print('[', self.name, '] Waiting Time:', self.result.waitingTime)
        print('[', self.name, '] Idle Time:', self.result.idleTime)
        print('[', self.name, '] P4 End')

        return self.result

if __name__ == '__main__':
    topo = Topo.generate(30, 0.9, 0.002, 6, 0.5, 15, 1)

