import multiprocessing
import sys
import copy
sys.path.append("..")
from AlgorithmBase import AlgorithmBase
from AlgorithmBase import AlgorithmResult
from MyAlgorithm import MyAlgorithm
from OnlineAlgorithm import OnlineAlgorithm
from GreedyGeographicRouting import GreedyGeographicRouting
from GreedyHopRouting import GreedyHopRouting
# from REPS import REPS
from topo.Topo import Topo
from topo.Node import Node
from topo.Link import Link
from random import sample
from numpy import log as ln


def runThread(algo, requests, algoIndex, ttime, pid, resultDict):
    for i in range(ttime):
        result = algo.work(requests[i], i)
    if algoIndex == 0:
        for req in algo.requestState:
            if algo.requestState[req].state == 2:
                algo.requestState[req].intermediate.clearIntermediate()
    resultDict[pid] = result



def Run(numOfRequestPerRound = 5, numOfNode = 100, r = 7, q = 0.9, alpha = 0.0002, SocialNetworkDensity = 0.5, rtime = 20, topo = None, FixedRequests = None):

    if topo == None:
        topo = Topo.generate(numOfNode, q, 5, alpha, 6)
    
    topo.setQ(q)
    topo.setAlpha(alpha)

    # make copy
    algorithms = []
    algorithms.append(MyAlgorithm(copy.deepcopy(topo)))
    # algorithms.append(GreedyHopRouting(copy.deepcopy(topo)))
    # algorithms.append(GreedyGeographicRouting(copy.deepcopy(topo)))
    # algorithms.append(OnlineAlgorithm(copy.deepcopy(topo)))
    # algorithms.append(REPS(copy.deepcopy(topo)))

    algorithms[0].r = r
    algorithms[0].density = SocialNetworkDensity

    times = 100
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
            for i in range(ttime):
                if i < rtime:
                    for _ in range(numOfRequestPerRound):
                        a = sample([i for i in range(numOfNode)], 2)
                        ids[i].append((a[0], a[1]))
        
        for algoIndex in range(len(algorithms)):
            algo = copy.deepcopy(algorithms[algoIndex])
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
    
    numOfRequestPerRound = [1, 2, 3, 4, 5]
    totalRequest = [10, 20, 30, 40, 50]
    numOfNodes = [50, 100, 150, 200]
    r = [0, 2, 4, 6, 8, 10]
    q = [0.000001, 0.2, 0.4, 0.6, 0.8, 1]
    alpha = [0.0000, 0.0002, 0.0004, 0.0006, 0.0008, 0.001]
    SocialNetworkDensity = [0.25, 0.5, 0.75, 1]
    # mapSize = [(1, 2), (100, 100), (50, 200), (10, 1000)]

    Xlabels = ["#RequestPerRound", "totalRequest", "#nodes", "r", "swapProbability", "alpha", "SocialNetworkDensity"]
    Xparameters = [numOfRequestPerRound, totalRequest, numOfNodes, r, q, alpha, SocialNetworkDensity]

    topo = Topo.generate(100, 0.9, 5, 0.0002, 6)

    tmp_ids = {i : [] for i in range(200)}
    for i in range(200):
        if i < 20:
            for _ in range(5):
                a = sample([i for i in range(100)], 2)
                tmp_ids[i].append((a[0], a[1]))
               
    skipXlabel = [0, 1, 2, 4, 5, 6]
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
            if XlabelIndex == 1: # totalRequest
                result = Run(numOfRequestPerRound = Xparam, rtime = 1, topo = copy.deepcopy(topo))
            if XlabelIndex == 2: # #nodes
                result = Run(numOfNode = Xparam)
            if XlabelIndex == 3: # r
                result = Run(r = Xparam, topo = copy.deepcopy(topo), FixedRequests = tmp_ids)
            if XlabelIndex == 4: # swapProbability
                result = Run(q = Xparam, topo = copy.deepcopy(topo))
            if XlabelIndex == 5: # alpha
                result = Run(alpha = Xparam, topo = copy.deepcopy(topo))
            if XlabelIndex == 6: # SocialNetworkDensity
                result = Run(SocialNetworkDensity = Xparam, topo = copy.deepcopy(topo))
            # if XlabelIndex == 7:
            #     result = Run(mapSize = Xparam)
            Ydata.append(result)

        # Ydata[0] = numOfNode = 10 algo1Result algo2Result ... 
        # Ydata[1] = numOfNode = 20 algo1Result algo2Result ... 
        # Ydata[2] = numOfNode = 50 algo1Result algo2Result ... 
        # Ydata[3] = numOfNode = 100 algo1Result algo2Result ... 

        for Ylabel in Ylabels:
            filename = Xlabel + "_" + Ylabel + ".txt"
            F = open(targetFilePath + filename, "w")
            for i in range(len(Xparameters[XlabelIndex])):
                Xaxis = str(Xparameters[XlabelIndex][i])
                Yaxis = [algoResult.toDict()[Ylabel] for algoResult in Ydata[i]]
                Yaxis = str(Yaxis).replace("[", " ").replace("]", "\n").replace(",", "")
                F.write(Xaxis + Yaxis)
            F.close()

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
            if XlabelIndex == 1: # totalRequest
                result = Run(numOfRequestPerRound = Xparam, rtime = 1, topo = copy.deepcopy(topo))
            if XlabelIndex == 2: # #nodes
                result = Run(numOfNode = Xparam)
            if XlabelIndex == 3: # r
                result = Run(r = Xparam, alpha = 0.0004, topo = copy.deepcopy(topo), FixedRequests = tmp_ids)
            if XlabelIndex == 4: # swapProbability
                result = Run(q = Xparam, topo = copy.deepcopy(topo))
            if XlabelIndex == 5: # alpha
                result = Run(alpha = Xparam, topo = copy.deepcopy(topo))
            if XlabelIndex == 6: # SocialNetworkDensity
                result = Run(SocialNetworkDensity = Xparam, topo = copy.deepcopy(topo))
            # if XlabelIndex == 7:
            #     result = Run(mapSize = Xparam)
            Ydata.append(result)


        # Ydata[0] = numOfNode = 10 algo1Result algo2Result ... 
        # Ydata[1] = numOfNode = 20 algo1Result algo2Result ... 
        # Ydata[2] = numOfNode = 50 algo1Result algo2Result ... 
        # Ydata[3] = numOfNode = 100 algo1Result algo2Result ... 

        for Ylabel in Ylabels:
            filename = Xlabel + "_" + Ylabel + "2.txt"
            F = open(targetFilePath + filename, "w")
            for i in range(len(Xparameters[XlabelIndex])):
                Xaxis = str(Xparameters[XlabelIndex][i])
                Yaxis = [algoResult.toDict()[Ylabel] for algoResult in Ydata[i]]
                Yaxis = str(Yaxis).replace("[", " ").replace("]", "\n").replace(",", "")
                F.write(Xaxis + Yaxis)
            F.close()

    exit(0)
    # write remainRequestPerRound
    results = Run(numOfRequestPerRound = 50, rtime = 1) # algo1Result algo2Result ...
    for result in results:
        result.remainRequestPerRound.insert(0, 1)
    
    # sampleRounds = [0, 5, 10, 15, 20, 25]
    sampleRounds = [0, 2, 4, 6, 8, 10]
    filename = "Timeslot" + "_" + "#remainRequest" + ".txt"
    F = open(targetFilePath + filename, "w")
    for roundIndex in sampleRounds:
        Xaxis = str(roundIndex)
        Yaxis = [result.remainRequestPerRound[roundIndex] for result in results]
        Yaxis = str(Yaxis).replace("[", " ").replace("]", "\n").replace(",", "")
        F.write(Xaxis + Yaxis)
    F.close()
