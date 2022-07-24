import random
from random import sample
import math
import sys
sys.path.append("..")
from AlgorithmBase import AlgorithmBase
from AlgorithmBase import PickedPath
from topo.Topo import Topo 
from topo.Node import Node 
from topo.Link import Link


class Request:

    def __init__(self, state):
        state: int          # 0 代表src直接送到dst, 1 代表src送到K, 2 代表k送到dst
        intermediate: Node  # 中繼點 k
        pathlen: int        
        path: list     
        taken : bool        # 是否可處理這個req (已預定資源)
        savetime : int      # req存在中繼點k 還沒送出去經過的時間
        width : int         # seg1 用過的 links

class MyAlgorithm(AlgorithmBase):

    def __init__(self, topo):
        super().__init__(topo)
        self.pathsSortedDynamically = []
        self.name = "My"
        self.givenShortestPath = {}     # {(src, dst): path, ...}               path表
        self.requestState = {}          # {(src, dst, timeslot) : RequestInfo}  request表 
        self.factorialTable = {}        # 階層運算表
        self.expectTable = {}           # {(path1, path2) : expectRound}        expectRound表

        self.totalTime = 0
        self.totalUsedQubits = 0
        self.takeTemporary = 0          # 選擇分段的request數量
        self.totalNumOfReq = 0          # 總request數量

   
    # p1
    def descideSegmentation(self):
        nodeRemainingQubits = {node: node.remainingQubits for node in self.topo.nodes}

        # 在前面回合 要拆成2段 但送失敗(還在src) 先把預定的bit扣掉 
        for req in self.requestState:
            if self.requestState[req].state == 1:
                k = self.requestState[req].intermediate
                nodeRemainingQubits[k] -= 1
            
        # 針對新的req 決定要不要拆
        for req in self.srcDstPairs:
            src, dst = req[0], req[1]
            path_sd = self.givenShortestPath[(src, dst)]
            self.requestState[(src, dst, self.timeSlot)] = Request(0, None, len(path_sd), path_sd, None, False, 0, 0)
            P_sd = self.Pr(self.givenShortestPath[(src, dst)])
            minNum = 1 / P_sd
            # print('minNum:', minNum)
            
            for k in self.socialRelationship[src]:
                if nodeRemainingQubits[k] <= 1 or k == dst or self.r < 1:
                    continue
                path_sk = self.givenShortestPath[(src, k)]
                path_kd = self.givenShortestPath[(k, dst)]
                expectKey = ((src, k), (k, dst))

                if expectKey in self.expectTable:
                    curMin = self.expectTable[expectKey]
                    print('[MyAlgo] get from table')
                else:
                    P_sk = self.Pr(path_sk)
                    P_kd = self.Pr(path_kd)
                    curMin = self.expectedRound(P_sk, P_kd)
                    self.expectTable[expectKey] = curMin

                # print('curMin:', curMin)
                if minNum > curMin:    # 分2段 取k中間  
                    minNum = curMin
                    self.requestState[(src, dst, self.timeSlot)] = Request(1, k, len(path_sk), path_sk, path_kd, False, 0, 0)

            # 模擬用掉這個k的一個Qubits 紀錄剩下的數量
            k = self.requestState[(src, dst, self.timeSlot)].intermediate
            if k == None: continue
            nodeRemainingQubits[k] -= 1
            self.takeTemporary += 1
        
        self.totalNumOfReq += len(self.srcDstPairs)
        self.result.temporaryRatio = self.takeTemporary / self.totalNumOfReq

    def prepare(self):
        self.requestState.clear()
        self.totalTime = 0
    
    # p2 第2次篩選
    def p2Extra(self):

        while True:
            found = False

            for req in self.requestState:
                requestInfo = self.requestState[req]

                if requestInfo.state == 0: 
                    src, dst = req[0], req[1]
                elif requestInfo.state == 1:
                    src, dst = req[0], requestInfo.intermediate
                elif requestInfo.state == 2:
                    src, dst = requestInfo.intermediate, req[1]

                if not requestInfo.taken:
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

                    if requestInfo.state == 1:
                        self.totalUsedQubits += 1
                        dst.assignIntermediate()
                    
                    if requestInfo.state == 2:
                        requestInfo.pathseg2 = p
                    else:
                        requestInfo.pathseg1 = p
                    requestInfo.taken= True
                    
                    found = True
                    print('[MyAlgo] P2Extra take')

                elif requestInfo.taken:
                    if src.remainingQubits < 1:
                        continue
                    
                    if requestInfo.state == 2:
                        p = requestInfo.pathseg2
                    else:
                        p = requestInfo.pathseg1
                    
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

                    requestInfo.width += 1
                    found = True
            # for end
            if not found:
                break
        # while end

    def resetFailedRequestFor1(self, requestInfo, usedLinks):      # 第一段傳失敗
        # for link in usedLinks:
        #     link.clearPhase4Swap()
        
        requestInfo.taken = False
        requestInfo.width = 0
        if requestInfo.state == 1:
            requestInfo.intermediate.clearIntermediate()

        for link in usedLinks:
            link.clearEntanglement()
        
    def resetFailedRequestFor2(self, requestInfo, usedLinks):       # 第二段傳失敗 且超時
        requestInfo.savetime = 0
        requestInfo.state = 1
        requestInfo.pathlen = len(requestInfo.pathseg1)
        requestInfo.intermediate.clearIntermediate()
        requestInfo.width = 0
        requestInfo.taken = False # 這邊可能有問題 重新分配資源

        # 第二段的資源全部釋放
        for link in usedLinks:
            link.clearEntanglement()    
    
    def resetSucceedRequestFor1(self, requestInfo, usedLinks):      # 第一段傳成功
        requestInfo.state = 2
        requestInfo.pathlen = len(requestInfo.pathseg2)
        requestInfo.taken = False                           # 這邊可能有問題 重新分配資源
        requestInfo.width = 0
        # requestInfo.linkseg1 = usedLinks                  # 紀錄seg1用了哪些link seg2成功要釋放資源

        # 第一段的資源還是預留的 只是清掉entangled跟swap
        for link in usedLinks:      
            link.clearEntanglement()

    def resetSucceedRequestFor2(self, requestInfo, usedLinks):      # 第二段傳成功 
        # 資源全部釋放
        requestInfo.intermediate.clearIntermediate()
        for link in usedLinks:
            link.clearEntanglement()
        # for link in requestInfo.linkseg1: 
        #     link.clearEntanglement()

    # p1 & p2    
    def p2(self):

        # p1
        self.descideSegmentation()

        # 根據path長度排序 
        # state2 > state1, timeslot, path長度
        sorted(self.requestState.items(), key=lambda x: (-x[1].state, x[0][2], x[1].pathlen))
        self.requestState = dict(self.requestState)

        if len(self.requestState) > 0:
            self.result.numOfTimeslot += 1

        # p2 (1)
        for req in self.requestState:
            requestInfo = self.requestState[req]
            if requestInfo.taken == True:   # 被選過了 可能是上一輪失敗的 已經配好資源了
                continue

            if requestInfo.state == 0:      # 0
                src, dst = req[0], req[1]
            elif requestInfo.state == 1:    # 1
                src, dst = req[0], requestInfo.intermediate
            elif requestInfo.state == 2:    # 2
                src, dst = requestInfo.intermediate, req[1]

            # 檢查path node Qubit資源
            path = self.givenShortestPath[(src, dst)]
            unavaliable = False
            for n in path:
                if ((n == src or n == dst) and n.remainingQubits < 1) or \
                    (requestInfo.state == 1 and n == src and n.remainingQubits < 1) or \
                    (requestInfo.state == 1 and n == dst and n.remainingQubits < 2) or \
                    (requestInfo.state == 2 and n == src and n.remainingQubits < 1) or \
                    (requestInfo.state == 2 and n == dst and n.remainingQubits < 1) or \
                    ((n != src and n != dst) and n.remainingQubits < 2):             
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
            if requestInfo.state == 1:
                self.totalUsedQubits += 1
                dst.assignIntermediate()
            
            # take這個request
            if requestInfo.state == 2:
                requestInfo.pathseg2 = path
            else:
                requestInfo.pathseg1 = path
            requestInfo.taken= True
            requestInfo.width = 1
        
        # p2 繼續找路徑分配資源 
        self.p2Extra()


        for req in self.requestState:
            requestInfo = self.requestState[req]
            if requestInfo.taken == False:
                self.result.idleTime += 1

    # p4 & p5
    def p4(self):
        
        sorted(self.requestState, key=lambda q: q[2])
        finishedRequest = []
        # p4
        for req in self.requestState:
            requestInfo = self.requestState[req]
            if not requestInfo.taken:
                continue
            print('----------------------')
            print('request information')
            print('----------------------')
            print('src:', req[0].id, 'dst:', req[1].id, 'time:', self.timeSlot)
            
            # swap
            if requestInfo.state == 2:
                p = requestInfo.pathseg2
            else:
                p = requestInfo.pathseg1

            width = requestInfo.width
            usedLinks = set()
            # oldNumOfPairs = len(self.topo.getEstablishedEntanglements(p[0], p[-1]))

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

            print('----------------------')
            print('[MyAlgo] success:', success)
            print('[MyAlgo] state:', requestInfo.state)
            p2 = self.givenShortestPath[(req[0],req[1])]
            print('[MyAlgo] original path:', [x.id for x in p2])
            print('[MyAlgo] path:', [x.id for x in p])

            # failed
            if success == 0 and len(p) != 2:
                if requestInfo.state == 0 or requestInfo.state == 1:    # 0, 1
                    self.resetFailedRequestFor1(requestInfo, usedLinks)
                elif requestInfo.state == 2:                            # 2
                    requestInfo.savetime += 1
                    if requestInfo.savetime > self.r:   # 超出k儲存時間 重頭送 重設req狀態
                        self.resetFailedRequestFor2(requestInfo, usedLinks)
                    else:
                        self.resetFailedRequestFor1(requestInfo, usedLinks)
                continue
            
            # succeed
            if success > 0 or len(p) == 2:
                if requestInfo.state == 0:      # 0
                    self.totalTime += self.timeSlot - req[2]
                    finishedRequest.append(req)
                    for link in usedLinks:
                        link.clearEntanglement()
                elif requestInfo.state == 1:    # 1
                    self.resetSucceedRequestFor1(requestInfo, usedLinks)
                elif requestInfo.state == 2:    # 2
                    self.resetSucceedRequestFor2(requestInfo, usedLinks)
                    self.totalTime += self.timeSlot - req[2]
                    finishedRequest.append(req)
                continue
            # p5 end
        # p4 end

        for req in finishedRequest:
            self.requestState.pop(req)
        self.srcDstPairs.clear()

        remainTime = 0
        for req in self.requestState:
            # self.result.unfinishedRequest += 1
            remainTime += self.timeSlot - req[2]

        self.topo.clearAllEntanglements()
        self.result.remainRequestPerRound.append(len(self.requestState)/self.totalNumOfReq)  
        self.result.waitingTime = (self.totalTime + remainTime) / self.totalNumOfReq + 1
        self.result.usedQubits = self.totalUsedQubits / self.totalNumOfReq

        print('[MyAlgo] waiting time:',  self.result.waitingTime)
        print('[MyAlgo] idle time:', self.result.idleTime)
        print('[MyAlgo] remaining request:', len(self.requestState))
        print('[MyAlgo] p5 end')


        return self.result
    
if __name__ == '__main__':

    topo = Topo.generate(100, 0.9, 5, 0.0001, 6)
    # s = MyAlgorithm(topo)

    # for i in range(0, 200):
    #     requests = []
    #     if i < 1:
    #         for j in range(10):
    #             a = sample(topo.nodes, 2)
    #             requests.append((a[0], a[1]))
    #         s.work(requests, i)
    #     else:
    #         s.work([], i)


 