import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase
from GreedyHopRouting import GreedyHopRouting
from MyAlgorithm import MyAlgorithm
from OnlineAlgorithm import OnlineAlgorithm
from FER import FER
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from random import sample

class GreedyHopRouting_OPP(AlgorithmBase):

    def __init__(self, topo, k):
        super().__init__(topo)
        self.name = "Greedy_OPP"
        self.pathsSortedDynamically = []
        self.requests = []
        self.bindLinks = {}
        self.state = {}
        self.reqToIntermediate = {}
        self.linkLifetime = 30
        self.k = k

        self.totalTime = 0
        self.totalUsedQubits = 0
        self.totalNumOfReq = 0

    def prepare(self):
        self.totalTime = 0
        self.requests.clear()

    # def updateRequestState(self, theFariestIntermediate):
    #     finished = []
    #     unfinished = []
    #     reallocated = []

    #     for path in self.pathsSortedDynamically:
    #         (_, width, p, time, intermediate, req) = path
    #         # req = (p[0], p[-1], time)

    #         if req not in self.requests:    
    #             if req in self.bindLinks:   # If the SD-pair has finished but links are not deleted
    #                 print('[', self.name, '] Finish')
    #                 for link in self.bindLinks[req]:
    #                     link.clearEntanglement()
    #                 self.bindLinks.pop(req)
    #                 finished.append(path)
    #             else:  # If the SD-pair has finished and release links
    #                 # print('[', self.name, '] Finish and No Remain Links')
    #                 finished.append(path)
    #         # elif req in self.requests and len(self.bindLinks[req]) == 0 and self.state[req] == 1:   # If the request using all links but failed, reallocate
    #         #     print('[', self.name, '] Reallocated')
    #         #     reallocated.append(path)
    #         #     self.state[req] = 0
    #         elif req in self.requests and req in theFariestIntermediate:   # If the request using some links to intermediate 
    #             if intermediate == theFariestIntermediate[req][0]:
    #                 print('[', self.name, '] Intermediate')
    #                 intermediate.remainingQubits -= 1
    #                 for link in theFariestIntermediate[req][2]:
    #                     link.clearEntanglement()
    #                     if link in self.bindLinks[req]:
    #                         self.bindLinks[req].remove(link)
    #             self.state[req] = 2  
    #         else:   # If the SD-pair unfinished
    #             print('[', self.name, '] No Intermediate')
    #             print('[', self.name, '] Path:', [x.id for x in p])
    #             print('[', self.name, '] Intermediate Node:', intermediate.id)
    #             unfinished.append(path)
    #             self.state[req] = 1

    #     print('---')
    #     return finished, unfinished, reallocated

    # def succeedStateOfPath(self, path, width, links):
    #     succ = 0
    #     intermediate = self.topo.sentinel 
    #     farAway = -1
    #     theSwappedLinks = set()
    #     releaseLinks = set()

    #     for _ in range(0, width):
    #         nodes = []
    #         prevLinks = []
    #         nextLinks = [] 
    #         _intermediate = self.topo.sentinel 
    #         _farAway = -1
    #         _releaseLinks = set()

    #         # swap (select links)
    #         for i in range(1, len(path) - 1):
    #             prev = path[i-1]
    #             curr = path[i]
    #             next = path[i+1]
    #             prevLink = []
    #             nextLink = []
                
    #             for link in curr.links:
    #                 if link.entangled and (link.n1 == prev and not link.s2 or link.n2 == prev and not link.s1) and link in links:
    #                     # print('prev link', link.id)
    #                     prevLink.append(link)
    #                     break

    #             for link in curr.links:
    #                 if link.entangled and (link.n1 == next and not link.s2 or link.n2 == next and not link.s1) and link in links:
    #                     # print('next link', link.id)
    #                     nextLink.append(link)
    #                     break

    #             if len(prevLink) == 0 or len(nextLink) == 0:
    #                 _intermediate = curr
    #                 _farAway = i
    #                 break

    #             nodes.append(curr)
    #             prevLinks.append(prevLink[0])
    #             nextLinks.append(nextLink[0])

    #         swapFailed = False
            
        #     # swap
        #     if len(nodes) <= len(path) - 2 and len(path) > 2:
        #         for (node, l1, l2) in zip(nodes, prevLinks, nextLinks):
        #             # print(l1.id, l2.id)
        #             theSwappedLinks.add(l1)
        #             theSwappedLinks.add(l2)                    
        #             if not node.attemptSwapping(l1, l2):
        #                 swapFailed = True

        #             if len(nodes) < len(path) - 2:
        #                 _releaseLinks.add(l1)
        #                 _releaseLinks.add(l2)
                         

        #     if not swapFailed and _farAway == -1:
        #         succ += 1
        #     elif not swapFailed and _farAway != -1:
        #         if _farAway > farAway:
        #             intermediate = _intermediate 
        #             releaseLinks = _releaseLinks
        #             farAway = _farAway

        # return succ, intermediate, farAway, theSwappedLinks, releaseLinks    

    def swapped(self, path, links):
        succNumOfLinks = 0

        # Calculate the continuous succeed links whether larger than k
        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            if prevLink.entangled:
                succNumOfLinks += 1
            else:
                break

            if n == len(path)-2:
                if nextLink.entangled:
                    succNumOfLinks += 1

      
        if len(path) == 2:  # If path just 2 length 
            if links[0].entangled:
                succNumOfLinks = self.k
        
        if succNumOfLinks < self.k:
            return path[0]  # Forward 0 hop
        
        if len(path) == 2 or self.k == 1:
            if path[1] == path[-1]: # next terminal
                return path[1]

            if path[1].remainingQubits < 1:
                return path[0]  # Forward 0 hop
            else:
                path[1].remainingQubits -= 1
                return path[1]  # Forward 1 hop

        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            if prevLink.entangled and not prevLink.swappedAt(path[n]) and nextLink.entangled and not prevLink.swappedAt(path[n]):
                if not path[n].attemptSwapping(prevLink, nextLink): # Swap failed than clear the link state
                    for link in links:
                        if link.swapped():
                            link.clearPhase4Swap() 
                    return path[0]          # Forward 0 hop
                else:       
                    if n+1 >= self.k or n == len(path)-2:   # Swap succeed and the next hop is distance or immediate than forward to it
                        if path[n+1] == path[-1]: # next terminal
                            return path[n+1]

                        if path[n+1].remainingQubits < 1:
                            return path[0]  # Forward 0 hop
                        else:
                            path[n+1].remainingQubits -= 1
                            return path[n+1]  # Forward n+1 hop
                    else:   
                        return path[0]      # Forward 0 hop
            elif prevLink.entangled and prevLink.swappedAt(path[n]) and nextLink.entangled and prevLink.swappedAt(path[n]):
                continue
        
    def p2(self):
        # self.pathsSortedDynamically.clear()

        # Pre-prepare and initialize
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
                self.reqToIntermediate[req] = p[0]
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
        reqUpdated = {req: 0 for req in self.reqToIntermediate}
        print('[', self.name, '] Swapped 1')

        # Swapped (1)
        for path in self.pathsSortedDynamically:
            (_, width, p, time, req) = path
            self.state[req] = 1   

            for w in range(0, width): 
                intermediate = self.reqToIntermediate[req]
                links = self.bindLinks[req][path][w]

                if intermediate not in p or intermediate == req[1] or reqUpdated[req] == 1:
                    continue

                _p = p[p.index(intermediate):len(p)]
                _links = links[p.index(intermediate):len(p)-1]
                arrive = self.swapped(_p, _links)

                if intermediate == arrive:
                    continue
                
                print('[', self.name, '] Path:', [x.id for x in p])
                print('[', self.name, '] Links:', [x.id for x in links])
                print('arrive:', arrive.id)
                print('[', self.name, '] Path2:', [x.id for x in _p])
                print('[', self.name, '] Links2:', [x.id for x in _links])
                
                if intermediate != req[0]:  
                    intermediate.remainingQubits += 1       
                self.reqToIntermediate[req] = arrive
                reqUpdated[req] = 1
                break
        
        # Calculate the number of finished request
        finished = []
        for req in self.requests:
            if req not in self.reqToIntermediate:
                continue
            intermediate = self.reqToIntermediate[req]
            if intermediate == req[1]:  # intermediate = terminal
                for path in self.bindLinks[req]:
                    self.pathsSortedDynamically.remove(path)
                    (_, width, p, time, req) = path
                    for w in range(0, width): 
                        for link in self.bindLinks[req][path][w]:
                            link.clearEntanglement()
                
                self.reqToIntermediate.pop(req)
                self.bindLinks.pop(req)
                finished.append(req)
        
        # Delete the finished request
        for req in finished:
            if req in self.requests:
                self.totalTime += self.timeSlot - req[2]
                self.requests.remove(req)                

        # Calculate the idle time for all requests
        for req in self.requests:
            # pick = False
            # for path in self.pathsSortedDynamically:
            #     (_, width, p, time, _req) = path
            #     if _req == req:
            #         pick = True
            #         break               
            # if not pick:
            #     self.result.idleTime += 1
            if req in self.reqToIntermediate:
                continue
            else: 
                self.result.idleTime += 1

        print('[', self.name, '] P2 End')
    
    def p4(self):

        # theFariestIntermediate = {}
        # newPath = []
        reqUpdated = {req: 0 for req in self.reqToIntermediate}

        print('[', self.name, '] Swapped 2')

        # Swapped (2)
        for path in self.pathsSortedDynamically:
            (_, width, p, time, req) = path
            self.state[req] = 1   

            for w in range(0, width): 
                intermediate = self.reqToIntermediate[req]
                links = self.bindLinks[req][path][w]

                if intermediate not in p or intermediate == req[1] or reqUpdated[req] == 1:
                    continue
                
                _p = p[p.index(intermediate):len(p)]
                _links = links[p.index(intermediate):len(p)-1]
                arrive = self.swapped(_p, _links)

                if intermediate == arrive:
                    continue

                print('[', self.name, '] Path:', [x.id for x in p])
                print('[', self.name, '] Links:', [x.id for x in links])
                print('arrive:', arrive.id)
                print('[', self.name, '] Path2:', [x.id for x in _p])
                print('[', self.name, '] Links2:', [x.id for x in _links])

                if intermediate != req[0]:  
                    intermediate.remainingQubits += 1       
                self.reqToIntermediate[req] = arrive
                reqUpdated[req] = 1
                break

        # Calculate the number of finished request
        finished = []
        for req in self.requests:
            if req not in self.reqToIntermediate:
                continue
            intermediate = self.reqToIntermediate[req]
            if intermediate == req[1]:  # intermediate = terminal
                for path in self.bindLinks[req]:
                    (_, width, p, time, req) = path
                    for w in range(0, width): 
                        for link in self.bindLinks[req][path][w]:
                            link.clearEntanglement()
                    self.pathsSortedDynamically.remove(path)

                self.reqToIntermediate.pop(req)
                self.bindLinks.pop(req)
                finished.append(req)
        
        # Delete the finished request
        for req in finished:
            if req in self.requests:
                self.totalTime += self.timeSlot - req[2]
                self.requests.remove(req)

            # if self.state[req] == 1:
            #     newPath.append(currNewPath)
            #     continue

            # if self.state[req] == 2 and self.reqToIntermediate[req] != intermediate:
            #     newPath.append(currNewPath)
            #     continue

            # if self.state[req] == 2:
            #     intermediate.remainingQubits += 1
            #     p = p[p.index(intermediate):len(p)]

            
            # print('[', self.name, '] Request:', p[0].id, p[-1].id, time)
            # print('[', self.name, '] Width:', width)
            # print('[', self.name, '] Path:', [x.id for x in p])
            # print('[', self.name, '] Used Links:', len(links))
 
            # succ, _intermediate, farAway, theSwappedLinks, releaseLinks = self.succeedStateOfPath(p, width, links)
            # currNewPath =  (_, width, p, time, _intermediate, req)
            # newPath.append(currNewPath)

            # print('[', self.name, '] Intermediate:', _intermediate.id)
            # print('[', self.name, '] FarAway:', farAway)

            # Update the fariest intermediate for SD-pairs
            # if req in theFariestIntermediate:
            #     if farAway > theFariestIntermediate[req][1] and _intermediate.remainingQubits >= 1:
            #         theFariestIntermediate[req] = (_intermediate, farAway, releaseLinks)
            #         self.reqToIntermediate[req] = _intermediate
            # elif _intermediate.remainingQubits >= 1:
            #     theFariestIntermediate[req] = (_intermediate, farAway, releaseLinks) 
            #     self.reqToIntermediate[req] = _intermediate   

            # print(theFariestIntermediate)

            # succ = len(self.topo.getEstablishedEntanglements(p[0], p[-1])) - oldNumOfPairs
            # print('[', self.name, '] Succ:', succ)
            # print('[', self.name, '] Swapped Links:', len(theSwappedLinks))
            # print('---swap end---')


            # Remove finished requests for 1 length 
            # if len(p) == 2:
            #     if req in self.requests:
            #         self.totalTime += self.timeSlot - time
            #         self.requests.remove(req)
            
            # Remove finished requests
            # while succ > 0:
            #     if req in self.requests:
            #         self.totalTime += self.timeSlot - time
            #         self.requests.remove(req)   
            #     succ -= 1

            # Clear entanglement for swapped links
            # for link in theSwappedLinks:
            #     link.clearPhase4Swap()
        # for end

        # Update the paths' state
        # self.pathsSortedDynamically = newPath
          
        # Delete and clear entanglement for finished SD-pairs 
        # check and update the state of each request
        # finished, unfinished, reallocated = self.updateRequestState(theFariestIntermediate)
            
        # for path in finished:
        #     self.pathsSortedDynamically.remove(path)

        # for path in reallocated:
        #     self.pathsSortedDynamically.remove(path)

        # update links' lifetime
        # for req in self.bindLinks:
        #     for link in self.bindLinks[req]:
        #         if link.entangled == True:
        #             link.lifetime += 1
        #             if link.lifetime > self.linkLifetime:
        #                 link.entangled == False
        #                 link.lifetime = 0
        
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

    topo = Topo.generate(100, 0.8, 5, 0.001, 6)
    # f = open('logfile.txt', 'w')
    
    a1 = GreedyHopRouting_OPP(topo, 1)
    a2 = GreedyHopRouting(topo)
    a3 = GreedyHopRouting_OPP(topo, 2)
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
    rtime = 1
    requests = {i : [] for i in range(ttime)}
    memory = {}

    for i in range(ttime):
        if i < rtime:
            a = sample(topo.nodes, samplesPerTime)
            for n in range(0,samplesPerTime,2):
                requests[i].append((a[n], a[n+1]))

    for node in a1.topo.nodes:
        memory[node.id] = node.remainingQubits

    # for i in range(ttime):
    #     t2 = a2.work(requests[i], i)
    
    for i in range(ttime):
        t1 = a1.work(requests[i], i)

    print('----------')

    for i in range(ttime):
        t3 = a3.work(requests[i], i)

    for node in a1.topo.nodes:
        if memory[node.id] != node.remainingQubits:
            print(node.id, memory[node.id]-node.remainingQubits)