from random import sample
import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase
from AlgorithmBase import PickedPath
from GreedyHopRouting import GreedyHopRouting
from OnlineAlgorithm import OnlineAlgorithm
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link

class Request:

    def __init__(self, src, dst, time):
        self.src = src
        self.dst = dst
        self.time = time
        self.state = 0  # 0:init / 1:non-seg / 2:predating / 3:postdating
        self.storageTime = 0
        self.intermediate = None
        self.path1 = Path()
        self.path2 = Path()
        self.paths = []
        self.pathlen = 0

class Path:

    def __init__(self):
        self.path = []

class MyAlgorithm(AlgorithmBase):

    def __init__(self, topo):
        super().__init__(topo)
        self.name = "SEER"
        self.pathsSortedDynamically = []
        self.r = 7                     # 暫存回合
        self.requests = []  
        self.totalTime = 0
        self.totalUsedQubits = 0
        self.takeTemporary = 0         # 選擇分段的request數量
        self.totalNumOfReq = 0         # 總request數量
        
    # p1
    def descideSegmentation(self):
        nodeRemainingQubits = {node: node.remainingQubits for node in self.topo.nodes}
   
        # 在前面回合 要拆成2段 但送失敗(還在src) 先把預定的bit扣掉 
        for req in self.requests:
            if req.state == 2:
                k = req.intermediate
                nodeRemainingQubits[k] -= 1 
        
        # 加入新的request到request set
        for req in self.srcDstPairs:
            src, dst = req[0], req[1]
            time = self.timeSlot
            request = Request(src, dst, time)
            self.requests.append(request)

        # 對 state = 0 的request決定要不要分段 
        for req in self.requests:
            if req.state != 0:
                continue

            src, dst = req.src, req.dst
            path_sd = Path()
            path_sd.path = self.topo.shortestPathTable[(src, dst)][0]
            req.state = 1
            req.path1 = path_sd
            req.intermediate = None
            req.pathlen = len(path_sd.path)

            P_sd = self.topo.shortestPathTable[(src, dst)][2]
            minNum = 1 / P_sd

            # 歷遍k
            for k in self.topo.socialRelationship[src]:
                if nodeRemainingQubits[k] <= 1 or k == dst or self.r < 1:
                    continue
                path_sk = Path()
                path_kd = Path()
                path_sk.path = self.topo.shortestPathTable[(src, k)][0]
                path_kd.path = self.topo.shortestPathTable[(k, dst)][0]
                expectKey = ((src, k), (k, dst))

                if expectKey in self.topo.expectTable:
                    curMin = self.topo.expectTable[expectKey]

                # 分段期望效果更好，紀錄如何分段 
                if minNum > curMin:    
                    minNum = curMin
                    req.state = 2
                    req.path1 = path_sk
                    req.path2 = path_kd
                    req.intermediate = k
                    req.pathlen = len(path_sk.path)

            # 模擬用掉這個k的一個Qubits 紀錄剩下的數量
            k = req.intermediate
            if k == None: continue
            nodeRemainingQubits[k] -= 1
            self.takeTemporary += 1

        self.totalNumOfReq += len(self.srcDstPairs)
        self.result.temporaryRatio = self.takeTemporary / self.totalNumOfReq

    def prepare(self):
        self.requests.clear()
        self.totalTime = 0
        self.topo.genShortestPathTable("Hop")
        self.topo.genExpectTable()
    
    # p2 榨乾資源 找multipath
    def p2Extra(self):

        while True:
            found = False

            for req in self.requests:

                if req.state == 1: 
                    src, dst = req.src, req.dst
                    path = req.path1
                elif req.state == 2:
                    src, dst = req.src, req.intermediate
                    path = req.path1
                elif req.state == 3:
                    src, dst = req.intermediate, req.dst
                    path = req.path2
                else:
                    continue
                
                w = self.topo.widthPhase2(path.path)

                # 決定路徑 
                if w > 0:   # 預找的路徑資源夠
                    P = Path()
                    p = path.path
                else:       # 預找的路徑資源不夠，另外找
                    if src.remainingQubits < 1:
                        continue

                    P = Path()
                    p = []
                    p.append(src)
                    
                    # Find a shortest path by greedy min hop  
                    while True:
                        last = p[-1]
                        if last == dst:
                            break

                        # Select avaliable neighbors of last(local)
                        selectedNeighbors = []    # type Node
                        selectedNeighbors.clear()
                        for neighbor in last.neighbors:
                            if neighbor.remainingQubits > 2 or neighbor == dst and neighbor.remainingQubits > 1:
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
                            if hopsCurMinNum > hopsNum:
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
                # if end

                # Assign Qubits for links in path     
                for i in range(0, len(p) - 1):
                    n1 = p[i]
                    n2 = p[i+1]
                    for link in n1.links:
                        if link.contains(n2) and (not link.assigned):
                            self.totalUsedQubits += 2
                            link.assignQubits()
                            break 
               
                P.path = p
                req.paths.append(P) 
                found = True
            # for end

            if not found:
                break
        # while end

    # p1 & p2    
    def p2(self):

        # p1
        self.descideSegmentation()

        # state2 > state1, timeslot, pathlen
        self.requests = sorted(self.requests, key=lambda x: (-x.state, x.time, x.pathlen))

        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1
     
        # p2 
        for req in self.requests:
         
            if len(req.paths) != 0:   # 有1個path並分配資源了
                continue
            
            if req.state == 1:      # 1
                src, dst = req.src, req.dst
                path = req.path1
            elif req.state == 2:    # 2
                src, dst = req.src, req.intermediate
                path = req.path1
            elif req.state == 3:    # 3
                src, dst = req.intermediate, req.dst
                path = req.path2
            else:   # 0
                continue

            # 檢查path node Qubit資源
            unavaliable = False
            p = path.path
            for n in p:
                if ((n == src or n == dst) and n.remainingQubits < 1) or ((n != src and n != dst) and n.remainingQubits < 2):             
                    unavaliable = True

            # 檢查link資源
            for i in range(0, len(p) - 1):
                n1 = p[i]
                n2 = p[i+1]
                pick = False
                for link in n1.links:
                    if link.contains(n2) and (not link.assigned):
                        pick = True
                        continue

                if not pick:
                    unavaliable = True  
            
            # 資源不夠 先跳過
            if unavaliable:
                continue

            # 分配資源給path
            for i in range(0, len(p) - 1):
                n1 = p[i]
                n2 = p[i+1]
                for link in n1.links:
                    if link.contains(n2) and (not link.assigned):
                        self.totalUsedQubits += 2
                        link.assignQubits()
                        break 

            # 把path加入進來
            req.paths.append(path)

            # req.taken= True
            req.width = 1
        
        # p2 找multipath
        self.p2Extra()

        for req in self.requests:
            if len(req.paths) == 0:
                self.result.idleTime += 1

    # p4 & p5
    def p4(self):
        
        finishedRequest = []
        # p4
        for req in self.requests:
            
            if len(req.paths) <= 0:
                continue

            if req.state == 1: 
                src, dst = req.src, req.dst
            elif req.state == 2:
                src, dst = req.src, req.intermediate
            elif req.state == 3:
                src, dst = req.intermediate, req.dst
            else:
                continue
            
            # swapped
            for path in req.paths:
                p = path.path
                usedLinks = set()
                for i in range(1, len(p) - 1):
                    prev = p[i-1]
                    curr = p[i]
                    next = p[i+1]
                    prevLinks = []
                    nextLinks = []
                    
                    for link in curr.links:
                        if link.entangled and (link.n1 == prev and not link.s2 or link.n2 == prev and not link.s1):
                            prevLinks.append(link)

                    for link in curr.links:
                        if link.entangled and (link.n1 == next and not link.s2 or link.n2 == next and not link.s1):
                            nextLinks.append(link)

                    if len(prevLinks) == 0 or len(nextLinks) == 0:
                        break

                    for (l1, l2) in zip(prevLinks, nextLinks):
                        usedLinks.add(l1)
                        usedLinks.add(l2)
                        curr.attemptSwapping(l1, l2)
                
                if len(p) == 2:
                    prev = p[0]
                    curr = p[1]
                    for link in prev.links:
                        if link.entangled and (link.n1 == prev and not link.s2 or link.n2 == prev and not link.s1):
                            usedLinks.add(link)
                            break
         
            success = len(self.topo.getEstablishedEntanglements(src, dst))

            # succeed
            if success > 0 or len(p) == 2:
                if req.state == 1:
                    finishedRequest.append(req)
                elif req.state == 3:
                    finishedRequest.append(req)
                    req.intermediate.clearIntermediate()
                else:
                    req.state = 3
                    req.intermediate.assignIntermediate()
                    req.pathlen = len(req.path2.path)
        # p4 end

        # 移除完成的request 
        for req in finishedRequest:
            self.totalTime += self.timeSlot - req.time
            self.requests.remove(req)

        # 更新未完成request狀態
        for req in self.requests:
            req.paths.clear()

            if req.state != 3:
                continue
            
            req.storageTime += 1

            # 超時的話，重設req
            if req.storageTime > self.r:
                req.intermediate.clearIntermediate()
                req.state = 0
                req.storageTime = 0

        remainTime = 0
        for req in self.requests:
            remainTime += self.timeSlot - req.time

        self.topo.clearAllEntanglements()   # 重設所有link狀態
        self.result.remainRequestPerRound.append(len(self.requests)/self.totalNumOfReq)  
        self.result.waitingTime = (self.totalTime + remainTime) / self.totalNumOfReq + 1
        self.result.usedQubits = self.totalUsedQubits / self.totalNumOfReq

        print('[', self.name, '] waiting time:', self.result.waitingTime)
        print('[', self.name, '] idle time:', self.result.idleTime)
        print('[', self.name, '] p4 end')

        return self.result
    
if __name__ == '__main__':

    topo = Topo.generate(30, 0.9, 1, 0.0008, 6, 0.5, 15)

    a1 = MyAlgorithm(topo)
    a2 = GreedyHopRouting(topo)
    a3 = OnlineAlgorithm(topo)

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
            node.remainingQubits += memory[node.id]-node.remainingQubits

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

