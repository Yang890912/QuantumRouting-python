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

    def checkReqState(self):
        finished = []
        unfinished = []
        reallocated = []

        for path in self.pathsSortedDynamically:
            (_, width, p, time) = path
            req = (p[0], p[-1], time)

            if req not in self.requests:    
                if req in self.bindLinks:   # If the SD-pair has finished but links are not deleted
                    print('[', self.name, '] Finish')
                    print('[', self.name, '] Remain Links:', len(self.bindLinks[req]))
                    for link in self.bindLinks[req]:
                        link.clearEntanglement()
                    self.bindLinks.pop(req)
                    finished.append(path)
                else:  # If the SD-pair has finished and release links
                    # print('[', self.name, '] Finish and No Remain Links')
                    finished.append(path)
            elif req in self.requests and len(self.bindLinks[req]) == 0 and self.state[req] == 1:   # If the request using all links but failed, reallocate
                print('[', self.name, '] Reallocated')
                reallocated.append(path)
                self.state[req] = 0
            else:   # If the SD-pair unfinished
                # print('[', self.name, '] Unfinished')
                unfinished.append(path)
                self.state[req] = 1

        print('---')
        return finished, unfinished, reallocated

    def p2(self):
        # self.pathsSortedDynamically.clear()

        # pre-prepare and initial
        for req in self.srcDstPairs:
            (src, dst) = req
            self.totalNumOfReq += 1
            self.requests.append((src, dst, self.timeSlot))
            self.bindLinks[(src, dst, self.timeSlot)] = []
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
                if self.state[req] == 1:
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
                self.pathsSortedDynamically.append((0.0, width, p, time))
                self.pathsSortedDynamically = sorted(self.pathsSortedDynamically, key=lambda x: x[1])

                # Assign Qubits for links in path 
                for _ in range(0, width):
                    for s in range(0, len(p) - 1):
                        n1 = p[s]
                        n2 = p[s+1]
                        for link in n1.links:
                            if link.contains(n2) and (not link.assigned):
                                self.totalUsedQubits += 2
                                link.assignQubits()
                                self.bindLinks[req].append(link)
                                break    
            # for end
            if not found:
                break
        # while end

        # Calculate the idle time 
        for req in self.requests:
            pick = False
            for path in self.pathsSortedDynamically:
                (_, width, p, time) = path
                if (p[0], p[-1], time) == req:
                    pick = True
                    break               
            if not pick:
                self.result.idleTime += 1

        print('[', self.name, '] P2 End')
    
    def p4(self):

        for path in self.pathsSortedDynamically:
            (_, width, p, time) = path
            oldNumOfPairs = len(self.topo.getEstablishedEntanglements(p[0], p[-1]))
            req = (p[0], p[-1], time)
            links = self.bindLinks[req]
            theSwappedLinks = set()

            print('---swap start---')
            print(p[0].id, p[-1].id, time)
            print('[', self.name, '] Width:', width)
            print('[', self.name, '] Path:', [x.id for x in p])
            print('[', self.name, '] Used Links:', len(links))
 
            for _ in range(0, width):

                nodes = []
                prevLinks = []
                nextLinks = [] 

                # swap (select links)
                for i in range(1, len(p) - 1):
                    prev = p[i-1]
                    curr = p[i]
                    next = p[i+1]
                    prevLink = []
                    nextLink = []
                    
                    for link in curr.links:
                        if link.entangled and (link.n1 == prev and not link.s2 or link.n2 == prev and not link.s1) and link in links:
                            # print('prev link', link.id)
                            prevLink.append(link)
                            break

                    for link in curr.links:
                        if link.entangled and (link.n1 == next and not link.s2 or link.n2 == next and not link.s1) and link in links:
                            # print('next link', link.id)
                            nextLink.append(link)
                            break

                    if len(prevLink) == 0 or len(nextLink) == 0:
                        break

                    nodes.append(curr)
                    prevLinks.append(prevLink[0])
                    nextLinks.append(nextLink[0])

                # swap  
                if len(nodes) == len(p) - 2 and len(p) > 2:
                    for (node, l1, l2) in zip(nodes, prevLinks, nextLinks):
                        # print(l1.id, l2.id)
                        theSwappedLinks.add(l1)
                        theSwappedLinks.add(l2)                    
                        node.attemptSwapping(l1, l2)
                
                if len(p) == 2:
                    prev = p[0]
                    curr = p[1]
                    for link in prev.links:
                        if link.entangled and (link.n1 == prev and not link.s2 or link.n2 == prev and not link.s1) and link in links:
                            theSwappedLinks.add(link)
                            break
            # for end

            succ = len(self.topo.getEstablishedEntanglements(p[0], p[-1])) - oldNumOfPairs
            print('[', self.name, '] Succ:', succ)
            print('[', self.name, '] Remove Links:', len(theSwappedLinks))
            print('---swap end---')


            # Remove finished requests for 1 length 
            if len(p) == 2:
                if req in self.requests:
                    self.totalTime += self.timeSlot - time
                    self.requests.remove(req)
            
            # Remove finished requests
            while succ > 0:
                if req in self.requests:
                    self.totalTime += self.timeSlot - time
                    self.requests.remove(req)   
                succ -= 1

            # Delete used links and clear entanglement for swapped 
            for link in theSwappedLinks:
                link.clearEntanglement()
                if link in links:
                    links.remove(link)
        # for end

        # Delete used links and clear entanglement for finished SD-pairs 
        # check and change the state of each request
        finished, unfinished, reallocated = self.checkReqState()
            
        for path in finished:
            self.pathsSortedDynamically.remove(path)

        for path in reallocated:
            self.pathsSortedDynamically.remove(path)

        # link dead
        for req in self.bindLinks:
            for link in self.bindLinks[req]:
                if link.entangled == True:
                    link.lifetime += 1
                    if link.lifetime > self.linkLifetime:
                        link.entangled == False
                        link.lifetime = 0

        #                       #                
        #   RECORD EXPERIMENT   #
        #                       #

        # Calculate the remaining time for unfinished SD-pairs
        remainTime = 0
        print('[', self.name, '] Remain Requests:', len(self.requests))
        for remainReq in self.requests:
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
    
    a1 = GreedyHopRouting(topo)
    # a2 = MyAlgorithm(topo)
    a3 = FER(topo)
    a4 = OnlineAlgorithm(topo)
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
    
    samplesPerTime = 2
    ttime = 100
    rtime = 10
    requests = {i : [] for i in range(ttime)}

    for i in range(ttime):
        if i < rtime:
            a = sample(topo.nodes, samplesPerTime)
            for n in range(0,samplesPerTime,2):
                requests[i].append((a[n], a[n+1]))

    # for i in range(ttime):
    #     t4 = a4.work(requests[i], i)
    
    for i in range(ttime):
        t1 = a1.work(requests[i], i)

    # for i in range(ttime):
    #     t3 = a3.work(requests[i], i)
