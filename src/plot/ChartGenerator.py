from cmath import log10
import numpy as np
import math
import os
import matplotlib.pyplot as plt
import matplotlib.transforms
# import latex
import matplotlib
from matplotlib.offsetbox import AnchoredOffsetbox, TextArea, HPacker, VPacker

class ChartGenerator:
    # data檔名 Y軸名稱 X軸名稱 Y軸要除多少(10的多少次方) Y軸起始座標 Y軸終止座標 Y軸座標間的間隔
    def __init__(self, dataName, Ylabel, Xlabel):
        filename = './data/' + dataName

        if not os.path.exists(filename):
            print("file doesn't exist")
            return
        
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        print("start generate", filename)
        
        
        # Ydiv, Ystart, Yend, Yinterval
        Ypow = 0
        Xpow = 0

        # color = [
        #     "#000000",
        #     "#006400",
        #     "#FF1493",
        #     "#7FFF00",   
        #     "#900321",
        # ]
        color = [
            "#FF0000",
            "#00FF00",   
            "#0000FF",
            "#000000",
            "#900321",
        ]
        # matplotlib.rcParams['text.usetex'] = True

        fontsize = 32
        Xlabel_fontsize = fontsize
        Ylabel_fontsize = fontsize
        Xticks_fontsize = fontsize
        Yticks_fontsize = fontsize
            
        # matplotlib.rcParams['text.usetex'] = True
        # fig, ax = plt.subplots(figsize=(8, 6), dpi=600) 
        
        andy_theme = {
        # "axes.grid": True,
        # "grid.linestyle": "--",
        # "legend.framealpha": 1,
        # "legend.facecolor": "white",
        # "legend.shadow": True,
        # "legend.fontsize": 14,
        # "legend.title_fontsize": 16,
        "xtick.labelsize": 20,
        "ytick.labelsize": 20,
        "axes.labelsize": 20,
        "axes.titlesize": 20,
        "font.family": "Times New Roman",
        "mathtext.it": "Times New Roman:italic",
        # "mathtext.default": "regular",
        "mathtext.fontset": "custom"
        # "mathtext.fontset": "custom"
        # "figure.autolayout": True
        # "text.usetex": True,
        # "figure.dpi": 100,
        }
        
        matplotlib.rcParams.update(andy_theme)
        fig, ax1 = plt.subplots(figsize = (7, 6), dpi = 600)
        # ax1.spines['top'].set_linewidth(1.5)
        # ax1.spines['right'].set_linewidth(1.5)
        # ax1.spines['bottom'].set_linewidth(1.5)
        # ax1.spines['left'].set_linewidth(1.5)
        ax1.tick_params(direction = "in")
        ax1.tick_params(bottom = True, top = True, left = True, right = True)
        ax1.tick_params(pad = 20)


        ##data start##
        x = []
        _y = []
        numOfData = 0

        for line in lines:
            line = line.replace('\n','')
            data = line.split(' ')
            numOfline = len(data)
            numOfData += 1
            for i in range(numOfline):
                if i == 0:
                    x.append(data[i])
                else:
                    _y.append(data[i])        
        
        numOfAlgo = len(_y) // numOfData

        y = [[] for _ in range(numOfAlgo)]
        for i in range(numOfData * numOfAlgo):
            y[i % numOfAlgo].append(_y[i])

        # print(x)
        # print(y)

        maxData = 0
        minData = math.inf

        for i in range(-10, -1, 1):
            if float(x[numOfData - 1]) <= 10 ** i:
                Xpow = (i - 2)

        Ydiv = float(10 ** Ypow)
        Xdiv = float(10 ** Xpow)
        
        for i in range(numOfData):
            x[i] = float(x[i]) / Xdiv

        for i in range(numOfAlgo):
            for j in range(numOfData):
                y[i][j] = float(y[i][j]) / Ydiv
                maxData = max(maxData, y[i][j])
                minData = min(minData, y[i][j])

        Yend = math.ceil(maxData)
        Ystart = 0
        Yinterval = (Yend - Ystart) / 5

        if maxData > 1.1:
            Yinterval = int(math.ceil(Yinterval))
            Yend = int(Yend)
        else:
            Yend = 1
            Ystart = 0
            Yinterval = 0.2

        marker = ['o', 's', 'v', 'x', 'd']
        for i in range(numOfAlgo):
            ax1.plot(x, y[i], color = color[i], lw = 2.5, linestyle = "-", marker = marker[i], markersize = 15, markerfacecolor = "none", markeredgewidth = 2.5)
        # plt.show()

        plt.xticks(fontsize = Xticks_fontsize)
        plt.yticks(fontsize = Yticks_fontsize)
        
        AlgoName = ["SEER", "Greedy", "Q-CAST", "REPS"]

        leg = plt.legend(
            AlgoName,
            loc = 10,
            bbox_to_anchor = (0.4, 1.25),
            prop = {"size": fontsize, "family": "Times New Roman"},
            frameon = "False",
            labelspacing = 0.2,
            handletextpad = 0.2,
            handlelength = 1,
            columnspacing = 0.2,
            ncol = 2,
            facecolor = "None",
        )

        leg.get_frame().set_linewidth(0.0)
        Ylabel += self.genMultiName(Ypow)
        Xlabel += self.genMultiName(Xpow)
        plt.subplots_adjust(top = 0.75)
        plt.subplots_adjust(left = 0.3)
        plt.subplots_adjust(right = 0.95)
        plt.subplots_adjust(bottom = 0.25)

        plt.yticks(np.arange(Ystart, Yend + Yinterval, step = Yinterval), fontsize = Yticks_fontsize)
        plt.xticks(x)
        plt.ylabel(Ylabel, fontsize = Ylabel_fontsize, labelpad = 35)
        plt.xlabel(Xlabel, fontsize = Xlabel_fontsize, labelpad = 10)
        ax1.yaxis.set_label_coords(-0.3, 0.5)
        ax1.xaxis.set_label_coords(0.45, -0.27)
        # plt.show()
        # plt.tight_layout()
        pdfName = dataName[0:-4]
        # plt.savefig('./pdf/{}.eps'.format(pdfName)) 
        plt.savefig('./pdf/{}.jpg'.format(pdfName)) 
        # Xlabel = Xlabel.replace(' (%)','')
        # Xlabel = Xlabel.replace('# ','')
        # Ylabel = Ylabel.replace('# ','')
        plt.close()

    def genMultiName(self, multiple):
        if multiple == 0:
            return str()
        else:
            return "($" + "10" + "^{" + str(multiple) + "}" + "$)"

if __name__ == "__main__":
    # data檔名 Y軸名稱 X軸名稱 Y軸要除多少(10的多少次方) Y軸起始座標 Y軸終止座標 Y軸座標間的間隔
    # ChartGenerator("numOfnodes_waitingTime.txt", "need #round", "#Request of a round", 0, 0, 25, 5)
    Xlabels = ["#RequestPerRound", "totalRequest", "#nodes", "r", "swapProbability", "alpha", "SocialNetworkDensity"]
    Ylabels = ["algorithmRuntime", "waitingTime", "idleTime", "usedQubits", "temporaryRatio"]
    
    for Xlabel in Xlabels:
        for Ylabel in Ylabels:
            dataFileName = Xlabel + '_' + Ylabel + '.txt'
            ChartGenerator(dataFileName, Ylabel, Xlabel)


    Xlabel = "Timeslot"
    Ylabel = "#remainRequest"
    dataFileName = Xlabel + "_" + Ylabel + ".txt"
    ChartGenerator(dataFileName, Ylabel, Xlabel)