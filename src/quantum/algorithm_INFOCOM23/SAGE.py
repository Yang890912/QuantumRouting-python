from random import sample
import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase, Request, Path
from GreedyHopRouting import GreedyHopRouting
from GreedyHopRouting_SOAR import GreedyHopRouting_SOAR
from GreedyHopRouting_OPP import GreedyHopRouting_OPP
from QCAST_SOAR import QCAST_SOAR
from topo.Topo import Topo 

class SAGE(AlgorithmBase):
    def __init__(self, topo, allowIntermediateFindPath = False):
        super().__init__(topo)
        self.name = "SAGE"
        self.requests = []         
        self.allowIntermediateFindPath = allowIntermediateFindPath
        self.mark = {}

        self.totalTime = 0
        self.totalUsedQubits = 0

    def decideIntermediate(self, src, dst, nodeRemainingQubits, usedNodes):
        minNum = 1 / self.topo.shortestPathTable[(src, dst)][2]
        intermediate = None

        for k in self.topo.socialRelationship[src]:
            if nodeRemainingQubits[k] <= 1 or k == dst or k in usedNodes:
                continue

            curMin = self.topo.expectTable[((src, k), (k, dst))]

            if minNum > curMin:    
                minNum = curMin
                intermediate = k

        return intermediate

    def decideSegmentation(self):
        nodeRemainingQubits = {node: node.remainingQubits for node in self.topo.nodes}
        self.totalNumOfReq += len(self.srcDstPairs)

        # Append new SDpairs
        for req in self.srcDstPairs:
            src, dst = req[0], req[1]
            time = self.timeSlot
            request = Request(src, dst, time, src)
            self.requests.append(request)

        # Find Path with our weight
        for req in self.requests:
            # Already has path, continue
            if len(req.paths) != 0:
                continue
            
            src, dst = req.src, req.dst
            p = []
            usedNodes = []
            usedNodes.append(src)
            usedNodes.append(dst)

            # Descide Intermediate to find path
            while True:
                k = self.decideIntermediate(src, dst, nodeRemainingQubits, usedNodes)
                usedNodes.append(k)
                if k == None:
                    tp = self.topo.shortestPathTable[(src, dst)][0]
                    if tp[-1] != req.dst:
                        tp = tp[0:-1]
                    for i in range(len(tp)-1, -1, -1):
                        p.insert(0, tp[i])
                    break
                else:
                    # path.intermediates.insert(0, k)
                    tp = self.topo.shortestPathTable[(k, dst)][0]
                    if tp[-1] != req.dst:
                        tp = tp[0:-1]
                    for i in range(len(tp)-1, -1, -1):
                        p.insert(0, tp[i])
                    dst = k
                    nodeRemainingQubits[k] -= 1 # temporary calculate
            
            # not has enough resource for path
            # if self.lackPathResource(req, path.path):
            #     continue
            
            width = self.topo.widthPhase2(p)

            if width <= 0:
                continue

            path = Path()
            path.path = p
            # establish intermediates
            for n in p:
                if n in self.topo.socialRelationship[req.src] and n != req.dst and n != req.src:
                    path.intermediates.append(n)
            
            # Allocate resources for path
            for i in range(0, len(p) - 1):
                n1 = p[i]
                n2 = p[i+1]
                for link in n1.links:
                    if link.contains(n2) and (not link.assigned):
                        self.totalUsedQubits += 2
                        link.assignQubits()
                        path.links.append(link)
                        break 
            
            req.paths.append(path)

    def prepare(self):
        self.requests.clear()
        self.totalTime = 0
        self.topo.genShortestPathTable("New")
        self.topo.genExpectTable()
 
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
        
        for path in unavaliablePaths:
            if path in request.paths:
                request.paths.remove(path)
         
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

    def p2Extra(self):
        # find multiPath from intermediate
        while True:
            found = False
            # Allocate resources for requests
            for req in self.requests:
                if not self.allowIntermediateFindPath:
                    if req.intermediate != req.src:
                        continue
                # Find the shortest path and assign qubits for every srcDstPair
                src, dst, time = req.intermediate, req.dst, req.time
                p = self.BFS(src, dst) # Find a shortest path by with min hop 
                if len(p) == 1:
                    continue 
              
                # Caculate width for p
                width = self.topo.widthPhase2(p)

                if width <= 0:
                    continue
                
                found = True
                path = Path()
                path.path = p

                # Allocate resources for path
                for i in range(0, len(p) - 1):
                    n1 = p[i]
                    n2 = p[i+1]
                    for link in n1.links:
                        if link.contains(n2) and (not link.assigned):
                            self.totalUsedQubits += 2
                            link.assignQubits()
                            path.links.append(link)
                            break 
                
                # Construct path2Intermediates   
                for i in range(len(p)):
                    if p[i] != p[0] and p[i] != p[-1] and p[i] in self.topo.socialRelationship[req.src]:
                        path.intermediates.append(p[i])
                        # print('path2Intermediates:', len(self.path2Intermediates[path]))
                
                req.paths.append(path)
            # for end
            if not found:
                break
        # While end
        print('[', self.name, '] P2 Extra End')

    def BFS(self, src, dst):
        queue = []
        visited = {node : False for node in self.topo.nodes}
        lastNode = {node : self.topo.sentinel for node in self.topo.nodes}

        queue.append(src)
        visited[src] = True
        while len(queue):
            currentNode = queue.pop(0)
            for link in currentNode.links:
                if not link.assigned:
                    nextNode = link.theOtherEndOf(currentNode)
                    if not visited[nextNode] and (nextNode.remainingQubits >= 2 or (nextNode.remainingQubits >= 1 and nextNode == dst)):
                        # find a node is unvisited and has resource
                        queue.append(nextNode)
                        visited[nextNode] = True
                        lastNode[nextNode] = currentNode

        if lastNode[dst] == self.topo.sentinel:
            # unable to find path from src to dst
            return [src]

        path = []
        currentNode = dst
        while currentNode != self.topo.sentinel:
            # traceback
            path.append(currentNode)
            currentNode = lastNode[currentNode]
        
        path = path[::-1] # list reverse
        if path[0] != src or path[-1] != dst:
            print("path error", file = sys.stderr)
            exit(0)
        return path

    def tryForward(self):
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

                arrive = self.forward(p, links, intermediate, intermediates)

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
                req.pathlen = len(p)
                self.releaseUsedLinks(req)
                req.numOfTemporary += 1
                self.totalNumOfTemporary += 1
                break

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

            paths = req.paths
            # Delete used links and clear entanglement for finished SD-pairs 
            for path in paths:
                links = path.links
                for link in links:
                    link.clearEntanglement()

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

                arrive = self.swapped(p, links, intermediate, intermediates)

    # p1, p2    
    def p2(self):

        # Decide path for SDpairs
        self.decideSegmentation()

        # Sort by time & ...
        self.requests = sorted(self.requests, key=lambda x: (x.time))

        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1

        # Allocate resources for requests
        for req in self.requests:
            # not have path
            if len(req.paths) > 0:
                continue
            
            # Find the shortest path and assign qubits for every srcDstPair
            src, dst, time = req.src, req.dst, req.time
            p = []
            p = self.BFS(src, dst) # Find a shortest path by with min hop  
            if len(p) == 1:
                continue
                       
            # Caculate width for p
            width = self.topo.widthPhase2(p)
              
            if width <= 0:
                continue
            
            path = Path()
            path.path = p

            # Allocate resources for path
            for i in range(0, len(p) - 1):
                n1 = p[i]
                n2 = p[i+1]
                for link in n1.links:
                    if link.contains(n2) and (not link.assigned):
                        self.totalUsedQubits += 2
                        link.assignQubits()
                        path.links.append(link)
                        break 
            
            # Construct path2Intermediates   
            for i in range(len(p)):
                if p[i] != p[0] and p[i] != p[-1] and p[i] in self.topo.socialRelationship[req.src]:
                    path.intermediates.append(p[i])
                    # print('path2Intermediates:', len(self.path2Intermediates[path]))
          
            req.paths.append(path)

        # Find multipath in residual graph  
        self.p2Extra()
     
        print('[', self.name, '] P2 End')

    # p4, p5
    def p4(self):
        self.tryForward()

        # Update storage time
        for req in self.requests:
            if req.intermediate != req.src:
                req.storageTime += 1
            clear = False
            # Time out
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
                        # print([x.id for x in path.path])
                        # print('clear', req.intermediate.id)
                        # print(req.intermediate.remainingQubits)
                        clear = True
                # Clear request' paths and reset
                # print('reset') 
                self.numOfTimeOut += 1        
                req.paths.clear()
                req.state = 0
                req.intermediate = req.src
                req.storageTime = 0
                req.CImark = False
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
                            # check right swapped state
                            for i in range(links.index(link), len(links)-1):
                                if (links[i], links[i+1]) in p[i+1].internalLinks:
                                    links[i].clearPhase4Swap()
                                    links[i+1].clearPhase4Swap()
                                else:
                                    break
                            # check left swapped state
                            for i in range(links.index(link), -1, -1):
                                if (links[i-1], links[i]) in p[i].internalLinks:
                                    links[i-1].clearPhase4Swap()
                                    links[i].clearPhase4Swap()
                                else:
                                    break
                        else:
                            link.entangled = False
                            link.lifetime = 0

        #                       #                
        #   RECORD EXPERIMENT   #
        #                       #

        # Calculate the idle time
        for req in self.requests:
            if req.state == 0:
                self.idleTime += 1

        # Calculate the remain time
        remainTime = 0
        for remainReq in self.requests:
            print('[', self.name, '] Remain Requests:', remainReq.src.id, remainReq.dst.id, remainReq.time, remainReq.state)
            remainTime += self.timeSlot - remainReq.time
            # print(remainReq.intermediate.id)
            paths = remainReq.paths
            # for path in paths:
            #     print([x.id for x in path.path])
            #     print([x.id for x in path.intermediates])

        # self.topo.clearAllEntanglements()
        self.result.remainRequestPerRound.append(len(self.requests)/self.totalNumOfReq)  
        self.result.waitingTime = (self.totalTime + remainTime) / self.totalNumOfReq + 1
        self.result.usedQubits = self.totalUsedQubits / self.totalNumOfReq

        print('[', self.name, '] Waiting Time:', self.result.waitingTime)
        # print('[', self.name, '] Idle Time:', self.result.idleTime)
        # print('[', self.name, '] Broken Requests:', self.totalNumOfBrokenReq)
        print('[', self.name, '] P5 End')


        return self.result
    
if __name__ == '__main__':
    topo = Topo.generate(30, 0.9, 0.002, 6, 0.5, 15, 1)

    a1 = SAGE(topo)
    a2 = GreedyHopRouting_SOAR(topo)
    a3 = QCAST_SOAR(topo)

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

    print('---')
    for link in topo.links:
        link.clearEntanglement()

    for i in range(ttime):
        a2.work(requests[i], i)

    for node in topo.nodes:
        if memory[node.id] != node.remainingQubits:
            print(node.id, memory[node.id]-node.remainingQubits)
    
    print('---')
    for link in topo.links:
        link.clearEntanglement()

    for i in range(ttime):
        a3.work(requests[i], i)

    for node in topo.nodes:
        if memory[node.id] != node.remainingQubits:
            print(node.id, memory[node.id]-node.remainingQubits)
    
    print('---')


