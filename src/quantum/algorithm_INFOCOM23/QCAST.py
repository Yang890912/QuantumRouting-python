import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase, Request, Path
from AlgorithmBase import PickedPath
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from random import sample
from string import Template
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

    def p2(self):
        """
            P2
        """
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
                candidates = self.calCandidates(self.requests) # :type candidates: `list[PickedPath]``   
                candidates = sorted(candidates, key=lambda x: x.weight)
                if len(candidates) == 0:
                    break
                pick = candidates[-1]   # :type pick: `PickedPath`

                if pick.weight > 0.0: 
                    self.pickAndAssignPath(pick)
                else:
                    break
    
        print(Template("[ $t ] P2 End").substitute(t=self.name))

    def calCandidates(self, requests): 
        """
            Calculate the candidate path for each requests 

            :return: the candidate path for each requests
            :rtype: `list[PickedPath]`
            :param requests: the requets
            :type requests: `list[(Node,Node)]`
        """
        candidates = [] 
        for req in requests:
            candidate = []
            src, dst, time = req.src, req.dst, req.time
            maxM = min(src.remainingQubits, dst.remainingQubits)
            # If not enough qubit
            if maxM == 0:   
                continue

            # If the req has binding links, continue
            if req.state != 0:  
                continue

            # w = maxM, maxM-1, maxM-2, ..., 1
            for w in range(maxM, 0, -1): 
                failNodes = []

                # Collect fail nodes (they dont have enough Qubits for SDpair in width w)
                for node in self.topo.nodes:
                    if node.remainingQubits < 2 * w and node != src and node != dst:
                        failNodes.append(node)

                edges = {}  # :type edges: `dict{(Node, Node): list[Link]}`

                # Collect edges with links 
                for link in self.topo.links:
                    # if link.n2.id < link.n1.id:
                    #     link.n1, link.n2 = link.n2, link.n1
                    if not link.assigned and link.n1 not in failNodes and link.n2 not in failNodes:
                        if not edges.__contains__((link.n1, link.n2)):
                            edges[(link.n1, link.n2)] = []
                        edges[(link.n1, link.n2)].append(link)

                neighborsOf = {node: [] for node in self.topo.nodes} # :type neighborsOf: `dict{Node: list[Node]}`

                # Filter available links satisfy width w
                for edge in edges:
                    links = edges[edge]
                    if len(links) >= w:
                        neighborsOf[edge[0]].append(edge[1])
                        neighborsOf[edge[1]].append(edge[0])

                                             
                if (len(neighborsOf[src]) == 0 or len(neighborsOf[dst]) == 0):
                    continue

                prevFromSrc = {}   # :type prevFromSrc: `dict{cur: prev}`

                def getPathFromSrc(n): 
                    path = []
                    cur = n
                    while (cur != self.topo.sentinel): 
                        path.insert(0, cur)
                        cur = prevFromSrc[cur]
                    return path
                
                # :type E: `dict{Node id: list[int, list[double]]}`
                # :type q: `list[(E, Node, Node)]`
                E = {node.id : [-sys.float_info.max, [0.0 for _ in range(0,w+1)]] for node in self.topo.nodes}  
                q = []  

                E[src.id] = [sys.float_info.max, [0.0 for _ in range(0,w+1)]]
                q.append((E[src.id][0], src, self.topo.sentinel))
                q = sorted(q, key=lambda q: q[0])

                # Dijkstra by EXT
                while len(q) != 0:
                    # Pop the node with the highest E
                    contain = q.pop(-1) 
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

                # If this SD-pair find a path, go on solving the next SD-pair 
                if len(candidate) > 0:
                    candidates += candidate
                    break
            # for w end      
        # for pairs end
        return candidates

    def pickAndAssignPath(self, pick, majorPath=None):
        """
            Pick and assign resources for paths for request

            :param pick: the picked path
            :type pick: `PickedPath`
            :param majorPath: if QCAST find recovery path, then will use it
            :type majorPath: `PickedPath`     
        """
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
 
    def trySwapped(self):
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
                arrive = self.traditionSwapped(p, links)

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
        """
            P4
        """
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
            Record experiment   
        """  
        # Calculate the idle time for all requests
        for req in self.requests:
            if req.state == 0:
                self.result.idleTime += 1

        # Calculate the remaining time for unfinished SD-pairs
        remainTime = 0
        for remainReq in self.requests:
            remainTime += self.timeSlot - remainReq.time

        # self.topo.clearAllEntanglements()
        self.result.remainRequestPerRound.append(len(self.requests)/self.totalNumOfReq)   
        self.result.waitingTime = (self.totalTime + remainTime) / self.totalNumOfReq + 1
        self.result.usedQubits = self.totalUsedQubits / self.totalNumOfReq

        print(Template("[ $t ] Remain Requests: ${a}").substitute(t=self.name, a=len(self.requests)))
        print(Template("[ $t ] Waiting Time: ${a}").substitute(t=self.name, a=self.result.waitingTime))
        print(Template("[ $t ] P4 End").substitute(t=self.name))

        return self.result

if __name__ == '__main__':
    topo = Topo.generate(30, 0.9, 0.002, 6, 0.5, 15, 1)
    a1 = QCAST(topo)
    samplesPerTime = 10
    ttime = 200
    rtime = 10
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
    
    # Run
    for i in range(ttime):
        a1.work(requests[i], i)

    for node in topo.nodes:
        if memory[node.id] != node.remainingQubits:
            print(node.id, memory[node.id]-node.remainingQubits)

