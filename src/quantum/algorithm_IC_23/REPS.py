import sys
import math
import random
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
        self.width = 0

class Request:
    def __init__(self, src, dst, index):
        self.src = src
        self.dst = dst
        self.index = index
        self.needFindPath = True
        self.currentTemp = (-1, -1) # [pathsIndex, nodesIndex]
        self.paths = []

class REPS(AlgorithmBase):
    def __init__(self, topo):
        super().__init__(topo)
        self.name = "REPS"
        self.requests = []
        self.isBind = {link : False for link in self.topo.links}
        self.totalRequest = 0
        self.totalUsedQubits = 0
        self.totalWaitingTime = 0

    def genNameByComma(self, varName, parName):
        return (varName + str(parName)).replace(' ', '')
    def genNameByBbracket(self, varName: str, parName: list):
        return (varName + str(parName)).replace(' ', '').replace(',', '][')
    
    def printResult(self):
        self.result.waitingTime = self.totalWaitingTime / self.totalRequest
        self.result.usedQubits = self.totalUsedQubits / self.totalRequest
        
        self.result.remainRequestPerRound.append(len(self.requests) / self.totalRequest)
        
        print("[REPS] total time:", self.result.waitingTime)
        print("[REPS] remain request:", len(self.requests))
        print("[REPS] current Timeslot:", self.timeSlot)

    def AddNewSDpairs(self):
        for (src, dst) in self.srcDstPairs:
            self.requests.append(Request(src, dst, self.totalRequest))
            self.totalRequest += 1

        self.srcDstPairs = []
        self.SDpairToRequest = {}
        for request in self.requests:
            if request.needFindPath:
                src = request.src
                dst = request.src
                if (src, dst) not in self.usedSDpair:
                    self.SDpairToRequest[(src, dst)] = request
                    self.srcDstPairs.append((src, dst))

    def p2(self):
        self.AddNewSDpairs()
        self.totalWaitingTime += len(self.requests)
        self.result.idleTime += len(self.requests)
        if len(self.srcDstPairs) > 0:
            self.PFT() # find path for request
        if len(self.requests) > 0:
            self.assignQubitsForBindLinks()
            self.result.numOfTimeslot += 1
        print('[REPS] p2 end')
    
    def p4(self):
        print('[REPS] p4 end') 
        self.forward()
        self.printResult()
        return self.result

    
    def assignQubitsForBindLinks(self):
        pass

    def forward(self):
        pass

    def LP1(self): # compute self.fi_LP
        print('[REPS] LP1 start')
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

        m = gp.Model('REPS for PFT')
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
            m.addConstr(quicksum(x[n1, n2] for (n1, n2) in edgeContainu) <= self.topo.nodes[u].remainingQubits)

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
        print('[REPS] LP1 end')

    def edgeCapacity(self, u, v):
        capacity = 0
        for link in u.links:
            if link.contains(v) and not self.isBind[link]:
                capacity += 1
        used = 0
        for SDpair in self.srcDstPairs:
            used += self.fi[SDpair][(u, v)]
            used += self.fi[SDpair][(v, u)]
        return capacity - used

    def widthForSort(self, path):
        # path[-1] is the path of weight
        return -path[-1]
    

    def findAllLinkContain(self, u: Node, v: Node):
        links = []
        for link in u.links:
            if link.contain(v):
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
                    pathForRequest = Path()
                    pathForRequest.width = width
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
                pathForRequest.width = 1
                for nodeIndex in range(pathLen):
                    node = path[nodeIndex]
                    pathForRequest.nodes.append(node)

                request = self.SDpairToRequest[SDpair]
                request.paths.append(pathForRequest)

        for SDpair in self.srcDstPairs:
            request = self.SDpairToRequest[SDpair]
            if len(request.paths) == 0:
                # request didn't find a path
                continue

            # a reqeust find paths
            request.needFindPath = False
            width = request.width
            for path in request:
                for nodeIndex in range(len(request.nodes) - 1):
                    node = request.nodes[nodeIndex]
                    next = request.nodes[nodeIndex + 1]
                    request.links.append([])
                    targetLinks = self.findAllLinkContain(node, next)
                    for link in targetLinks:
                        if not self.isBind[link]:
                            request.links[nodeIndex].append(link)
                            self.isBind[link] = True
                            if len(request.links[nodeIndex]) == width:
                                break
        print('[REPS] PFT end')
                    

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
if __name__ == '__main__':
    
    topo = Topo.generate(100, 0.9, 5, 0.0002, 6)
    s = REPS(topo)
    result = AlgorithmResult()
    samplesPerTime = 2
    ttime = 100
    rtime = 2
    requests = {i : [] for i in range(ttime)}

    for i in range(ttime):
        if i < rtime:
            a = sample(topo.nodes, samplesPerTime)
            for n in range(0,samplesPerTime,2):
                requests[i].append((a[n], a[n+1]))

    for i in range(ttime):
        result = s.work(requests[i], i)
    

    print(result.waitingTime, result.numOfTimeslot)