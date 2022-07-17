import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase
from MyAlgorithm import MyAlgorithm
from OnlineAlgorithm import OnlineAlgorithm
from FER import FER
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from random import sample

class GreedyHopRouting(AlgorithmBase):

    def __init__(self, topo):
        super().__init__(topo)
        self.name = "Greedy_H"
        self.pathsSortedDynamically = []
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

    def p2(self):
        # self.pathsSortedDynamically.clear()

        # pre-prepare and initial
        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            self.requests.append((src, dst, self.timeSlot))
            self.bindLinks[(src, dst, self.timeSlot)] = {}
            self.state[(src, dst, self.timeSlot)] = 0
    
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
                
                if width == 0:
                    continue

                found = True
                path = (0.0, width, tuple(p), time, req)
                self.pathsSortedDynamically.append(path)   # (weight, width, path, time, req)
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
        print('[', self.name, '] P2 End')
    
    def p4(self):

        finished = []
        # Swapped 
        for path in self.pathsSortedDynamically:
            (_, width, p, time, req) = path
            self.state[req] = 1 

            if req in finished:
                continue

            for w in range(0, width): 
                links = self.bindLinks[req][path][w]
                arrive = self.swapped(p, links)

                if req[1] == arrive:
                    finished.append(req)

        # Calculate the idle time for all requests
        for req in self.requests:
            if self.state[req] == 0: 
                self.result.idleTime += 1

        # Calculate the finished number of requests
        for req in finished:
            if req in self.requests:
                print('[', self.name, '] Finished Requests:', req[0].id, req[1].id, req[2])
                self.totalTime += self.timeSlot - req[2]
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

        # Update links' lifetime       
        for path in self.pathsSortedDynamically:
            (_, width, p, time, req) = path
  
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

        # Calculate the remaining time for unfinished SD-pairs
        remainTime = 0
        for remainReq in self.requests:
            print('[', self.name, '] Remain Requests:', remainReq[0].id, remainReq[1].id, remainReq[2])
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
        print('[', self.name, '] P4 End')

        return self.result
        
if __name__ == '__main__':

    topo = Topo.generate(100, 0.9, 5, 0.001, 6)
    # f = open('logfile.txt', 'w')
    
    a1 = GreedyHopRouting(topo)
    # a2 = MyAlgorithm(topo)
    # a3 = FER(topo)
    # a4 = OnlineAlgorithm(topo)
    # samplesPerTime = 2

    # while samplesPerTime < 11:
    #     ttime = 200
    #     rtime = 10
    #     requests = {i : [] for i in range(ttime)}
    #     t1 = 0
    #     t2 = 0
    #     t3 = 0
    #     t4 = 0
    #     f.write(str(samplesPerTime/2)+' ')
    #     f.flush()
    #     for i in range(ttime):
    #         if i < rtime:
    #             a = sample(topo.nodes, samplesPerTime)
    #             for n in range(0,samplesPerTime,2):
    #                 requests[i].append((a[n], a[n+1]))
            

    #     for i in range(ttime):
    #         t1 = a1.work(requests[i], i)
    #     f.write(str(t1/(samplesPerTime/2*rtime))+' ')
    #     f.flush()

    #     for i in range(ttime):
    #         t3 = a3.work(requests[i], i)
    #     f.write(str(t3/(samplesPerTime/2*rtime))+' ')
    #     f.flush()

    #     for i in range(ttime):
    #         t4 = a4.work(requests[i], i)
    #     f.write(str(t4/(samplesPerTime/2*rtime))+' ')
    #     f.flush()

    #     for i in range(ttime):
    #         t2 = a2.work(requests[i], i)
    #     for req in a2.requestState:
    #         if a2.requestState[req].state == 2:
    #             a2.requestState[req].intermediate.clearIntermediate()    

    #     f.write(str(t2/(samplesPerTime/2*rtime))+'\n')
    #     f.flush()
    #     samplesPerTime += 2 

    # # 5XX
    # f.close()
    
    samplesPerTime = 10
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