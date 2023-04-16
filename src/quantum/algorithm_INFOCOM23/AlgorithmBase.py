from dataclasses import dataclass
from string import Template
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
        # ---
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

class Request:
    def __init__(self, src, dst, time, intermediate):
        """
        Initialize Request

        :param src: src
        :type src: `Node`
        :param dst: dst
        :type dst: `Node`
        :param time: entering time for request
        :type time: `int`
        :param intermediate: the intermediate node for request
        :type intermediate: `Node`
        """
        #
        #
        # CImark: Whether calculate the number of intermediate node on path for this request
        #
        self.src = src
        self.dst = dst
        self.time = time
        self.state = 0
        self.storageTime = 0
        self.broken = False 
        self.numOfTemporary = 0
        self.intermediate = intermediate
        self.paths = []
        self.CImark = False
        self.pathlen = 0
 
class Path:
    def __init__(self):
        """
        Initialize Path 

        """
        self.path = []
        self.links = []
        self.intermediates = []

class AlgorithmBase:
    def __init__(self, topo):
        self.name = "Base"
        self.topo = topo
        self.srcDstPairs = []
        self.timeSlot = 0
        self.result = AlgorithmResult()
        self.canEntangled = True
        self.totalNumOfReq = 0  # Total number of requests
        self.totalNumOfFinishedReq = 0  # Total number of finished requests
        self.totalNumOfBrokenReq = 0    # Total number of peeping requests
        self.totalNumOfSecureReq = 0    # Total number of secure requests
        self.totalNumOfIntermediate = 0 # Total number of intermediates
        self.totalNumOfNormalNodeOnPath = 0 # Total number of normal nodes on all paths
        self.totalNumOfTemporary = 0    # Total number of temporary counts
        self.idleTime = 0   # Total idle time
        self.numOfTimeOut = 0   # Total number of timeout requests
        self.doubleEntangled = ["SAGE", "QCAST_SOAR", "Greedy_SOAR", "REPS_SOAR"]
        self.doubleSwapped = ["SAGE", "QCAST_SOAR", "Greedy_SOAR", "REPS_SOAR", "Greedy", "QCAST", "REPS"]
        
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
    
    def traditionSwapped(self, path, links):
        """
            Linear swap
            traditionSwapped() in trySwapped() for QCAST and GREEDY algos 

            Return the farthest node on path after swapping
            If the return not dst, then path constructed failed

            :param path: the given path
            :type path: `list`
            :param links: links on path
            :type links: `list`
            :return: the farthest node on path after swapping
            :rtype: `Node`
        """
        # Calculate the continuous all succeed links 
        # Check entanglement on path are all successful
        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            if not prevLink.entangled:
                return path[0]

        # If path is just length 2, check directly 
        if len(path) == 2:  
            if not links[0].entangled:
                return path[0]
            else:
                return path[1]

        # Run swapping and check whether successful
        for n in range(1, len(path)-1):
            prevLink = links[n-1]
            nextLink = links[n]

            # If not swapped then run swapped, else continue
            #   If swap failed then clear the link state and return src
            #   If swap succeed and the next hop is terminal then return dst, else return src
            if not prevLink.swappedAt(path[n]) and not nextLink.swappedAt(path[n]):
                if not path[n].attemptSwapping(prevLink, nextLink): 
                    for link in links:
                        if link.swapped():
                            link.clearPhase4Swap() 
                    return path[0]  
                else:       
                    if n == len(path)-2:    
                        return path[-1]
                    else:
                        return path[0]
            
    def modifyResult(self, res):
        """
        Update the result

        :return: new result
        :rtype: `AlgorithmResult`
        :param res: old result
        :type res: `AlgorithmResult`
        """
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
        
        s = Template("[ $t ] trusedRatioOnPath: $a \
                      \n[ $t ] avgTimeSlotsForSecure: $b \
                      \n[ $t ] secureThroughput: $c \
                      \n[ $t ] throuhgput: $d \
                      \n[ $t ] secureRatio: $e \
                      \n[ $t ] avgTemporaryCount: $f \
                    " )
        print(s.substitute(t=self.name, 
                           a=res.trustedRatioOnPath,
                           b=res.avgTimeSlotsForSecure,
                           c=res.secureThroughput,
                           d=res.throuhgput,
                           e=res.secureRatio,
                           f=res.avgTemporaryCount))
                           
        return res

    def work(self, pairs, time): 
        """
        Algotithm Running Framework

        :return: result
        :rtype: `AlgorithmResult`
        :param pairs: SD pairs list
        :type pairs: `list[(Node, Node)]`
        :param time: the current time
        :type time: `int`
        """
        # Update current time and append new SD pairs
        self.timeSlot = time    
        self.srcDstPairs.extend(pairs) 

        # Pre-prepare
        if self.timeSlot == 0:  
            self.prepare()

        """
        Start > P2 > Swapped 1 > Entangled 1 > Swapped 2 > P4 > End
        """ 
        start = process_time()   
        self.p2()
        if self.name in self.doubleSwapped:  
            self.trySwapped()
        if self.canEntangled:   
            self.tryEntanglement()  
        self.trySwapped()
        res = self.p4() 
        end = process_time()    
        self.srcDstPairs.clear()

        res.totalRuntime += (end - start)
        res.algorithmRuntime = res.totalRuntime / res.numOfTimeslot
        # Modify recording results 
        res = self.modifyResult(res)    

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
    pass
   