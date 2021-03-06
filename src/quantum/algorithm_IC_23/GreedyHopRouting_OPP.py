import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase
from GreedyHopRouting import GreedyHopRouting
from OnlineAlgorithm import OnlineAlgorithm
from FER import FER
from FER_OPP import FER_OPP
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from random import sample

class GreedyHopRouting_OPP(AlgorithmBase):

    def __init__(self, topo, k=1):
        super().__init__(topo)
        self.name = "Greedy_OPP"
        self.pathsSortedDynamically = []
        self.requests = []
        self.bindLinks = {}
        self.state = {}
        self.req2Intermediate = {}
        self.reqBroken = {}
        self.reqStorageTime = {}
        self.k = k

        self.totalTime = 0
        self.totalUsedQubits = 0
        self.totalNumOfReq = 0
        self.totalNumOfBrokenReq = 0

    def prepare(self):
        self.totalTime = 0
        self.requests.clear()
    
    def updateLinksLifetime(self):
        # Update links' lifetime       
        for path in self.pathsSortedDynamically:
            (_, width, p, time, req) = path
  
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

    def updateStorageTime(self):
        # Update storage time 
        for req in self.requests:
            if req in self.req2Intermediate and req[0] != self.req2Intermediate[req]:
                self.reqStorageTime[req] += 1
                popPath = []

                if self.reqStorageTime[req] > self.topo.L:
                    self.req2Intermediate[req].remainingQubits += 1 
                    
                    # Delete used links and clear entanglement for  SD-pairs
                    if req in self.bindLinks:
                        for path in self.bindLinks[req]:
                            (_, width, p, time, req) = path
                            for w in range(0, width): 
                                for link in self.bindLinks[req][path][w]:
                                    link.clearEntanglement()
                            self.pathsSortedDynamically.remove(path)
                            popPath.append(path)
                    
                        for path in popPath:
                            if path in self.bindLinks[req]:
                                self.bindLinks[req].pop(path) 

                    self.state[req] = 0
                    print('reset')

    def removeAndReleaseFinishedRequests(self, finished):
        # Delete the finished request
        for req in finished:
            if req in self.requests:
                print('[', self.name, '] Finished Requests:', req[0].id, req[1].id, req[2])
                self.totalTime += self.timeSlot - req[2]
                if self.reqBroken[req]:
                    self.totalNumOfBrokenReq += 1
                self.requests.remove(req)

            # Delete used links and clear entanglement for finished SD-pairs 
            if req in self.bindLinks:
                for path in self.bindLinks[req]:
                    (_, width, p, time, req) = path
                    for w in range(0, width): 
                        for link in self.bindLinks[req][path][w]:
                            link.clearEntanglement()
                    self.pathsSortedDynamically.remove(path)
                self.bindLinks.pop(req)
                self.req2Intermediate.pop(req)       

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
        
        return path[0]

    def p2(self):
        # self.pathsSortedDynamically.clear()

        # Pre-prepare and initialize
        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            self.requests.append((src, dst, self.timeSlot))
            self.bindLinks[(src, dst, self.timeSlot)] = {}
            self.state[(src, dst, self.timeSlot)] = 0
            self.reqBroken[(src, dst, self.timeSlot)] = False
            self.reqStorageTime[(src, dst, self.timeSlot)] = 0
    
        # Record the number of time solve requests
        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1

        while True:
            found = False   # Record this round whether find new path to allocate resources

            # Find the shortest path and assign qubits for every srcDstPair
            # state = 0 -> no binding links 
            # state = 1 -> has binding links
            for req in self.requests:
                (src, dst, time) = req
                p = []
                p.append(src)

                # If the req has binding links, continue
                if self.state[req] != 0:
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
                path = (0.0, width, tuple(p), time, req)
                self.pathsSortedDynamically.append(path)   # (weight, width, path, time, req)
                self.req2Intermediate[req] = p[0]
                self.bindLinks[req][path] = []

                # Assign Qubits for links in path 
                for w in range(0, width):
                    self.bindLinks[req][path].append([])
                    for s in range(0, len(p) - 1):
                        n1 = p[s]
                        n2 = p[s+1]
                        for link in n1.links:
                            if link.contains(n2) and (not link.assigned):
                                self.totalUsedQubits += 2
                                link.assignQubits()
                                self.bindLinks[req][path][w].append(link)
                                break    
            # for end
            if not found:
                break
        # while end

        self.pathsSortedDynamically = sorted(self.pathsSortedDynamically, key=lambda x: x[1])
        reqUpdated = {req: 0 for req in self.req2Intermediate}
        finished = []

        print('[', self.name, '] Swapped 1')
        # Swapped (1)
        for path in self.pathsSortedDynamically:
            (_, width, p, time, req) = path
            self.state[req] = 1 
            intermediate = self.req2Intermediate[req]

            if req in finished:
                continue
            
            if intermediate != req[0]: 
                self.reqStorageTime[req] += 1

            for w in range(0, width): 
                if intermediate not in p or intermediate == req[1] or reqUpdated[req] == 1:
                    continue

                links = self.bindLinks[req][path][w]
                _p = p[p.index(intermediate):len(p)]
                _links = links[p.index(intermediate):len(p)-1]
                arrive = self.swapped(_p, _links)

                if intermediate == arrive:  # not forward
                    continue
                
                self.reqStorageTime[req] = 0

                if intermediate != req[0]:  
                    intermediate.remainingQubits += 1 
           
                if arrive == req[1]:    # arrive to destination
                    finished.append(req)

                if arrive not in self.topo.socialRelationship[req[0]] and arrive != req[1]: # arrive to not trust intermediate
                    self.reqBroken[req] = True

                self.req2Intermediate[req] = arrive
                reqUpdated[req] = 1
            
        self.removeAndReleaseFinishedRequests(finished) 

        print('[', self.name, '] P2 End')
    
    def p4(self):

        reqUpdated = {req: 0 for req in self.req2Intermediate}
        finished = []

        print('[', self.name, '] Swapped 2')
        # Swapped (2)
        for path in self.pathsSortedDynamically:
            (_, width, p, time, req) = path
            intermediate = self.req2Intermediate[req]

            if req in finished:
                continue

            for w in range(0, width): 
                if intermediate not in p or intermediate == req[1] or reqUpdated[req] == 1:
                    continue
                
                links = self.bindLinks[req][path][w]
                _p = p[p.index(intermediate):len(p)]
                _links = links[p.index(intermediate):len(p)-1]
                arrive = self.swapped(_p, _links)

                if intermediate == arrive:  # not forward
                    continue
      
                self.reqStorageTime[req] = 0
                
                if intermediate != req[0]:  
                    intermediate.remainingQubits += 1 

                if arrive == req[1]:    # arrive to destination
                    finished.append(req)

                if arrive not in self.topo.socialRelationship[req[0]] and arrive != req[1]: # arrive to not trust intermediate
                    self.reqBroken[req] = True

                self.req2Intermediate[req] = arrive
                reqUpdated[req] = 1

        self.removeAndReleaseFinishedRequests(finished) 
        
        # Update storage time 
        self.updateStorageTime()

        # Update links' lifetime       
        self.updateLinksLifetime()

        #                       #                
        #   RECORD EXPERIMENT   #
        #                       #

        # Calculate the idle time for all requests
        for req in self.requests:
            if self.state[req] == 0:
                self.result.idleTime += 1

        # Calculate the remaining time for unfinished SD-pairs
        remainTime = 0
        for remainReq in self.requests:
            print('[', self.name, '] Remain Requests:', remainReq[0].id, remainReq[1].id, remainReq[2], self.state[remainReq])
            remainTime += self.timeSlot - remainReq[2]
            for path in self.bindLinks[remainReq]:
                (_, width, p, time, req) = path
                for w in range(0, width): 
                    links = self.bindLinks[req][path][w]
                    print([link.swapped() for link in links])


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

    topo = Topo.generate(100, 0.9, 5, 0.005, 6)
    # f = open('logfile.txt', 'w')

    a1 = GreedyHopRouting_OPP(topo, 1)
    a2 = GreedyHopRouting_OPP(topo, 2)
    # a3 = GreedyHopRouting(topo)
    # a4 = FER_OPP(topo, 1)
 
    samplesPerTime = 8
    ttime = 200
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
    # a1
    for i in range(ttime):
        a1.work(requests[i], i)
    
    for node in topo.nodes:
        if memory[node.id] != node.remainingQubits:
            print(node.id, memory[node.id]-node.remainingQubits)

    print('---')
    for link in topo.links:
        link.clearEntanglement()

    # a2
    for i in range(ttime):
        a2.work(requests[i], i)

    for node in topo.nodes:
        if memory[node.id] != node.remainingQubits:
            print(node.id, memory[node.id]-node.remainingQubits)

    print('---')
    for link in topo.links:
        link.clearEntanglement()
    
    # # a3
    # for i in range(ttime):
    #     a4.work(requests[i], i)

    # for node in topo.nodes:
    #     if memory[node.id] != node.remainingQubits:
    #         print(node.id, memory[node.id]-node.remainingQubits)