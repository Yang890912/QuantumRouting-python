from pandas import *
import os
from os import listdir
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms
 
class ChartGenerator: 
    def __init__(self, dir, file):
        fileName = dir + file
        # no file
        if not os.path.exists(fileName):
            print("file doesn't exist")
            return
        
        # reading CSV file
        data = read_csv(fileName)
        
        # converting column data to list
        colHeader = list(data.columns)
        col = [list(data[i]) for i in colHeader]
        
        AlgoName = colHeader[1:]
        numOfData = len(col[0])
        numOfAlgo = len(AlgoName)
        
        x = col[0] # data
        y = col[1:]
        
        Xlabel, Ylabel = str(colHeader[0]).split("\\")
        
        print("start generate", fileName)

        # setting
        color = [
            "#FF0000",
            "#00FF00",   
            "#0000FF",
            "#000000",
            "#900321",
        ]
        
        fontsize = 32
        Xlabel_fontsize = fontsize
        Ylabel_fontsize = fontsize
        Xticks_fontsize = fontsize
        Yticks_fontsize = fontsize
        
        andy_theme = {
        # "xtick.labelsize": 20,
        # "ytick.labelsize": 20,
        # "axes.labelsize": 20,
        # "axes.titlesize": 20,
        "font.family": "Times New Roman",
        "mathtext.it": "Times New Roman:italic",
        "mathtext.fontset": "custom"
        }
        
        Ypow = 0
        Xpow = 0
        
        matplotlib.rcParams.update(andy_theme)
        
        fig, ax1 = plt.subplots(figsize = (7, 6), dpi = 600)
        
        # ax1.spines['top'].set_linewidth(2) # 框線粗度
        # ax1.spines['right'].set_linewidth(1.5)
        # ax1.spines['bottom'].set_linewidth(1.5)
        # ax1.spines['left'].set_linewidth(1.5)
        
        ax1.tick_params(direction = "in")
        ax1.tick_params(bottom = True, top = True, left = True, right = True)
        ax1.tick_params(pad = 20)
        
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
            Yend = 0.4
            Ystart = 0
            Yinterval = 0.1
        marker = ['o', 's', 'v', 'x', 'd']
        for i in range(numOfAlgo):
            ax1.plot(x, y[i], color = color[i], lw = 2.5, linestyle = "-", marker = marker[i], markersize = 15, markerfacecolor = "none", markeredgewidth = 2.5)
        
        plt.xticks(fontsize = Xticks_fontsize)
        plt.yticks(fontsize = Yticks_fontsize)

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
        
        plt.subplots_adjust(top = 0.75) # margin
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
        pdfName = file[0:-4]
        # plt.savefig('./pdf/{}.eps'.format(pdfName)) 
        plt.savefig("./pdf/{}.jpg".format(pdfName)) 
        # Xlabel = Xlabel.replace(' (%)','')
        # Xlabel = Xlabel.replace('# ','')
        # Ylabel = Ylabel.replace('# ','')
        # plt.close()

    def genMultiName(self, multiple):
        if multiple == 0:
            return str()
        else:
            return "($" + "10" + "^{" + str(multiple) + "}" + "$)"
       

if __name__ == "__main__":
    dir = "./data_csv/"
    files = listdir(dir)
    for file in files:
        ChartGenerator(dir, file)