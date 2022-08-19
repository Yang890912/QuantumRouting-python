import sys
import math
import gurobipy as gp
from gurobipy import quicksum
from queue import PriorityQueue
sys.path.append("..")
from AlgorithmBase import AlgorithmBase
from AlgorithmBase import AlgorithmResult
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link
from numpy import log as ln
from random import sample

EPS = 1e-6

class Path:
    def __init__(self):
        self.nodes = []
        self.links = []
    def setStatus(self):
        self.swapStatus = {node : False for node in self.nodes}
        self.swapStatus[self.nodes[0]] = True
        self.swapStatus[self.nodes[-1]] = True
    
class Request:
    def __init__(self, src, dst, index):
        self.src = src
        self.dst = dst
        self.index = index
        self.needFindPath = True
        self.currentTemp = (-1, -1) # [pathsIndex, nodesIndex]
        self.paths = []
        self.k = 1

class REPS(AlgorithmBase):
    def __init__(self, topo):
        super().__init__(topo)
        self.name = "REPS"
        self.requests = []
        self.isBind = {link : False for link in self.topo.links}
        self.totalNumOfReq = 0
        self.totalUsedQubits = 0
        self.totalWaitingTime = 0

    def genNameByComma(self, varName, parName):
        return (varName + str(parName)).replace(' ', '')
    def genNameByBbracket(self, varName: str, parName: list):
        return (varName + str(parName)).replace(' ', '').replace(',', '][')
    
    def printResult(self):
        self.result.waitingTime = self.totalWaitingTime / self.totalNumOfReq
        self.result.usedQubits = self.totalUsedQubits / self.totalNumOfReq
        self.result.remainRequestPerRound.append(len(self.requests) / self.totalNumOfReq)
        print("[ " + self.name + " ]", "len(srcDstPair) =", len(self.srcDstPairs))
        print("[ " + self.name + " ]", "avg time:", self.result.waitingTime)
        print("[ " + self.name + " ]", "remain request:", len(self.requests))
        print("[ " + self.name + " ]", "current Timeslot:", self.timeSlot)

    def AddNewSDpairs(self):
        for (src, dst) in self.srcDstPairs:
            self.requests.append(Request(src, dst, self.totalNumOfReq))
            self.totalNumOfReq += 1

        self.srcDstPairs = []
        self.SDpairToRequest = {}
        # requestQueue = sample(self.requests, min(5, len(self.requests)))
        for request in self.requests:
            if request.needFindPath:
                src = request.src
                dst = request.dst
                if (src, dst) not in self.srcDstPairs:
                    self.SDpairToRequest[(src, dst)] = request
                    self.srcDstPairs.append((src, dst))
            
            if len(self.srcDstPairs) >= 5:
                break
            
    def checkCanEntangled(self):
        if self.timeSlot % self.topo.L == 0:
            self.canEntangled = True
        else:
            self.canEntangled = False
    def p2(self):
        self.checkCanEntangled()
        self.AddNewSDpairs()
        self.totalWaitingTime += len(self.requests)
        self.result.idleTime += len(self.requests)
        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1
        if len(self.srcDstPairs) > 0 and (self.timeSlot % self.topo.L == 0):
            self.PFT() # find path for request
        print("[ " + self.name + " ]", "p2 end")
    
    def p4(self):
        print("[ " + self.name + " ]", "p4 end")
        self.forward()
        self.printResult()
        self.checkTimeout()
        return self.result

    def checkTimeout(self):
        for request in self.requests:
            for path in request.paths:
                path.setStatus()
        for link in self.topo.links:
            if link.entangled:
                link.lifetime += 1
            if link.lifetime > self.topo.L or (self.timeSlot % self.topo.L == self.topo.L - 1):
                link.clearPhase4Swap()

    def trySwapped(self):
        for request in self.requests:
            if len(request.paths) == 0:
                continue

            for path in request.paths:
                allLinksuccess = True
                for link in path.links:
                    if link.entangled == False:
                        allLinksuccess = False

                for nodeIndex in range(len(path.nodes)):
                    node = path.nodes[nodeIndex]
                    if path.swapStatus[node] == False and allLinksuccess:
                        link1 = path.links[nodeIndex - 1]
                        link2 = path.links[nodeIndex]
                        if link1.entangled and link2.entangled:
                            swapSuccess = path.swapStatus[node] = node.attemptSwapping(link1, link2)
                            if swapSuccess == False:
                                # swapping failed clear all link and swapStatus
                                for Index in range(nodeIndex + 1):
                                    path.links[Index].clearPhase4Swap()

                                path.setStatus()
                        break

    def forward(self):
        finishedRequest = []
        for request in self.requests:
            finish = False
            for path in request.paths:                
                thisPathFinish = True
                for node in path.nodes:
                    if path.swapStatus[node] == False:
                        thisPathFinish = False

                if thisPathFinish:
                    src = request.src
                    for nodeIndex in range(1, len(path.nodes) - 1):
                        node = path.nodes[nodeIndex]
                        if node in self.topo.socialRelationship[src]:
                            self.totalNumOfIntermediate += 1
                        self.totalNumOfNormalNodeOnPath += 1
                    finish = True
                
            if finish:
                # the request is finished
                finishedRequest.append(request)

        for request in finishedRequest:
            for path in request.paths:
                for link in path.links:
                    self.isBind[link] = False
                    link.clearEntanglement()
            self.totalNumOfFinishedReq += 1
            self.totalNumOfSecureReq += 1
            self.requests.remove(request)

    def LP1(self): # compute self.fi_LP
        print("[ " + self.name + " ]", "LP1 start")
        # initialize fi_LP(u, v) ans ti_LP

        self.fi_LP = {SDpair : {} for SDpair in self.srcDstPairs}
        self.ti_LP = {SDpair : 0 for SDpair in self.srcDstPairs}
        
        numOfNodes = len(self.topo.nodes)
        numOfSDpairs = len(self.srcDstPairs)

        edgeIndices = []
        notEdge = []
        for edge in self.topo.edges:
            edgeIndices.append((edge[0].id, edge[1].id))
        
        for u in range(numOfNodes):
            for v in range(numOfNodes):
                if (u, v) not in edgeIndices and (v, u) not in edgeIndices:
                    notEdge.append((u, v))
        # LP

        m = gp.Model(self.name + "for PFT")
        m.setParam("OutputFlag", 0)
        f = m.addVars(numOfSDpairs, numOfNodes, numOfNodes, lb = 0, vtype = gp.GRB.CONTINUOUS, name = "f")
        t = m.addVars(numOfSDpairs, lb = 0, vtype = gp.GRB.CONTINUOUS, name = "t")
        x = m.addVars(numOfNodes, numOfNodes, lb = 0, vtype = gp.GRB.CONTINUOUS, name = "x")
        m.update()
        
        m.setObjective(quicksum(t[i] for i in range(numOfSDpairs)), gp.GRB.MAXIMIZE)

        for i in range(numOfSDpairs):
            s = self.srcDstPairs[i][0].id
            m.addConstr(quicksum(f[i, s, v] for v in range(numOfNodes)) - quicksum(f[i, v, s] for v in range(numOfNodes)) == t[i])

            d = self.srcDstPairs[i][1].id
            m.addConstr(quicksum(f[i, d, v] for v in range(numOfNodes)) - quicksum(f[i, v, d] for v in range(numOfNodes)) == -t[i])

            for u in range(numOfNodes):
                if u not in [s, d]:
                    m.addConstr(quicksum(f[i, u, v] for v in range(numOfNodes)) - quicksum(f[i, v, u] for v in range(numOfNodes)) == 0)

        
        for (u, v) in edgeIndices:
            dis = self.topo.distance(self.topo.nodes[u].loc, self.topo.nodes[v].loc)
            probability = math.exp(-self.topo.alpha * dis)
            m.addConstr(quicksum(f[i, u, v] + f[i, v, u] for i in range(numOfSDpairs)) <= probability * x[u, v])

            capacity = self.edgeCapacity(self.topo.nodes[u], self.topo.nodes[v])
            m.addConstr(x[u, v] <= capacity)


        for (u, v) in notEdge:
            m.addConstr(x[u, v] == 0)               
            for i in range(numOfSDpairs):
                m.addConstr(f[i, u, v] == 0)

        for u in range(numOfNodes):
            edgeContainu = []
            for (n1, n2) in edgeIndices:
                if u in (n1, n2):
                    edgeContainu.append((n1, n2))
                    edgeContainu.append((n2, n1))
            m.addConstr(quicksum(x[n1, n2] for (n1, n2) in edgeContainu) <= max(0, self.topo.nodes[u].remainingQubits))

        m.optimize()

        for i in range(numOfSDpairs):
            SDpair = self.srcDstPairs[i]
            for edge in self.topo.edges:
                u = edge[0]
                v = edge[1]
                varName = self.genNameByComma('f', [i, u.id, v.id])
                self.fi_LP[SDpair][(u, v)] = m.getVarByName(varName).x

            for edge in self.topo.edges:
                u = edge[1]
                v = edge[0]
                varName = self.genNameByComma('f', [i, u.id, v.id])
                self.fi_LP[SDpair][(u, v)] = m.getVarByName(varName).x

            for (u, v) in notEdge:
                u = self.topo.nodes[u]
                v = self.topo.nodes[v]
                self.fi_LP[SDpair][(u, v)] = 0
            
            
            varName = self.genNameByComma('t', [i])
            self.ti_LP[SDpair] = m.getVarByName(varName).x
        print("[ " + self.name + " ]", "LP1 end")

    def edgeCapacity(self, u, v):
        capacity = 0
        for link in u.links:
            if link.contains(v) and self.isBind[link] == False:
                capacity += 1
        used = 0
        for SDpair in self.srcDstPairs:
            used += self.fi[SDpair][(u, v)]
            used += self.fi[SDpair][(v, u)]

        return capacity - used

    def widthForSort(self, path):
        # path[-1] is the path of weight
        return -path[-1]
    

    def findAllLinkContains(self, u: Node, v: Node):
        links = []
        for link in u.links:
            if link.contains(v):
                links.append(link)

        return links
    
    def PFT(self): # find path for request

        # initialize fi and ti
        self.fi = {SDpair : {} for SDpair in self.srcDstPairs}
        self.ti = {SDpair : 0 for SDpair in self.srcDstPairs}

        for SDpair in self.srcDstPairs:
            for u in self.topo.nodes:
                for v in self.topo.nodes:
                    self.fi[SDpair][(u, v)] = 0
        
        # PFT
        failedFindPath = False
        while not failedFindPath:
            self.LP1()
            failedFindPath = True
            Pi = {}
            paths = []
            for SDpair in self.srcDstPairs:
                # return paths for SDpair, path[-1] = width
                Pi[SDpair] = self.findPathsForPFT(SDpair) 

            for SDpair in self.srcDstPairs:
                K = len(Pi[SDpair])
                # update resource
                for k in range(K):
                    width = math.floor(Pi[SDpair][k][-1])
                    Pi[SDpair][k][-1] -= width
                    paths.append(Pi[SDpair][k])
                    pathLen = len(Pi[SDpair][k]) - 1
                    self.ti[SDpair] += width
                    if width == 0:
                        continue
                    failedFindPath = False
                    for nodeIndex in range(pathLen - 1):
                        node = Pi[SDpair][k][nodeIndex]
                        next = Pi[SDpair][k][nodeIndex + 1]
                        self.fi[SDpair][(node, next)] += width

                    
                    # request find a path
                    for _ in range(width):
                        pathForRequest = Path()
                        for nodeIndex in range(pathLen):
                            node = Pi[SDpair][k][nodeIndex]
                            pathForRequest.nodes.append(node)

                        request = self.SDpairToRequest[SDpair]
                        request.paths.append(pathForRequest)

            paths = sorted(paths, key = self.widthForSort)

            for path in paths:
                pathLen = len(path) - 1
                width = path[-1]
                SDpair = (path[0], path[-2])
                isable = True
                for nodeIndex in range(pathLen - 1):
                    node = path[nodeIndex]
                    next = path[nodeIndex + 1]
                    if self.edgeCapacity(node, next) < 1:
                        isable = False
                
                if not isable:
                    continue
                
                failedFindPath = False
                self.ti[SDpair] += 1
                for nodeIndex in range(pathLen - 1):
                    node = path[nodeIndex]
                    next = path[nodeIndex + 1]
                    self.fi[SDpair][(node, next)] += 1

                # request find a path
                pathForRequest = Path()
                for nodeIndex in range(pathLen):
                    node = path[nodeIndex]
                    pathForRequest.nodes.append(node)

                request = self.SDpairToRequest[SDpair]
                request.paths.append(pathForRequest)

        for SDpair in self.srcDstPairs:
            request = self.SDpairToRequest[SDpair]
            removePaths = []

            for path in request.paths:
                # check there is resource for this path
                hasResource = True
                if path.nodes[0].remainingQubits < 1 or path.nodes[-1].remainingQubits < 1:
                    hasResource = False

                for nodeIndex in range(1, len(path.nodes) - 1):
                    if path.nodes[nodeIndex].remainingQubits < 2:
                        hasResource = False
                
                if not hasResource:
                    removePaths.append(path)
                    continue

                path.setStatus()
                request.needFindPath = False
                for nodeIndex in range(len(path.nodes) - 1):
                    node = path.nodes[nodeIndex]
                    next = path.nodes[nodeIndex + 1]
                    targetLinks = self.findAllLinkContains(node, next)
                    for link in targetLinks:
                        if not self.isBind[link]:
                            path.links.append(link)
                            link.assignQubits()
                            self.result.usedQubits += 2
                            self.isBind[link] = True
                            break
        
            for path in removePaths:
                request.paths.remove(path)

            for pathIndex in range(len(request.paths)):
                path = request.paths[pathIndex]

        print("[ " + self.name + " ]", "PFT end")

    def findPathsForPFT(self, SDpair):
        src = SDpair[0]
        dst = SDpair[1]
        pathList = []

        while self.DijkstraForPFT(SDpair):
            path = []
            currentNode = dst
            while currentNode != self.topo.sentinel:
                path.append(currentNode)
                currentNode = self.parent[currentNode]

            path = path[::-1]
            width = self.widthForPFT(path, SDpair)
            
            for i in range(len(path) - 1):
                node = path[i]
                next = path[i + 1]
                self.fi_LP[SDpair][(node, next)] -= width

            path.append(width)
            pathList.append(path.copy())

        return pathList
    def DijkstraForPFT(self, SDpair):
        src = SDpair[0]
        dst = SDpair[1]
        self.parent = {node : self.topo.sentinel for node in self.topo.nodes}
        adjcentList = {node : set() for node in self.topo.nodes}
        for node in self.topo.nodes:
            for link in node.links:
                if not self.isBind[link]:
                    neighbor = link.theOtherEndOf(node)
                    adjcentList[node].add(neighbor)
        
        distance = {node : 0 for node in self.topo.nodes}
        visited = {node : False for node in self.topo.nodes}
        pq = PriorityQueue()

        pq.put((-math.inf, src.id))
        while not pq.empty():
            (dist, uid) = pq.get()
            u = self.topo.nodes[uid]
            if visited[u]:
                continue

            if u == dst:
                return True
            distance[u] = -dist
            visited[u] = True
            
            for next in adjcentList[u]:
                newDistance = min(distance[u], self.fi_LP[SDpair][(u, next)])
                if distance[next] < newDistance:
                    distance[next] = newDistance
                    self.parent[next] = u
                    pq.put((-distance[next], next.id))

        return False

    def widthForPFT(self, path, SDpair):
        numOfnodes = len(path)
        width = math.inf
        for i in range(numOfnodes - 1):
            currentNode = path[i]
            nextNode = path[i + 1]
            width = min(width, self.fi_LP[SDpair][(currentNode, nextNode)])
        return width
if __name__ == '__main__':
    
    topo = Topo.generate(100, 0.9, 2, 0.002, 6, 0.25, 15)
    s = REPS(topo)
    result = AlgorithmResult()
    SDpairPerTime = 1
    ttime = 200
    rtime = 5
    requests = {i : [] for i in range(ttime)}

    for i in range(rtime):
        a = sample(topo.nodes, SDpairPerTime * 2)
        for n in range(0, SDpairPerTime * 2, 2):
            requests[i].append((a[n], a[n+1]))
    
    for i in range(ttime):
        result = s.work(requests[i], i)
    

    print(result.waitingTime, result.numOfTimeslot)