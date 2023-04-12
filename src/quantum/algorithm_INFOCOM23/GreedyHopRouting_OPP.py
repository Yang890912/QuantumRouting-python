import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase, Request, Path
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from random import sample

class GreedyHopRouting_OPP(AlgorithmBase):
    def __init__(self, topo):
        super().__init__(topo)
        self.name = 'Greedy_OPP'
        self.requests = []
        self.totalTime = 0
        self.totalUsedQubits = 0

    def prepare(self):
        self.totalTime = 0
        self.requests.clear()
    
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
                    succNumOfLinks = self.topo.k

        # If path just 2 length 
        if len(path) == 2:  
            if links[0].entangled:
                return path[1]
            else:
                return path[0]

        if succNumOfLinks < self.topo.k:
            return path[0]  # Forward 0 hop
        
        if self.topo.k == 1:
            if path[1].remainingQubits < 1:
                # return path[0]  # Forward 0 hop
                pass
            else:
                path[1].remainingQubits -= 1
                return path[1]  # Forward 1 hop

            # Can consume extra memory
            # print(path[1].id, 'Qubit --')
            # path[1].remainingQubits -= 1
            # return path[1]  # Forward 1 hop

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
                    if n+1 >= self.topo.k or n == len(path)-2:   # satisfy k   
                        if path[n+1] == path[-1]:   # next terminal
                            return path[-1]

                        if path[n+1].remainingQubits < 1:   # not enough memory
                            return path[0]  # Forward 0 hop
                        else:
                            path[n+1].remainingQubits -= 1
                            return path[n+1]  # Forward n+1 hop
                    else:   
                        return path[0]      # Forward 0 hop
            elif prevLink.entangled and prevLink.swappedAt(path[n]) and nextLink.entangled and nextLink.swappedAt(path[n]):
                continue
        
        return path[0]
    
    def trySwapped(self):
        # Swapped 
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
                arrive = self.swapped(_p, _links)

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
                print('[', self.name, '] Finished Requests:', req.src.id, req.dst.id, req.time)
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
        # self.pathsSortedDynamically.clear()

        # Pre-prepare and initialize
        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            request = Request(src, dst, self.timeSlot, src)
            self.requests.append(request)
    
        # Record the number of time solve requests
        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1

        while True:
            found = False   # Record this round whether find new path to allocate resources

            # Find the shortest path and assign qubits for every srcDstPair
            for req in self.requests:
                src, dst, time = req.src, req.dst, req.time
                p = []
                p.append(src)

                # If the req has binding links, continue
                if req.state != 0:
                    continue

                # Find a shortest path by greedy min hop  
                while True:
                    last = p[-1]
                    if last == dst:
                        break

                    # Select avaliable neighbors of last(local)
                    selectedNeighbors = []    # type Node
                    selectedNeighbors.clear()
                    for neighbor in last.neighbors:
                        if neighbor.remainingQubits > 2 or (neighbor == dst and neighbor.remainingQubits > 1):
                            for link in neighbor.links:
                                if link.contains(last) and (not link.assigned):
                                    # print('select neighbor:', neighbor.id)
                                    selectedNeighbors.append(neighbor)
                                    break

                    # Choose the neighbor with smallest number of hop from it to dst
                    next = self.topo.sentinel
                    hopsCurMinNum = sys.maxsize
                    for selectedNeighbor in selectedNeighbors:
                        hopsNum = self.topo.hopsAway(selectedNeighbor, dst, 'Hop')      
                        if hopsCurMinNum > hopsNum and hopsNum != -1:
                            hopsCurMinNum = hopsNum
                            next = selectedNeighbor

                    # If have cycle, break
                    if next == self.topo.sentinel or next in p:
                        break 
                    p.append(next)
                # while end

                if p[-1] != dst:
                    continue
                
                # Caculate width for p
                width = self.topo.widthPhase2(p)
              
                if width <= 0:
                    continue

                found = True
                               
                for w in range(width):
                    path = Path()
                    path.path = p
                    # Assign Qubits for links in path 
                    for s in range(0, len(p) - 1):
                        n1 = p[s]
                        n2 = p[s+1]
                        for link in n1.links:
                            if link.contains(n2) and (not link.assigned):
                                self.totalUsedQubits += 2
                                link.assignQubits()
                                path.links.append(link)
                                break 
                                         
                    req.paths.append(path)  
            # for end
            if not found:
                break
        # while end
      
        print('[', self.name, '] P2 End')
    
    def p4(self):
     
        # Update storage time
        for req in self.requests:
            if req.intermediate != req.src:
                req.storageTime += 1
            clear = False
            # time out
            if req.storageTime > self.topo.L:
                paths = req.paths
                for path in paths:
                    # clear links
                    links = path.links
                    for link in links:
                        link.clearEntanglement()
                    #clear intermediates
                    if not clear:
                        req.intermediate.clearIntermediate()
                        # print([x.id for x in path.path])
                        # print('clear', req.intermediate.id)
                        # print(req.intermediate.remainingQubits)
                        clear = True
                # clear request' paths and reset
                # print('reset')      
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
                    # time out
                    if link.lifetime > self.topo.L:
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
                self.idleTime += 1

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
        print('[', self.name, '] Broken Requests:', self.totalNumOfBrokenReq)
        print('[', self.name, '] P4 End')

        return self.result
        
if __name__ == '__main__':
    topo = Topo.generate(30, 0.9, 0.002, 6, 0.5, 15, 1)

