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

class FER_OPP(AlgorithmBase):

    def __init__(self, topo, allowRecoveryPaths=False, k=1):
        super().__init__(topo)
        self.name = "FER_OPP"
        self.majorPaths = []            # [PickedPath, ...]
        self.allowRecoveryPaths = allowRecoveryPaths
        self.requests = []
        self.bindLinks = {}
        self.state = {}
        self.req2Intermediate = {}
        self.reqBroken = {}
        self.k = k

        self.totalTime = 0
        self.totalUsedQubits = 0
        self.totalNumOfReq = 0
        self.totalNumOfBrokenReq = 0

    def prepare(self):
        self.totalTime = 0
        self.requests.clear()

    # P2
    def p2(self):

        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            self.requests.append((src, dst, self.timeSlot))
            self.bindLinks[(src, dst, self.timeSlot)] = {}
            self.state[(src, dst, self.timeSlot)] = 0
            self.reqBroken[(src, dst, self.timeSlot)] = False

        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1

        while True: 
            candidates = self.calCandidates(self.requests) # candidates -> [PickedPath, ...]   
            candidates = sorted(candidates, key=lambda x: x.weight)
            if len(candidates) == 0:
                break
            pick = candidates[-1]   # pick -> PickedPath 

            # print('---')
            # for c in candidates:
            #     print('[', self.name, '] Path:', [x.id for x in c.path])
            #     print('[', self.name, '] EXT:', c.weight)
            #     print('[', self.name, '] Width:', c.width)
            
            # print('[', self.name, '] Pick:', [x.id for x in pick.path])
            # print('---')

            if pick.weight > 0.0: 
                self.pickAndAssignPath(pick)
            else:
                break
        
        reqUpdated = {req: 0 for req in self.req2Intermediate}
        finished = []

        # Swapped (1)
        for pathWithWidth in self.majorPaths:
            width = pathWithWidth.width
            path = tuple(pathWithWidth.path)
            time = pathWithWidth.time
            req = (path[0], path[-1], time)
            intermediate = self.req2Intermediate[req]
            self.state[req] = 1 

            if req in finished:
                continue

            for n in range(0, len(path)-1):
                for w in range(0, width): 
                    if not self.bindLinks[req][path][w][n].entangled and not self.bindLinks[req][path][w][n].swapped():
                        for ww in range(w+1, width):
                            if self.bindLinks[req][path][ww][n].entangled and not self.bindLinks[req][path][ww][n].swapped():
                                self.bindLinks[req][path][w][n], self.bindLinks[req][path][ww][n] = self.bindLinks[req][path][ww][n], self.bindLinks[req][path][w][n] 

            for w in range(0, width): 
                if intermediate not in path or intermediate == req[1] or reqUpdated[req] == 1:
                    continue 

                links = self.bindLinks[req][path][w]
                _p = path[path.index(intermediate):len(path)]
                _links = links[path.index(intermediate):len(path)-1]
                arrive = self.swapped(_p, _links)

                if intermediate == arrive:
                    continue

                if intermediate != req[0]:  
                    intermediate.remainingQubits += 1 

                if arrive == req[1]:
                    finished.append(req)

                if arrive not in self.topo.socialRelationship[req[0]] and arrive != req[1]:
                    self.reqBroken[req] = True 

                self.req2Intermediate[req] = arrive
                reqUpdated[req] = 1
      
        removedPickedPath = []

        # Calculate the finished number of requests and delete 
        for req in finished:
            if req in self.requests:
                print('[', self.name, '] Finished Requests:', req[0].id, req[1].id, req[2])
                self.totalTime += self.timeSlot - req[2]
                if self.reqBroken[req]:
                    self.totalNumOfBrokenReq += 1
                self.requests.remove(req)

        # Delete used links and clear entanglement for finished SD-pairs 
        for pathWithWidth in self.majorPaths:
            width = pathWithWidth.width
            path = tuple(pathWithWidth.path)
            time = pathWithWidth.time
            req = (path[0], path[-1], time)

            if req in finished: 
                if path in self.bindLinks[req]:
                    for w in range(0, width): 
                        for link in self.bindLinks[req][path][w]:
                            link.clearEntanglement()
                    removedPickedPath.append(pathWithWidth)

        for req in finished: 
            if req in self.bindLinks:          
                self.bindLinks.pop(req)

        for pathWithWidth in removedPickedPath:
            self.majorPaths.remove(pathWithWidth)

        print('[', self.name, '] P2 End')

    # Calculate the candidate path for each requests 
    def calCandidates(self, requests: list): # pairs -> [(Node, Node), ...]
        candidates = [] 
        for req in requests:
            candidate = []
            (src, dst, time) = req
            maxM = min(src.remainingQubits, dst.remainingQubits)
            if maxM == 0:   # not enough qubit
                continue
            
            if self.state[req] != 0:   # If the req has binding links, continue
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

        self.majorPaths.append(pick)
        path = tuple(pick.path)        
        width = pick.width
        time = pick.time
        req = (path[0], path[-1], time)
        self.bindLinks[req][path] = []
        self.req2Intermediate[req] = path[0]

        # Assign Qubits for links in path 
        for w in range(0, width):
            self.bindLinks[req][path].append([])
            for s in range(0, len(path) - 1):
                n1 = path[s]
                n2 = path[s+1]
                for link in n1.links:
                    if link.contains(n2) and (not link.assigned):
                        self.totalUsedQubits += 2
                        link.assignQubits()
                        self.bindLinks[req][path][w].append(link)
                        break    
 
    def swapped(self, path, links):
        succNumOfLinks = 0

        # Calculate the continuous succeed number of links whether larger than k
        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            if prevLink.entangled:
                succNumOfLinks += 1
            else:
                break

            if n == len(path)-2:
                if nextLink.entangled:
                    succNumOfLinks = self.k

        # If path just 2 length 
        if len(path) == 2:  
            if links[0].entangled:
                return path[1]
            else:
                return path[0]

        if succNumOfLinks < self.k:
            return path[0]  # Forward 0 hop
        
        if self.k == 1:
            # if path[1].remainingQubits < 1:
            #     return path[0]  # Forward 0 hop
            # else:
            #     path[1].remainingQubits -= 1
            #     return path[1]  # Forward 1 hop

            # Can consume extra memory
            path[1].remainingQubits -= 1
            return path[1]  # Forward 1 hop

        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            if prevLink.entangled and not prevLink.swappedAt(path[n]) and nextLink.entangled and not nextLink.swappedAt(path[n]):
                if not path[n].attemptSwapping(prevLink, nextLink): # Swap failed 
                    for link in links:
                        if link.swapped():
                            link.clearPhase4Swap() 
                    return path[0]  # Forward 0 hop
                else:                                               # Swap succeed 
                    if n+1 >= self.k or n == len(path)-2:   # satisfy k   
                        if path[n+1] == path[-1]:   # next terminal
                            return path[-1]

                        if path[n+1].remainingQubits < 1:   # has enough memory
                            return path[0]  # Forward 0 hop
                        else:
                            path[n+1].remainingQubits -= 1
                            return path[n+1]  # Forward n+1 hop
                    else:   
                        return path[0]      # Forward 0 hop
            elif prevLink.entangled and prevLink.swappedAt(path[n]) and nextLink.entangled and nextLink.swappedAt(path[n]):
                continue

    def p4(self):
        reqUpdated = {req: 0 for req in self.req2Intermediate}
        finished = []

        # Swapped (2)
        for pathWithWidth in self.majorPaths:
            width = pathWithWidth.width
            path = tuple(pathWithWidth.path)
            time = pathWithWidth.time
            req = (path[0], path[-1], time)
            intermediate = self.req2Intermediate[req]
            self.state[req] = 1 

            if req in finished:
                continue

            for n in range(0, len(path)-1):
                for w in range(0, width): 
                    if not self.bindLinks[req][path][w][n].entangled and not self.bindLinks[req][path][w][n].swapped():
                        for ww in range(w+1, width):
                            if self.bindLinks[req][path][ww][n].entangled and not self.bindLinks[req][path][ww][n].swapped():
                                self.bindLinks[req][path][w][n], self.bindLinks[req][path][ww][n] = self.bindLinks[req][path][ww][n], self.bindLinks[req][path][w][n] 

            for w in range(0, width):
                if intermediate not in path or intermediate == req[1] or reqUpdated[req] == 1:
                    continue 

                links = self.bindLinks[req][path][w]
                _p = path[path.index(intermediate):len(path)]
                _links = links[path.index(intermediate):len(path)-1]
                arrive = self.swapped(_p, _links)

                if intermediate == arrive:
                    continue

                if intermediate != req[0]:  
                    intermediate.remainingQubits += 1 

                if arrive == req[1]:
                    finished.append(req)
                
                if arrive not in self.topo.socialRelationship[req[0]] and arrive != req[1]:
                    self.reqBroken[req] = True 

                self.req2Intermediate[req] = arrive
                reqUpdated[req] = 1
      
        # Calculate the idle time for all requests
        for req in self.requests:
            if self.state[req] == 0: 
                self.result.idleTime += 1

        removedPickedPath = []

        # Calculate the finished number of requests and delete 
        for req in finished:
            if req in self.requests:
                print('[', self.name, '] Finished Requests:', req[0].id, req[1].id, req[2])
                self.totalTime += self.timeSlot - req[2]
                if self.reqBroken[req]:
                    self.totalNumOfBrokenReq += 1
                self.requests.remove(req)

        # Delete used links and clear entanglement for finished SD-pairs 
        for pathWithWidth in self.majorPaths:
            width = pathWithWidth.width
            path = tuple(pathWithWidth.path)
            time = pathWithWidth.time
            req = (path[0], path[-1], time)

            if req in finished: 
                if path in self.bindLinks[req]:
                    for w in range(0, width): 
                        for link in self.bindLinks[req][path][w]:
                            link.clearEntanglement()
                    removedPickedPath.append(pathWithWidth)

        for req in finished: 
            if req in self.bindLinks:          
                self.bindLinks.pop(req)

        for pathWithWidth in removedPickedPath:
            self.majorPaths.remove(pathWithWidth)
       
        # Update links' lifetime       
        for pathWithWidth in self.majorPaths:
            width = pathWithWidth.width
            path = tuple(pathWithWidth.path)
            time = pathWithWidth.time
            req = (path[0], path[-1], time)
  
            for w in range(0, width): 
                links = self.bindLinks[req][path][w]
                for link in links:
                    if link.entangled == True:
                        link.lifetime += 1
                        if link.lifetime > self.topo.L:
                            if link.swapped():
                                for link2 in links:
                                    if link2.swapped():
                                        link2.clearPhase4Swap()
                            else:
                                link.entangled == False
                                link.lifetime = 0

        #                       #                
        #   RECORD EXPERIMENT   #
        #                       #

        remainTime = 0
        for remainReq in self.requests:
            print('[', self.name, '] Remain Requests:', remainReq[0].id, remainReq[1].id, remainReq[2])
            # self.result.unfinishedRequest += 1
            remainTime += self.timeSlot - remainReq[2]

        # self.topo.clearAllEntanglements()
        self.result.remainRequestPerRound.append(len(self.requests)/self.totalNumOfReq)   
        self.result.waitingTime = (self.totalTime + remainTime) / self.totalNumOfReq + 1
        self.result.usedQubits = self.totalUsedQubits / self.totalNumOfReq

        print('[', self.name, '] Waiting Time:', self.result.waitingTime)
        print('[', self.name, '] Idle Time:', self.result.idleTime)
        print('[', self.name, '] Broken Requests:', self.totalNumOfBrokenReq)
        print('[', self.name, '] P4 End')

        return self.result

if __name__ == '__main__':

    topo = Topo.generate(100, 0.9, 5, 0.001, 6)
    # f = open('logfile.txt', 'w')
    
    a1 = FER_OPP(topo)
    # a2 = MyAlgorithm(topo)
    # a3 = FER(topo)
    # a4 = OnlineAlgorithm(topo)
 
    samplesPerTime = 6
    ttime = 100
    rtime = 5
    requests = {i : [] for i in range(ttime)}
    memory = {}

    # Record nodes' remainingqubits
    for node in topo.nodes:
        memory[node.id] = node.remainingQubits

    # Generate requests
    for i in range(ttime):
        if i < rtime:
            a = sample(topo.nodes, samplesPerTime)
            for n in range(0,samplesPerTime,2):
                requests[i].append((a[n], a[n+1]))
    
    for i in range(ttime):
        t1 = a1.work(requests[i], i)

    for node in topo.nodes:
        if memory[node.id] != node.remainingQubits:
            print(node.id, memory[node.id]-node.remainingQubits)