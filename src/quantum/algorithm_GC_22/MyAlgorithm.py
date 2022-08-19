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
        self.state = 0
        self.storageTime = 0
        self.intermediate = None
        self.path1 = []
        self.path2 = []
        self.pathlen = 0
        self.width = 0
        self.taken = False

class MyAlgorithm(AlgorithmBase):

    def __init__(self, topo):
        super().__init__(topo)
        self.pathsSortedDynamically = []
        self.name = "My"
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
            if req.state == 1:
                k = req.intermediate
                nodeRemainingQubits[k] -= 1 
           
        # 針對新的req 決定要不要拆
        for req in self.srcDstPairs:
            src, dst = req[0], req[1]
            path_sd = self.topo.shortestPathTable[(src, dst)][0]
            request = Request(src, dst, self.timeSlot)
            request.path1 = path_sd

            P_sd = self.topo.shortestPathTable[(src, dst)][2]
            minNum = 1 / P_sd

            for k in self.topo.socialRelationship[src]:
                if nodeRemainingQubits[k] <= 1 or k == dst or self.r < 1:
                    continue
                path_sk = self.topo.shortestPathTable[(src, k)][0]
                path_kd = self.topo.shortestPathTable[(k, dst)][0]
                expectKey = ((src, k), (k, dst))

                if expectKey in self.topo.expectTable:
                    curMin = self.topo.expectTable[expectKey]

                # print('curMin:', curMin)
                if minNum > curMin:    # 分2段 取k中間  
                    minNum = curMin
                    request.state = 1
                    request.path1 = path_sk
                    request.path2 = path_kd
                    request.intermediate = k
                    request.pathlen = len(path_sk)

            self.requests.append(request)

            # 模擬用掉這個k的一個Qubits 紀錄剩下的數量
            k = request.intermediate
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
    
    # p2 第2次篩選
    def p2Extra(self):

        while True:
            found = False

            for req in self.requests:

                if req.state == 0: 
                    src, dst = req.src, req.dst
                elif req.state == 1:
                    src, dst = req.src, req.intermediate
                elif req.state == 2:
                    src, dst = req.intermediate, req.dst

                if not req.taken:
                    if src.remainingQubits < 1:
                        continue
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
                    
                    # Assign Qubits for links in path     
                    for i in range(0, len(p) - 1):
                        n1 = p[i]
                        n2 = p[i+1]
                        for link in n1.links:
                            if link.contains(n2) and (not link.assigned):
                                self.totalUsedQubits += 2
                                link.assignQubits()
                                break 

                    if req.state == 1:
                        self.totalUsedQubits += 1
                        dst.assignIntermediate()
                    
                    if req.state == 2:
                        req.path2 = p
                    else:
                        req.path1 = p
                    req.taken= True
                    
                    found = True
                    # print('[MyAlgo] P2Extra take')

                elif req.taken: # 有路徑 然後加粗
                    if src.remainingQubits < 1:
                        continue
                    
                    if req.state == 2:
                        p = req.path2
                    else:
                        p = req.path1
                    
                    # 檢查資源
                    unavaliable = False
                    for n in p:
                        if ((n == src or n == dst) and n.remainingQubits < 1) or \
                            ((n != src and n != dst) and n.remainingQubits < 2):             
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

                    req.width += 1
                    found = True
            # for end
            if not found:
                break
        # while end

    def resetFailedRequestFor1(self, request, usedLinks):      # 第一段傳失敗
        # for link in usedLinks:
        #     link.clearPhase4Swap()
        
        request.taken = False
        request.width = 0
        if request.state == 1:
            request.intermediate.clearIntermediate()

        for link in usedLinks:
            link.clearEntanglement()
        
    def resetFailedRequestFor2(self, request, usedLinks):       # 第二段傳失敗 且超時
        request.storageTime = 0
        request.state = 1
        request.pathlen = len(request.path1)
        request.intermediate.clearIntermediate()
        request.width = 0
        request.taken = False # 這邊可能有問題 重新分配資源

        # 第二段的資源全部釋放
        for link in usedLinks:
            link.clearEntanglement()    
    
    def resetSucceedRequestFor1(self, request, usedLinks):      # 第一段傳成功
        request.state = 2
        request.pathlen = len(request.path2)
        request.taken = False                           # 這邊可能有問題 重新分配資源
        request.width = 0
        # requestInfo.linkseg1 = usedLinks                  # 紀錄seg1用了哪些link seg2成功要釋放資源

        # 第一段的資源還是預留的 只是清掉entangled跟swap
        for link in usedLinks:      
            link.clearEntanglement()

    def resetSucceedRequestFor2(self, request, usedLinks):      # 第二段傳成功 
        # 資源全部釋放
        request.intermediate.clearIntermediate()
        for link in usedLinks:
            link.clearEntanglement()

    # p1 & p2    
    def p2(self):

        # p1
        self.descideSegmentation()

        # state2 > state1, timeslot, pathlen
        self.requests = sorted(self.requests, key=lambda x: (-x.state, x.time, x.pathlen))

        if len(self.requests) > 0:
            self.result.numOfTimeslot += 1
     
        # p2 (1)
        for req in self.requests:
         
            if req.taken == True:   # 被選過了 可能是上一輪失敗的 已經配好資源了
                continue

            if req.state == 0:      # 0
                src, dst = req.src, req.dst
            elif req.state == 1:    # 1
                src, dst = req.src, req.intermediate
            elif req.state == 2:    # 2
                src, dst = req.intermediate, req.dst

            # 檢查path node Qubit資源
            path = self.topo.shortestPathTable[(src, dst)][0]
            unavaliable = False
            for n in path:
                if ((n == src or n == dst) and n.remainingQubits < 1) or ((n != src and n != dst) and n.remainingQubits < 2):             
                    unavaliable = True

            # 檢查link資源
            for i in range(0, len(path) - 1):
                n1 = path[i]
                n2 = path[i+1]
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
            for i in range(0, len(path) - 1):
                n1 = path[i]
                n2 = path[i+1]
                for link in n1.links:
                    if link.contains(n2) and (not link.assigned):
                        self.totalUsedQubits += 2
                        link.assignQubits()
                        break 

            # 有分段 另外分配資源給中繼點
            if req.state == 1:
                self.totalUsedQubits += 1
                dst.assignIntermediate()
            
            # take這個request
            if req.state == 2:
                req.path2 = path
            else:
                req.path1 = path

            req.taken= True
            req.width = 1
        
        # p2 繼續找路徑分配資源 
        self.p2Extra()

        for req in self.requests:
            if req.taken == False:
                self.result.idleTime += 1

    # p4 & p5
    def p4(self):
        
        finishedRequest = []
        # p4
        for req in self.requests:
            if not req.taken:
                continue
                   
            # swap
            if req.state == 2:
                p = req.path2
            else:
                p = req.path1

            width = req.width
            
            usedLinks = set()
            for i in range(1, len(p) - 1):
                prev = p[i-1]
                curr = p[i]
                next = p[i+1]
                prevLinks = []
                nextLinks = []
                
                w = width
                for link in curr.links:
                    if link.entangled and (link.n1 == prev and not link.s2 or link.n2 == prev and not link.s1) and w > 0:
                        prevLinks.append(link)
                        w -= 1

                w = width
                for link in curr.links:
                    if link.entangled and (link.n1 == next and not link.s2 or link.n2 == next and not link.s1) and w > 0:
                        nextLinks.append(link)
                        w -= 1

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
         
            # p5
            success = len(self.topo.getEstablishedEntanglements(p[0], p[-1]))

            # failed
            if success == 0 and len(p) != 2:
                if req.state == 0 or req.state == 1:    # 0, 1
                    self.resetFailedRequestFor1(req, usedLinks)
                elif req.state == 2:                            # 2
                    req.storageTime += 1
                    if req.storageTime > self.r:   # 超出k儲存時間 重頭送 重設req狀態
                        self.resetFailedRequestFor2(req, usedLinks)
                    else:
                        self.resetFailedRequestFor1(req, usedLinks)
                continue
            
            # succeed
            if success > 0 or len(p) == 2:
                if req.state == 0:      # 0
                    self.totalTime += self.timeSlot - req.time
                    finishedRequest.append(req)
                    for link in usedLinks:
                        link.clearEntanglement()
                elif req.state == 1:    # 1
                    self.resetSucceedRequestFor1(req, usedLinks)
                elif req.state == 2:    # 2
                    self.resetSucceedRequestFor2(req, usedLinks)
                    self.totalTime += self.timeSlot - req.time
                    finishedRequest.append(req)
                continue
            # p5 end
        # p4 end

        for req in finishedRequest:
            self.requests.remove(req)

        self.srcDstPairs.clear()

        remainTime = 0
        for req in self.requests:
            remainTime += self.timeSlot - req.time

        self.topo.clearAllEntanglements()
        self.result.remainRequestPerRound.append(len(self.requests)/self.totalNumOfReq)  
        self.result.waitingTime = (self.totalTime + remainTime) / self.totalNumOfReq + 1
        self.result.usedQubits = self.totalUsedQubits / self.totalNumOfReq

        print('[', self.name, '] waiting time:', self.result.waitingTime)
        print('[', self.name, '] idle time:', self.result.idleTime)
        print('[', self.name, '] p4 end')

        return self.result
    
if __name__ == '__main__':

    topo = Topo.generate(30, 0.9, 1, 0.003, 6, 0.5, 15)

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

