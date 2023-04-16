import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase, Request, Path
from GreedyHopRouting import GreedyHopRouting
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from random import sample
from string import Template

class GreedyHopRouting_OPP(GreedyHopRouting):
    def __init__(self, topo):
        super().__init__(topo)
        self.name = 'Greedy_OPP'
        self.requests = []
        self.totalTime = 0
        self.totalUsedQubits = 0

    def prepare(self):
        self.totalTime = 0
        self.requests.clear()
      
    def trySwapped(self):
        """
            try swapped 
        """
        reqUpdated = {req: 0 for req in self.requests}
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
                intermediate = req.intermediate

                if intermediate not in p or intermediate == req.dst or reqUpdated[req] == 1:
                    continue
                
                _p = p[p.index(intermediate):len(p)]
                _links = links[p.index(intermediate):len(p)-1]
                arrive = self.OPPSwapped(_p, _links)

                if intermediate == arrive:
                    continue
                
                if intermediate != req.src:  # Increase 1 Qubits for intermediate
                    intermediate.clearIntermediate() 
                
                if arrive != req.dst:    # Arrive not destination
                    # arrive.assignIntermediate()
                    pass
                else:
                    finished.append(req)
                
                if arrive not in self.topo.socialRelationship[req.src] and arrive != req.dst: # Check the trust for intermediate
                    req.broken = True
                

                if not req.CImark:
                    req.CImark = True
                    # Calculate the rate of intermediate
                    for s in range(1, len(p) - 2):
                        self.totalNumOfNormalNodeOnPath += 1
                        if p[s] in self.topo.socialRelationship[req.src]:
                            self.totalNumOfIntermediate += 1
                
                req.intermediate = arrive
                req.storageTime = 0
                reqUpdated[req] = 1
                req.numOfTemporary += 1

        # Delete the finished request
        for req in finished:
            if req in self.requests:
                # print('[', self.name, '] Finished Requests:', req.src.id, req.dst.id, req.time)
                self.totalTime += self.timeSlot - req.time
                if req.broken:
                    self.totalNumOfBrokenReq += 1
                self.totalNumOfFinishedReq += 1
                self.totalNumOfSecureReq = self.totalNumOfFinishedReq - self.totalNumOfBrokenReq
                self.requests.remove(req)
                self.totalNumOfTemporary += req.numOfTemporary

            paths = req.paths
            # Delete used links and clear entanglement for finished SD-pairs 
            for path in paths:
                links = path.links
                for link in links:
                    link.clearEntanglement()

    def p2(self):
        """
            In P2, run algorithm
        """
        # Pre-prepare and initialize
        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            request = Request(src, dst, self.timeSlot, src)
            self.requests.append(request)
    
        # Record the number of time solve requests
        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1

        self.greedyRouting()

        print(Template("[ $t ] P2 End").substitute(t=self.name))
    
    def p4(self):
        """
            In P4 will update storage time and lifetime of link
        """
        # Update storage time
        for req in self.requests:
            if req.intermediate != req.src:
                req.storageTime += 1
            clear = False
            # If time out, clear resources
            if req.storageTime > self.topo.L:
                paths = req.paths
                for path in paths:
                    # Clear links
                    links = path.links
                    for link in links:
                        link.clearEntanglement()
                    # Clear intermediates
                    if not clear and req.intermediate:
                        req.intermediate.clearIntermediate()
                        clear = True
                # Clear request' paths and reset state of request
                req.paths.clear()    
                req.state = 0
                req.storageTime = 0
                req.intermediate = req.src

        # Update links' lifetime       
        for req in self.requests:
            paths = req.paths
            for path in paths: 
                links = path.links
                for link in links:
                    if link.entangled == True:
                        link.lifetime += 1
                    # If time out, clear resources
                    if link.lifetime > self.topo.L:
                        # If link is swapped, clear swapped
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
                self.idleTime += 1

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
        print(Template("[ $t ] Idle Time: ${a}").substitute(t=self.name, a=self.result.idleTime))
        print(Template("[ $t ] Broken Requests: ${a}").substitute(t=self.name, a=self.totalNumOfBrokenReq))
        print(Template("[ $t ] P4 End").substitute(t=self.name))

        return self.result
        
if __name__ == '__main__':
    topo = Topo.generate(30, 0.9, 0.002, 6, 0.5, 15, 1)
    a1 = GreedyHopRouting_OPP(topo)
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

