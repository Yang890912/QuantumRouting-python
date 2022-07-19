
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

class OnlineAlgorithm(AlgorithmBase):

    def __init__(self, topo, allowRecoveryPaths = False):
        super().__init__(topo)
        self.name = "QCAST"
        self.majorPaths = []            # [PickedPath, ...]
        self.recoveryPaths = {}         # {PickedPath: [PickedPath, ...], ...}
        self.pathToRecoveryPaths = {}   # {PickedPath : [RecoveryPath, ...], ...}
        self.allowRecoveryPaths = allowRecoveryPaths
        self.requests = []
        self.bindLinks = {}
        self.state = {}
        self.linkLifetime = 30

        self.totalTime = 0
        self.totalUsedQubits = 0
        self.totalNumOfReq = 0
    
    def prepare(self):
        self.totalTime = 0
        self.requests.clear()

    # P2
    def p2(self):
        # self.majorPaths.clear()
        self.recoveryPaths.clear()
        self.pathToRecoveryPaths.clear()

        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            self.requests.append((src, dst, self.timeSlot))
            self.bindLinks[(src, dst, self.timeSlot)] = {}
            self.state[(src, dst, self.timeSlot)] = 0

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

        if self.allowRecoveryPaths:
            print('[', self.name, '] P2Extra')
            self.P2Extra()
            print('[', self.name, '] P2Extra End')
        
        for req in self.requests:
            pick = False
            for pathWithWidth in self.majorPaths:
                p = pathWithWidth.path
                if (p[0], p[-1], pathWithWidth.time) == req:
                    pick = True
                    break
                    
            if not pick:
                self.result.idleTime += 1

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

                # IF this SD-pair find a path, go on solving the next SD-pair 
                if len(candidate) > 0:
                    candidates += candidate
                    break
            # for w end      
        # for pairs end
        return candidates

    def pickAndAssignPath(self, pick: PickedPath, majorPath: PickedPath = None):
        # req = tuple()
        # if majorPath != None:
        #     self.recoveryPaths[majorPath].append(pick)
        #     req = (majorPath.path[0], majorPath.path[-1], pick.time)
        # else:
        #     self.majorPaths.append(pick)
        #     self.recoveryPaths[pick] = list()
        #     req = (pick.path[0], pick.path[-1], pick.time)

        self.majorPaths.append(pick)
        path = tuple(pick.path)        
        width = pick.width
        time = pick.time
        req = (path[0], path[-1], time)
        self.bindLinks[req][path] = []

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

    def P2Extra(self):
        for majorPath in self.majorPaths:
            p = majorPath.path

            for l in range(1, self.topo.k + 1):
                for i in range(0, len(p) - l):
                    (src, dst) = (p[i], p[i+l])

                    candidates = self.calCandidates([(src, dst, self.timeSlot)]) # candidates -> [PickedPath, ...]   
                    candidates = sorted(candidates, key=lambda x: x.weight)
                    if len(candidates) == 0:
                        continue
                    pick = candidates[-1]   # pick -> PickedPath

                    if pick.weight > 0.0: 
                        self.pickAndAssignPath(pick, majorPath)

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

            if prevLink.entangled and not prevLink.swappedAt(path[n]) and nextLink.entangled and not prevLink.swappedAt(path[n]):
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
            elif prevLink.entangled and prevLink.swappedAt(path[n]) and nextLink.entangled and prevLink.swappedAt(path[n]):
                continue

    def p4(self):
        finished = []

        for pathWithWidth in self.majorPaths:
            width = pathWithWidth.width
            path = tuple(pathWithWidth.path)
            time = pathWithWidth.time
            req = (path[0], path[-1], time)
            self.state[req] = 1 

            # 
            # If allow extra links end
            #
            if self.allowRecoveryPaths:
                recoveryPaths = self.recoveryPaths[pathWithWidth]   # recoveryPaths -> [pickedPath, ...]
                recoveryPaths = sorted(recoveryPaths, key=lambda x: len(x.path)*10000 + path.index(x.path[0])) # sort recoveryPaths by it recoverypath length and the index of the first node in recoveryPath  

                # Construct pathToRecoveryPaths table
                for recoveryPath in recoveryPaths:
                    w = recoveryPath.width
                    p = recoveryPath.path
                    available = sys.maxsize
                    for i in range(0, len(p) - 1):
                        n1 = p[i]
                        n2 = p[i+1]
                        cnt = 0
                        for link in n1.links:
                            if link.contains(n2) and link.entangled:
                                cnt += 1
                        if cnt < available:
                            available = cnt
                    
                    if not self.pathToRecoveryPaths.__contains__(pathWithWidth):
                        self.pathToRecoveryPaths[pathWithWidth] = []
                    
                    self.pathToRecoveryPaths[pathWithWidth].append(RecoveryPath(p, w, 0, available))
                # for end 

                rpToWidth = {tuple(recoveryPath.path): recoveryPath.width for recoveryPath in recoveryPaths}  # rpToWidth -> {tuple: int, ...}
  
            # for w-width major path, treat it as w different paths, and repair separately
            for w in range(0, width):
                brokenEdges = list()    # [(int, int), ...]

                # 
                # If allow extra links end
                #
                if self.allowRecoveryPaths:
                    brokenEdges = list()    # [(int, int), ...]
                    # find all broken edges on the major path
                    # 尋找在 majorPath 裡斷掉的 link，其中一條斷掉就要記錄。
                    for i in range(0, len(path) - 1):
                        i1 = i
                        i2 = i+1
                        n1 = path[i1]
                        n2 = path[i2]
                        broken = True
                        for link in n1.links:
                            if link.contains(n2) and link.assigned and link.notSwapped() and link.entangled:
                                broken = False
                                break
                        if broken:
                            brokenEdges.append((i1, i2))

                            # if link.contains(n2) and link.assigned and link.notSwapped() and not link.entangled:
                            #     brokenEdges.append((i1, i2))

                    edgeToRps = {brokenEdge: [] for brokenEdge in brokenEdges}   # {tuple : [tuple, ...], ...}
                    rpToEdges = {tuple(recoveryPath.path): [] for recoveryPath in recoveryPaths}    # {tuple : [tuple, ...], ...}

                    # Construct edgeToRps & rpToEdges
                    # 掃描所有可以用的 recoveryPath，看它斷在 majorPath 的哪裡，並標記。
                    for recoveryPath in recoveryPaths:
                        rp = recoveryPath.path
                        s1, s2 = path.index(rp[0]), path.index(rp[-1])

                        for j in range(s1, s2):
                            if (j, j+1) in brokenEdges:
                                edgeToRps[(j, j+1)].append(tuple(rp))
                                rpToEdges[tuple(rp)].append((j, j+1))
                            # elif (j+1, j) in brokenEdges:
                            #     edgeToRps[(j+1, j)].append(tuple(rp))
                            #     rpToEdges[tuple(rp)].append((j+1, j))

                    realRepairedEdges = set()
                    realPickedRps= set()

                    # try to cover the broken edges
                    # 掃描每個斷掉的 edge
                    for brokenEdge in brokenEdges:
                        # if the broken edge is repaired, go to repair the next broken edge
                        if brokenEdge in realRepairedEdges: 
                            continue
                        repaired = False
                        next = 0    # last repaired location
                        rps = edgeToRps[brokenEdge] # the rps cover the edge
                        
                        # filter the avaliable rp in rps for brokenEdge
                        for rp in rps:
                            if rpToWidth[tuple(rp)] <= 0 or tuple(rp) in realPickedRps:
                                rps.remove(rp)

                        # sort rps by the start id in majorPath
                        rps = sorted(rps, key=lambda x: path.index(x[0]) * 10000 + path.index(x[-1]))

                        for rp in rps:
                            if path.index(rp[0]) < next:
                                continue 

                            next = path.index(rp[-1])
                            pickedRps = realPickedRps
                            repairedEdges = realRepairedEdges
                            otherCoveredEdges = set(rpToEdges[tuple(rp)]) - {brokenEdge}
                            covered = False

                            for edge in otherCoveredEdges: #delete covered rps, or abort
                                prevRp = set(tuple(edgeToRps[edge])) & pickedRps    # 這個edge 所覆蓋到的rp 假如已經有被選過 表示她被修理過了 表示目前這個rp要修的edge蓋到以前的rp
                                
                                if prevRp == set():
                                    repairedEdges.add(edge)
                                else: 
                                    covered = True
                                    break  # the rps overlap. taking time to search recursively. just abort
                            
                            if covered:
                                continue

                            repaired = True      
                            repairedEdges.add(brokenEdge) 
                            pickedRps.add(tuple(rp))

                            for rp in realPickedRps - pickedRps:
                                rpToWidth[tuple(rp)] += 1
                            for rp in pickedRps - realPickedRps:
                                rpToWidth[tuple(rp)] -= 1
                            
                            realPickedRps = pickedRps
                            realRepairedEdges = repairedEdges
                        # for rp end

                        if not repaired:   # this major path cannot be repaired
                            break
                    # for brokenEdge end

                    for rp in realPickedRps:
                        for recoveryPath in self.pathToRecoveryPaths[pathWithWidth]:
                            if recoveryPath.path == rp:
                                recoveryPath.taken += 1
                                break
                        
                        toOrigin = set()
                        toAdd = set()
                        toDelete = set()

                        for i in range(0, len(acc) - 1):
                            toOrigin.add((acc[i], acc[i+1]))
                        for i in range(0, len(rp) - 1):
                            toAdd.add((rp[i], rp[i+1]))

                        startDelete = 0
                        endDelete = len(acc) - 1

                        for i in range(0, len(acc)):
                            startDelete = i
                            if acc[i] == rp[0]:
                                break
                        for i in range(len(acc) - 1, -1, -1):
                            endDelete = i
                            if acc[i] == rp[-1]:
                                break   
                        for i in range(startDelete, endDelete):
                            toDelete.add((acc[i], acc[i+1]))

                        edgesOfNewPathAndCycles = (toOrigin - toDelete) | toAdd
                        p = self.topo.shortestPath(acc[0], acc[-1], 'Hop', edgesOfNewPathAndCycles)
                        acc = p[1]
                # 
                # If allow extra links end
                #

                links = self.bindLinks[req][path][w]
                arrive = self.swapped(path, links)

                if req[1] == arrive:
                    finished.append(req)
            # for w end
        # for pathWithWidth end

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
                        if link.lifetime > self.linkLifetime:
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
        print('[', self.name, '] P4 End')

        return self.result

if __name__ == '__main__':

    topo = Topo.generate(100, 0.9, 5, 0.001, 6)
    # f = open('logfile.txt', 'w')
    
    a1 = OnlineAlgorithm(topo)
    # a2 = GreedyHopRouting(topo)
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

    # for i in range(ttime):
    #     t3 = a3.work(requests[i], i)

    for node in topo.nodes:
        if memory[node.id] != node.remainingQubits:
            print(node.id, memory[node.id]-node.remainingQubits)

