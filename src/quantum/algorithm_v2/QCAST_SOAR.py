import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase, Request, Path
from AlgorithmBase import PickedPath
from QCAST import QCAST 
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from random import sample
from string import Template
import copy

class QCAST_SOAR(QCAST):
    def __init__(self, topo):
        super().__init__(topo)
        self.name = "QCAST_SOAR"
        self.requests = []
        self.mark= {}
        self.totalTime = 0
        self.totalUsedQubits = 0
        self.totalNumOfReq = 0
        self.totalNumOfBrokenReq = 0

    def prepare(self):
        self.totalTime = 0
        self.requests.clear()

    def releaseUsedLinks(self, request):
        intermediate = request.intermediate
        unavaliablePaths = []

        for path in request.paths:
            p = path.path
            links = path.links

            if intermediate not in p:
                for link in links:
                    link.clearEntanglement()
                unavaliablePaths.append(path)
            else:
                path.path = p[p.index(intermediate):len(p)]
                # Update links
                for i in range(p.index(intermediate)):
                    links[i].clearEntanglement()
                path.links = links[p.index(intermediate):len(p)-1]
                # Update intermediates
                if intermediate in path.intermediates: 
                    path.intermediates.remove(intermediate)
                pass
        
        for path in unavaliablePaths:
            if path in request.paths:
                request.paths.remove(path)

    def trySwapped(self):
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
                intermediates = path.intermediates
             
                _p = p[p.index(intermediate):len(p)]
                _links = links[p.index(intermediate):len(p)-1]
                arrive = self.swapped(_p, _links, intermediate, intermediates)
  
    def tryForward(self):
        # Forward
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
                intermediates = path.intermediates

                if intermediate not in p or intermediate == req.dst or reqUpdated[req] == 1:
                    continue
                
                _p = p[p.index(intermediate):len(p)]
                _links = links[p.index(intermediate):len(p)-1]
                arrive = self.forward(_p, _links, intermediate, intermediates)

                if intermediate == arrive:
                    continue
                
                if intermediate != req.src:  # Increase 1 Qubits for intermediate
                    intermediate.clearIntermediate() 
                
                if arrive != req.dst:    # Arrive not destination
                    arrive.assignIntermediate()
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
                req.pathlen = len(p)
                self.releaseUsedLinks(req)
                self.totalNumOfTemporary += 1

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
                # self.totalNumOfTemporary += req.numOfTemporary
                # self.totalLenOfPath += req.pathlen

            paths = req.paths
            # Delete used links and clear entanglement for finished SD-pairs 
            for path in paths:
                links = path.links
                for link in links:
                    link.clearEntanglement()

    def p2(self):
        """
            In P2, run the algorithm 
        """
        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            request = Request(src, dst, self.timeSlot, src)
            self.requests.append(request)
            self.mark[request] = False

        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1

        while True: 
            candidates = self.calCandidates(self.requests) # :type candidates: `list[PickedPath]` 
            candidates = sorted(candidates, key=lambda x: x.weight)
            if len(candidates) == 0:
                break
            pick = candidates[-1]   # :type pick: `PickedPath`

            if pick.weight > 0.0: 
                self.pickAndAssignPath(pick)
            else:
                break
        
        print(Template("[ $t ] P2 End").substitute(t=self.name))

    def swapped(self, path, links, intermediate, intermediates):
        curr = path.index(intermediate)

        # path length = 2
        if len(path) == 2:  
            if links[0].entangled:
                return path[1]
            else:
                return path[0]

        canSwapped = 1  # cumulation 2 -> can swapped

        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            if (prevLink, nextLink) not in path[n].internalLinks and (nextLink, prevLink) not in path[n].internalLinks:
                # if path[n] in intermediates:    # NOT CHECKED
                #     if prevLink.entangled and path[n].remainingQubits >= 1:
                #         canSwapped = 1
                #     else:
                #         canSwapped += 1
                # else:
                canSwapped += 1
                if canSwapped >= 2 and prevLink.entangled and nextLink.entangled:
                    if not path[n].attemptSwapping(prevLink, nextLink): # Swap failed 
                        prevLink.clearPhase4Swap()
                        nextLink.clearPhase4Swap()
                        # check left link swapped
                        for i in range(n-1,0,-1):
                            if links[i-1].swappedAt(path[i]):
                                links[i-1].clearPhase4Swap()
                            else:
                                break 
                        # check right link swapped
                        for i in range(n+1,len(path)-1):
                            if links[i].swappedAt(path[i]):
                                links[i].clearPhase4Swap()
                            else:
                                break
                    canSwapped = 0

                        
        return path[curr]

    def forward(self, path, links, intermediate, intermediates):
        curr = path.index(intermediate)

        # path length = 2
        if len(path) == 2:  
            if links[0].entangled:
                return path[1]
            else:
                return path[0]

        Connected = True
        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            if path[n] in intermediates:    # n in intermediates and n is not swapped
                if Connected and prevLink.entangled and path[n].remainingQubits >= 1 and (prevLink, nextLink) not in path[n].internalLinks:
                    curr = n
                    Connected = False

            if prevLink.entangled and prevLink.swappedAt(path[n]) and nextLink.entangled and nextLink.swappedAt(path[n]):   # Already swapped 
                if n+1 == len(path)-1 and Connected: 
                    curr = n+1
                    Connected = False
            else:
                Connected = False

        return path[curr]

    def p4(self):
        """
            In P4 will forward, update storage time and lifetime of link
        """
        self.tryForward()

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
                    if not clear:
                        req.intermediate.clearIntermediate()
                        clear = True
                # Clear request' paths and reset state of request
                req.paths.clear()
                self.numOfTimeOut += 1       
                req.state = 0
                req.storageTime = 0
                req.intermediate = req.src
                req.numOfTemporary = 0
     
        # Update links' lifetime       
        for req in self.requests:
            paths = req.paths
            for path in paths: 
                links = path.links
                p = path.path
                for link in links:
                    if link.entangled == True:
                        link.lifetime += 1
                    # time out
                    if link.lifetime > self.topo.L:
                        # link is swapped
                        if link.swapped():
                            # Check right swapped state
                            for i in range(links.index(link), len(links)-1):
                                if (links[i], links[i+1]) in p[i+1].internalLinks:
                                    links[i].clearPhase4Swap()
                                    links[i+1].clearPhase4Swap()
                                else:
                                    break
                            # Check left swapped state
                            for i in range(links.index(link), -1, -1):
                                if (links[i-1], links[i]) in p[i].internalLinks:
                                    links[i-1].clearPhase4Swap()
                                    links[i].clearPhase4Swap()
                                else:
                                    break
                        else:
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
            paths = remainReq.paths

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
    a1 = QCAST_SOAR(topo)
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
    
