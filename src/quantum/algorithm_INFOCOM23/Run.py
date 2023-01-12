import multiprocessing
import sys
import copy
import csv
sys.path.append("..")
from AlgorithmBase import AlgorithmBase
from AlgorithmBase import AlgorithmResult
from SAGE import SAGE
from GreedyHopRouting import GreedyHopRouting
from GreedyHopRouting_OPP import GreedyHopRouting_OPP
from GreedyHopRouting_SOAR import GreedyHopRouting_SOAR
from QCAST import QCAST
from QCAST_OPP import QCAST_OPP
from QCAST_SOAR import QCAST_SOAR
from REPS import REPS
from REPS_OPP import REPS_OPP
from REPS_SOAR import REPS_SOAR

from topo.Topo import Topo
from topo.Node import Node
from topo.Link import Link
from random import sample
from numpy import log as ln



def runThread(algo, requests, algoIndex, ttime, pid, resultDict):
    for i in range(ttime):
        result = algo.work(requests[i], i)
    # if algoIndex == 0:
    #     for req in algo.requestState:
    #         if algo.requestState[req].state == 2:
    #             algo.requestState[req].intermediate.clearIntermediate()
    resultDict[pid] = result



def Run(numOfRequestPerRound = 5, numOfNode = None, L = None, q = None, alpha = None, SocialNetworkDensity = None, rtime = 10, topo = None, FixedRequests = None, k = None):

    if topo == None:
        topo = Topo.generate(numOfNode, q, k, alpha, 6, SocialNetworkDensity, L)
    else:
        if q != None:
            topo.setQ(q)
        if alpha != None:
            topo.setAlpha(alpha)
        if SocialNetworkDensity != None:
            topo.setDensity(SocialNetworkDensity)
        if L != None:
            topo.setL(L)
        if k != None:
            topo.k = k

    # make copy
    algorithms = []
    algorithms.append(MyAlgorithm(copy.deepcopy(topo)))
    # algorithms.append(test2(copy.deepcopy(topo)))
    # algorithms.append(GreedyHopRouting(copy.deepcopy(topo)))
    # algorithms.append(OnlineAlgorithm(copy.deepcopy(topo)))
    # algorithms.append(REPS(copy.deepcopy(topo)))
    algorithms.append(GreedyHopRouting_OPP(copy.deepcopy(topo)))
    algorithms.append(OnlineAlgorithm_OPP(copy.deepcopy(topo)))
    algorithms.append(REPS_OPP(copy.deepcopy(topo)))
    algorithms.append(GreedyHopRouting_SOPP(copy.deepcopy(topo)))
    algorithms.append(OnlineAlgorithm_SOPP(copy.deepcopy(topo)))
    algorithms.append(REPS_SOPP(copy.deepcopy(topo)))

    times = 10
    results = [[] for _ in range(len(algorithms))]
    ttime = 200

    resultDicts = [multiprocessing.Manager().dict() for _ in algorithms]
    jobs = []

    pid = 0
    for _ in range(times):
        ids = {i : [] for i in range(ttime)}
        if FixedRequests != None:
            ids = FixedRequests
        else:
            for i in range(rtime):
                usedSDpair = set()
                for _ in range(numOfRequestPerRound):
                    SDpairIDList = sample([id for id in range(len(topo.nodes))], 2)
                    SDpairID = (SDpairIDList[0], SDpairIDList[1])
                    distance = topo.shortestPath(topo.nodes[SDpairID[0]], topo.nodes[SDpairID[1]], "Hop")[0]
                    roundCount = 0
                    while roundCount <= 100 and (SDpairID in usedSDpair or distance <= 10):
                        roundCount += 1
                        SDpairIDList = sample([id for id in range(len(topo.nodes))], 2)
                        SDpairID = (SDpairIDList[0], SDpairIDList[1])
                        distance = topo.shortestPath(topo.nodes[SDpairID[0]], topo.nodes[SDpairID[1]], "Hop")[0]
                    usedSDpair.add(SDpairID)
                    ids[i].append(SDpairID)
        
        for algoIndex in range(len(algorithms)):
            print("process copy copy ...", pid)
            algo = copy.deepcopy(algorithms[algoIndex])
            print("process copied", pid)
            requests = {i : [] for i in range(ttime)}
            for i in range(rtime):
                for (src, dst) in ids[i]:
                    requests[i].append((algo.topo.nodes[src], algo.topo.nodes[dst]))
            
            pid += 1
            job = multiprocessing.Process(target = runThread, args = (algo, requests, algoIndex, ttime, pid, resultDicts[algoIndex]))
            jobs.append(job)

    for job in jobs:
        job.start()

    for job in jobs:
        job.join()

    for algoIndex in range(len(algorithms)):
        results[algoIndex] = AlgorithmResult.Avg(resultDicts[algoIndex].values())

    # results[0] = result of GreedyHopRouting = a AlgorithmResult
    # results[1] = result of MyAlgorithm
    # results[2] = result of GreedyGeographicRouting
    # results[3] = result of OnlineAlgorithm
    # results[4] = result of REPS

    return results
    

if __name__ == '__main__':
    print("start Run and Generate data.txt")
    targetFilePath = "../../plot/data/"
    temp = AlgorithmResult()
    Ylabels = temp.Ylabels # Ylabels = ["algorithmRuntime", "waitingTime", "idleTime", "usedQubits", "temporaryRatio"]
    
    algorithmNames = ["SAGE", "Greedy", "QCAST", "REPS"]
    numOfRequestPerRound = [1, 2, 3, 4, 5]
    totalRequest = [10, 20, 30, 40, 50]
    numOfNodes = [50, 100, 150, 200]
    # numOfNodes = [10, 20, 30, 40, 50]
    L = [1, 2, 3, 4, 5]
    k = [1, 2, 3, 4, 5]
    q = [0.6, 0.7, 0.8, 0.9, 1]
    alpha = [0.000, 0.0002, 0.0004, 0.0006, 0.0008, 0.001]
    SocialNetworkDensity = [0.25, 0.5, 0.75, 1]
    # mapSize = [(1, 2), (100, 100), (50, 200), (10, 1000)]

    # Xlabels = ["#RequestPerRound", "totalRequest", "SocialNetworkDensity", "L", "swapProbability", "alpha", "k", "#nodes"]
    # Xparameters = [numOfRequestPerRound, totalRequest, SocialNetworkDensity, L, q, alpha, k, numOfNodes]
    Xlabels = ["#RequestPerRound", "SocialNetworkDensity", "L", "swapProbability", "alpha", "k"]
    Xparameters = [numOfRequestPerRound, SocialNetworkDensity, L, q, alpha, k]

    # ----- default value -------
    default_n = 100
    # default_n = 20
    default_q = 0.9
    default_k = 1
    default_alpha = 0.0002
    default_density = 0.25
    default_L = 5
    topo = Topo.generate(default_n, default_q, default_k, default_alpha, 6, default_density, default_L)
    # ---------------------------
    ttime = 200
    rtime = 10

    FixedRequestsID = {i : [] for i in range(ttime)}
    for i in range(rtime):
        usedSDpair = set()
        for _ in range(5): # rpr
            SDpairIDList = sample([id for id in range(len(topo.nodes))], 2)
            SDpairID = (SDpairIDList[0], SDpairIDList[1])
            distance = topo.shortestPath(topo.nodes[SDpairID[0]], topo.nodes[SDpairID[1]], "Hop")[0]
            roundCount = 0
            while roundCount <= 100 and (SDpairID in usedSDpair or distance <= 10):
                roundCount += 1
                SDpairIDList = sample([id for id in range(len(topo.nodes))], 2)
                SDpairID = (SDpairIDList[0], SDpairIDList[1])
                distance = topo.shortestPath(topo.nodes[SDpairID[0]], topo.nodes[SDpairID[1]], "Hop")[0]
            usedSDpair.add(SDpairID)
            FixedRequestsID[i].append(SDpairID)
               
    skipXlabel = [1,2]
    for XlabelIndex in range(len(Xlabels)):
        Xlabel = Xlabels[XlabelIndex]
        Ydata = []
        if XlabelIndex in skipXlabel:
            continue
        for Xparam in Xparameters[XlabelIndex]:
            
            # check schedule
            statusFile = open("status.txt", "w")
            print(Xlabel + str(Xparam), file = statusFile)
            statusFile.flush()
            statusFile.close()
            # ------
            if XlabelIndex == 0: # #RequestPerRound
                result = Run(numOfRequestPerRound = Xparam, topo = copy.deepcopy(topo))
            # if XlabelIndex == 1: # totalRequest
            #     result = Run(numOfRequestPerRound = Xparam, rtime = 1, topo = copy.deepcopy(topo))
            # if XlabelIndex == 1: # SocialNetworkDensity
            #     result = Run(SocialNetworkDensity = Xparam, topo = copy.deepcopy(topo))
            # if XlabelIndex == 2: # L
            #     result = Run(L = Xparam, topo = copy.deepcopy(topo))
            if XlabelIndex == 3: # swapProbability
                result = Run(q = Xparam, topo = copy.deepcopy(topo))
            if XlabelIndex == 4: # alpha
                result = Run(alpha = Xparam, topo = copy.deepcopy(topo))
            # if XlabelIndex == 5: # k
            #     result = Run(k = Xparam, topo = copy.deepcopy(topo))
            # if XlabelIndex == 7: # #nodes
            #     result = Run(numOfNode = Xparam, L = default_L, q = default_q, alpha = default_alpha, SocialNetworkDensity = default_density, k = default_k)

            Ydata.append(result)

        # Ydata[0] = numOfNode = 10 algo1Result algo2Result ... 
        # Ydata[1] = numOfNode = 20 algo1Result algo2Result ... 
        # Ydata[2] = numOfNode = 50 algo1Result algo2Result ... 
        # Ydata[3] = numOfNode = 100 algo1Result algo2Result ... 

        # write in txt
        # for Ylabel in Ylabels:
        #     filename = Xlabel + "_" + Ylabel + ".txt"
        #     F = open(targetFilePath + filename, "w")
        #     for i in range(len(Xparameters[XlabelIndex])):
        #         Xaxis = str(Xparameters[XlabelIndex][i])
        #         Yaxis = [algoResult.toDict()[Ylabel] for algoResult in Ydata[i]]
        #         Yaxis = str(Yaxis).replace("[", " ").replace("]", "\n").replace(",", "")
        #         F.write(Xaxis + Yaxis)
        #     F.close()
        
        # write in csv
        for Ylabel in Ylabels: # 結果寫入檔案
            filename = Xlabel + "_" + Ylabel + ".csv"
            F = open(targetFilePath + filename, "w")
            writer = csv.writer(F) # create the csv writer
            
            row = []
            row.append(Xlabel + " \\ " + Ylabel)
            row.extend(algorithmNames)  
            writer.writerow(row) # write a row to the csv file
            
            for i in range(len(Xparameters[XlabelIndex])):
                row = []
                row.append(Xparameters[XlabelIndex][i])
                row.extend([algoResult.toDict()[Ylabel] for algoResult in Ydata[i]])
                writer.writerow(row)
            F.close()

    exit(0)

    # write remainRequestPerRound
    results = Run(numOfRequestPerRound = 50, rtime = 1) # algo1Result algo2Result ...
    for result in results:
        result.remainRequestPerRound.insert(0, 1)
    
    # sampleRounds = [0, 5, 10, 15, 20, 25]
    sampleRounds = [0, 2, 4, 6, 8, 10]

    # write in txt
    # filename = "Timeslot" + "_" + "#remainRequest" + ".txt"
    # F = open(targetFilePath + filename, "w")
    # for roundIndex in sampleRounds:
    #     Xaxis = str(roundIndex)
    #     Yaxis = [result.remainRequestPerRound[roundIndex] for result in results]
    #     Yaxis = str(Yaxis).replace("[", " ").replace("]", "\n").replace(",", "")
    #     F.write(Xaxis + Yaxis)
    # F.close()

    # write in csv
    filename = "Timeslot" + "_" + "#remainRequest" + ".csv"
    F = open(targetFilePath + filename, "w")
    writer = csv.writer(F) # create the csv writer
    
    row = []
    row.append(Xlabel + " \\ " + Ylabel)
    row.extend(algorithmNames)  
    writer.writerow(row) # write a row to the csv file

    for roundIndex in sampleRounds:
        row = []
        row.append(str(roundIndex))
        row.extend(result.remainRequestPerRound[roundIndex] for result in results)
        writer.writerow(row)
    F.close()