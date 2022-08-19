from dataclasses import dataclass
from time import process_time, sleep
import sys
import math
sys.path.append("..")
from topo.Topo import Topo  

class AlgorithmResult:
    def __init__(self):
        self.algorithmRuntime = 0
        self.waitingTime = 0
        self.idleTime = 0
        self.usedQubits = 0
        self.temporaryRatio = 0
        self.numOfTimeslot = 0
        self.totalRuntime = 0
        # ---
        self.secureThroughput = 0
        self.avgTimeSlotsForSecure = math.inf
        self.throuhgput = 0
        self.trustedRatioOnPath = 0
        self.secureRatio = 0
        self.avgTemporaryCount = 0
        self.numOfTimeOut = 0
        self.totalLenOfPath = 0
        self.totalTemporaryCount = 0
        self.totalNumOfIntermediate = 0
        # ----
        # self.Ylabels = ["algorithmRuntime", "waitingTime", "idleTime", "usedQubits", "temporaryRatio"]
        self.Ylabels = ["algorithmRuntime", "waitingTime", "idletime", "numOfTimeOut", "secureThroughput", "avgTimeSlotsForSecure", "throuhgput", "trustedRatioOnPath", "secureRatio", "avgTemporaryCount"]
        self.remainRequestPerRound = []

    def toDict(self):
        dic = {}
        dic[self.Ylabels[0]] = self.algorithmRuntime
        dic[self.Ylabels[1]] = self.waitingTime
        dic[self.Ylabels[2]] = self.idleTime
        dic[self.Ylabels[3]] = self.numOfTimeOut
        dic[self.Ylabels[4]] = self.secureThroughput
        dic[self.Ylabels[5]] = self.avgTimeSlotsForSecure
        dic[self.Ylabels[6]] = self.throuhgput
        dic[self.Ylabels[7]] = self.trustedRatioOnPath
        dic[self.Ylabels[8]] = self.secureRatio
        dic[self.Ylabels[9]] = self.avgTemporaryCount

        return dic
    
    def Avg(results: list):
        AvgResult = AlgorithmResult()
        AvgResult.avgTimeSlotsForSecure = 0

        ttime = 200
        AvgResult.remainRequestPerRound = [0 for _ in range(ttime)]
        for result in results:
            AvgResult.algorithmRuntime += result.algorithmRuntime
            AvgResult.waitingTime += result.waitingTime
            AvgResult.secureThroughput += result.secureThroughput
            AvgResult.avgTimeSlotsForSecure += result.avgTimeSlotsForSecure
            AvgResult.throuhgput += result.throuhgput
            AvgResult.trustedRatioOnPath += result.trustedRatioOnPath
            AvgResult.secureRatio += result.secureRatio
            AvgResult.avgTemporaryCount += result.avgTemporaryCount
            AvgResult.idleTime += result.idleTime
            AvgResult.numOfTimeOut += result.numOfTimeOut
            # AvgResult.usedQubits += result.usedQubits
            # AvgResult.temporaryRatio += result.temporaryRatio

            # Len = len(result.remainRequestPerRound)
            # if ttime != Len:
            #     print("the length of RRPR error:", Len, file = sys.stderr)
            
            # for i in range(ttime):
            #     AvgResult.remainRequestPerRound[i] += result.remainRequestPerRound[i]


        num = len(results)
        AvgResult.algorithmRuntime /= num
        AvgResult.waitingTime /= num
        AvgResult.secureThroughput /= num
        AvgResult.avgTimeSlotsForSecure /= num
        AvgResult.throuhgput /= num
        AvgResult.trustedRatioOnPath /= num
        AvgResult.secureRatio /= num
        AvgResult.avgTemporaryCount /= num
        AvgResult.idleTime /= num
        AvgResult.numOfTimeOut /= num
        # AvgResult.usedQubits /= len(results)
        # AvgResult.temporaryRatio /= len(results)

        # for i in range(ttime):
        #     AvgResult.remainRequestPerRound[i] /= len(results)
            
        return AvgResult

class AlgorithmBase:

    def __init__(self, topo):
        self.name = "Base"
        self.topo = topo
        self.srcDstPairs = []
        self.timeSlot = 0
        self.result = AlgorithmResult()
        self.canEntangled = True
        self.totalNumOfReq = 0  # total number of requests
        self.totalNumOfFinishedReq = 0 # total number of finished requests
        self.totalNumOfBrokenReq = 0    # total number of peeping requests
        self.totalNumOfSecureReq = 0    # total number of secure requests
        self.totalNumOfIntermediate = 0 # total number of intermediates
        self.totalNumOfNormalNodeOnPath = 0 # total number of normal nodes
        self.totalNumOfTemporary = 0 # total number of temporary counts
        self.idleTime = 0   # total idle time
        self.numOfTimeOut = 0   # total timeout
        self.doubleEntangled = ["My", "QCAST_SOPP", "Greedy_SOPP", "REPS_SOPP", "test", "test2"]
        self.doubleSwapped = ["My", "QCAST_SOPP", "Greedy_SOPP", "REPS_SOPP", "Greedy", "QCAST", "REPS", "test", "test2"]
        
    def prepare(self):
        pass
    
    def p2(self):
        pass

    def p4(self):
        pass

    def trySwapped(self):
        pass

    def tryEntanglement(self):
        for link in self.topo.links:
            link.tryEntanglement()
    
    def modifyResult(self, res):

        # res.totalRuntime += (end - start)
        # res.algorithmRuntime = res.totalRuntime / res.numOfTimeslot

        res.secureThroughput = self.totalNumOfSecureReq / res.numOfTimeslot
        if res.secureThroughput > 0:
            res.avgTimeSlotsForSecure = self.totalNumOfReq / res.secureThroughput

        res.throuhgput = self.totalNumOfFinishedReq / res.numOfTimeslot

        if self.totalNumOfNormalNodeOnPath > 0:
            res.trustedRatioOnPath = self.totalNumOfIntermediate / self.totalNumOfNormalNodeOnPath

        if self.totalNumOfFinishedReq > 0:
            res.secureRatio = self.totalNumOfSecureReq / self.totalNumOfFinishedReq
        
        if self.totalNumOfReq > 0:
            res.idleTime = self.idleTime / self.totalNumOfReq
            res.avgTemporaryCount = self.totalNumOfTemporary / self.totalNumOfReq
        

        print("[", self.name, "]", "trusedRatioOnPath = ", res.trustedRatioOnPath)
        print("[", self.name, "]", "avgTimeSlotsForSecure = ", res.avgTimeSlotsForSecure)
        print("[", self.name, "]", "secureThroughput = ", res.secureThroughput)
        print("[", self.name, "]", "throuhgput = ", res.throuhgput)
        print("[", self.name, "]", "secureRatio = ", res.secureRatio)
        print("[", self.name, "]", "avgTemporaryCount = ", res.avgTemporaryCount)
    
        return res

    def work(self, pairs: list, time): 

        self.timeSlot = time    # Update current time
        self.srcDstPairs.extend(pairs) # Append new SDpairs

        if self.timeSlot == 0:  # pre-prepare
            self.prepare()

        start = process_time()   # start

        self.p2()   # p2
        
        if self.name in self.doubleSwapped:  # swapped 1
            self.trySwapped()

        if self.canEntangled:   # entangled 1
            self.tryEntanglement()
        
        self.trySwapped()   # swapped 2

        # if self.canEntangled and self.name in self.doubleEntangled:   # entangled 2
        #     self.tryEntanglement()

        res = self.p4() # p4 

        end = process_time()    # end 

        self.srcDstPairs.clear()

        res.totalRuntime += (end - start)
        res.algorithmRuntime = res.totalRuntime / res.numOfTimeslot

        res = self.modifyResult(res)    # modify recording results 

        return res

@dataclass
class PickedPath:
    weight: float
    width: int
    path: list
    time: int

    def __hash__(self):
        return hash((self.weight, self.width, self.path[0], self.path[-1]))

if __name__ == '__main__':

    topo = Topo.generate(100, 0.9, 5, 0.002, 6, 0.5, 30)
    # neighborsOf = {}
    # neighborsOf[1] = {1:2}
    # neighborsOf[1].update({3:3})
    # neighborsOf[2] = {2:1}

    # print(neighborsOf[2][2])
   