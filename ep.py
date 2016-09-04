# -*- coding: utf-8 -*-
"""
Created on Sun Aug 21 12:37:56 2016

@author: luan
"""

import numpy as np
import cv2
from mpegCodec import codec
from math import log
from mpegCodec.frames import MJPEGcodec as jpeg
from mpegCodec.utils.image_quality_assessment import metrics
from Tkinter import Tk
from tkFileDialog import askopenfilename
from math import sqrt
import operator

class ep:
    def __init__ (self, image, pop_length, quality):
        self.image = image
        self.quality = quality
        self.r, self.c, self.d = self.image.shape
        self.pop_length = pop_length
        self.generation = 1
        self.sigma = 1
        self.hufftables = self.acdctables()
        self.pop = []
        self.best_individual = [[],0.0]
        self.count = 0
    
    def zagzig(self, seq, bshp=[8,8]):
        block = np.zeros(bshp)            
        indx = sorted(((x,y) for x in range(bshp[0]) for y in range(bshp[1])),
                            key = lambda (x,y): (x+y, -y if (x+y) % 2 else y))
        if len(seq)>0:                    
            for s in range(len(seq)): #        for t in range(len(seq[s])):
                block[indx[s]] = seq[s]
            
        return np.float_(block)
        
    def fitness (self, xm, x, ym, y):
        a = 0.6
        b = 1.0 - a
        
        return a*float(ym/y)-b*float(x/xm)
        
#    def fitness (self, xm, x, ym, y):
#        return (ym/y)-(1.- float(xm)/float(x))
        
        
    def individual (self):
        Z = np.zeros((8,8,3))
        values = []
        for i in range (3):
            length = 64
            values_aux = np.random.randint(low=1, high=255, size=(length))
            values_aux.sort()
            values = np.concatenate((values,values_aux),axis=0)
            Z[:,:,i] = self.zagzig(seq=values_aux)
        
        encoder = jpeg.Encoder(self.image, self.quality, self.hufftables, Z, mode = '420')
        xm = float(encoder.NumBits)/float(self.r*self.c)
        decoder = jpeg.Decoder(encoder.seqhuff, self.hufftables, Z, [self.image.shape, self.quality, '420'])
        ym = metrics.msim(self.image, decoder._run_()[0:self.r, 0:self.c])[0]
        
        encoder = jpeg.Encoder(self.image, self.quality, self.hufftables, self.genQntb(self.quality), mode = '420')
        x = float(encoder.NumBits)/float(self.r*self.c)
        decoder = jpeg.Decoder(encoder.seqhuff, self.hufftables, self.genQntb(self.quality), [self.image.shape, self.quality, '420'])
        y = metrics.msim(self.image, decoder._run_()[0:self.r, 0:self.c])[0]
        
        return [values, self.fitness(xm, x, ym, y)]
        
    def mutation (self):
        size = 64
        pop = []
        c = sqrt(2*(3*64))**(-1)
        loc = 0.0
        values = []
        for i in range(self.pop_length):
            print '-> Individual: %d' %(i)
            Z = np.zeros((8,8,3))
            for j in range (3):
                scale = 1.0
                scale = np.std(self.pop[i][0][j:j+64])*np.exp(c*np.random.normal(loc,scale))
                mut = np.random.normal(loc, scale, size)
                mut.sort()
                values_aux = np.floor(np.abs(self.pop[i][0][j:j+64]+mut))
                values_aux[values_aux[:]==0.0] = 1.0
                values = np.concatenate((values,values_aux),axis=0)
                Z[:,:,j] = self.zagzig(seq=values_aux)
                
            encoder = jpeg.Encoder(self.image, self.quality, self.hufftables, Z, mode = '420')
            xm = float(encoder.NumBits)/float(self.r*self.c)
            decoder = jpeg.Decoder(encoder.seqhuff, self.hufftables, Z, [self.image.shape, self.quality, '420'])
            ym = metrics.msim(self.image, decoder._run_()[0:self.r, 0:self.c])[0]
            
            encoder = jpeg.Encoder(self.image, self.quality, self.hufftables, self.genQntb(self.quality), mode = '420')
            x = float(encoder.NumBits)/float(self.r*self.c)
            decoder = jpeg.Decoder(encoder.seqhuff, self.hufftables, self.genQntb(self.quality), [self.image.shape, self.quality, '420'])
            y = metrics.msim(self.image, decoder._run_()[0:self.r, 0:self.c])[0]                
                
            pop.append([values, self.fitness(xm, x, ym, y)])
        
        return pop

    def vs (self, position, number_opponents, length):
        index = []
        while len(index) < number_opponents:
            opponent = np.random.randint(length)
            if opponent != position:
                index.append(opponent)
        return index
        
    def selection (self, aux_pop):
        print '# Selection'
        temp_pop = np.concatenate((self.pop,aux_pop), axis=0)
        score = {}
        number_opponents = 10
        for i in range(len(temp_pop)):
            score[i] = 0
            
        for i in range(len(temp_pop)):
            opponents = self.vs (i, number_opponents, 2*self.pop_length)
            for j in opponents:
                if temp_pop[i][1] > temp_pop[j][1]:
                    score[i] += 1
                elif temp_pop[i][1] < temp_pop[j][1]:
                    score[j] += 1
                elif temp_pop[i][1] == temp_pop[j][1]:
                    score[i] += 1
                    score[j] += 1
                    
        score = sorted(score.items(), key=operator.itemgetter(1), reverse=True)
        pop = []
        for i in range(self.pop_length):
            pop.append(temp_pop[score[i][0]])
            
        return pop
        
        
    def genPop (self):
        pop = []
        if len(self.pop) == 0:
            for i in range (self.pop_length):
                print '-> Individual: %d' %(i)
                pop.append(self.individual())
                
        else:
            temp_pop = self.mutation()
            pop = self.selection(temp_pop)
        
        return np.array(pop)
        
    def stopping_criterion (self, best_individual):
        if self.count == 20:
            return True
        else:
            return False
        
    def run (self):
        print '##### Starting evolutionary programming #####'
        xm, x, ym, y = 0.,0.,0.,0.
        criterion = False
        while criterion is False:
            print '# Generation: %d' % (self.generation)
            self.pop = self.genPop()
            best = self.pop[0]
            if best[1] > self.best_individual[1]:
                self.best_individual = best
                self.count = 0 
            else:
                self.count += 1
            self.generation += 1
            print ' -> Best fitness = %f' % (self.best_individual[1])
            criterion = self.stopping_criterion(best)
        Z = np.zeros((8,8,3))
        for i in range (3):
            Z[:,:,i] = self.zagzig(seq=self.best_individual[0][i:i+64])
        encoder = jpeg.Encoder(self.image, self.quality, self.hufftables, Z, mode = '420')
        xm = float(encoder.NumBits)/float(self.r*self.c)
        decoder = jpeg.Decoder(encoder.seqhuff, self.hufftables, Z, [self.image.shape, self.quality, '420'])
        ym = metrics.msim(self.image, decoder._run_()[0:self.r, 0:self.c])[0]

        encoder = jpeg.Encoder(self.image, self.quality, self.hufftables, self.genQntb(self.quality), mode = '420')
        x = float(encoder.NumBits)/float(self.r*self.c)
        decoder = jpeg.Decoder(encoder.seqhuff, self.hufftables, self.genQntb(self.quality), [self.image.shape, self.quality, '420'])
        y = metrics.msim(self.image, decoder._run_()[0:self.r, 0:self.c])[0]    
        print'Thanks!'
        
        return [xm, ym, x, y]
    
    def acdctables(self):
        """
        # MPEG Encoder: \n
        Method: acdctables (self)-> (dcLumaTB, dcChroTB, acLumaTB, acChrmTB) \n
        About: Generates the Huffman code Tables for AC and DC coefficient differences.
        """
        dcLumaTB = { 0:(2,'00'),     1:(3,'010'),      2:(3,'011'),       3:(3,'100'),
                    4:(3,'101'),    5:(3,'110'),      6:(4,'1110'),      7:(5,'11110'),
                    8:(6,'111110'), 9:(7,'1111110'), 10:(8,'11111110'), 11:(9,'111111110')}
        
        dcChroTB = { 0:(2,'00'),       1:(2,'01'),         2:( 2,'10'),          3:( 3,'110'),
                    4:(4,'1110'),     5:(5,'11110'),      6:( 6,'111110'),      7:( 7,'1111110'),
                    8:(8,'11111110'), 9:(9,'111111110'), 10:(10,'1111111110'), 11:(11,'11111111110')}
                         
        #Table for luminance DC coefficient differences
        #       [(run,category) : (size, 'codeword')]
        acLumaTB = {( 0, 0):( 4,'1010'), #EOB
                    ( 0, 1):( 2,'00'),               ( 0, 2):( 2,'01'),
                    ( 0, 3):( 3,'100'),              ( 0, 4):( 4,'1011'),
                    ( 0, 5):( 5,'11010'),            ( 0, 6):( 7,'1111000'),
                    ( 0, 7):( 8,'11111000'),         ( 0, 8):(10,'1111110110'),
                    ( 0, 9):(16,'1111111110000010'), ( 0,10):(16,'1111111110000011'),
                    ( 1, 1):( 4,'1100'),             ( 1, 2):( 5,'11011'),
                    ( 1, 3):( 7,'1111001'),          ( 1, 4):( 9,'111110110'),
                    ( 1, 5):(11,'11111110110'),      ( 1, 6):(16,'1111111110000100'),
                    ( 1, 7):(16,'1111111110000101'), ( 1, 8):(16,'1111111110000110'),
                    ( 1, 9):(16,'1111111110000111'), ( 1,10):(16,'1111111110001000'),
                    ( 2, 1):( 5,'11100'),            ( 2, 2):( 8,'11111001'),
                    ( 2, 3):(10,'1111110111'),       ( 2, 4):(12,'111111110100'),
                    ( 2, 5):(16,'1111111110001001'), ( 2, 6):(16,'1111111110001010'),
                    ( 2, 7):(16,'1111111110001011'), ( 2, 8):(16,'1111111110001100'),
                    ( 2, 9):(16,'1111111110001101'), ( 2,10):(16,'1111111110001110'),
                    ( 3, 1):( 6,'111010'),           ( 3, 2):( 9,'111110111'),
                    ( 3, 3):(12,'111111110101'),     ( 3, 4):(16,'1111111110001111'),
                    ( 3, 5):(16,'1111111110010000'), ( 3, 6):(16,'1111111110010001'),
                    ( 3, 7):(16,'1111111110010010'), ( 3, 8):(16,'1111111110010011'),
                    ( 3, 9):(16,'1111111110010100'), ( 3,10):(16,'1111111110010101'),
                    ( 4, 1):( 6,'111011'),           ( 4, 2):(10,'1111111000'),
                    ( 4, 3):(16,'1111111110010110'), ( 4, 4):(16,'1111111110010111'),
                    ( 4, 5):(16,'1111111110011000'), ( 4, 6):(16,'1111111110011001'),
                    ( 4, 7):(16,'1111111110011010'), ( 4, 8):(16,'1111111110011011'),
                    ( 4, 9):(16,'1111111110011100'), ( 4,10):(16,'1111111110011101'),
                    ( 5, 1):( 7,'1111010'),          ( 5, 2):(11,'11111110111'),
                    ( 5, 3):(16,'1111111110011110'), ( 5, 4):(16,'1111111110011111'),
                    ( 5, 5):(16,'1111111110100000'), ( 5, 6):(16,'1111111110100001'),
                    ( 5, 7):(16,'1111111110100010'), ( 5, 8):(16,'1111111110100011'),
                    ( 5, 9):(16,'1111111110100100'), ( 5,10):(16,'1111111110100101'),
                    ( 6, 1):( 7,'1111011'),          ( 6, 2):(12,'111111110110'),
                    ( 6, 3):(16,'1111111110100110'), ( 6, 4):(16,'1111111110100111'),
                    ( 6, 5):(16,'1111111110101000'), ( 6, 6):(16,'1111111110101001'),
                    ( 6, 7):(16,'1111111110101010'), ( 6, 8):(16,'1111111110101011'),
                    ( 6, 9):(16,'1111111110101100'), ( 6,10):(16,'1111111110101101'),
                    ( 7, 1):( 8,'11111010'),         ( 7, 2):(12,'111111110111'),
                    ( 7, 3):(16,'1111111110101110'), ( 7, 4):(16,'1111111110101111'),
                    ( 7, 5):(16,'1111111110110000'), ( 7, 6):(16,'1111111110110001'),
                    ( 7, 7):(16,'1111111110110010'), ( 7, 8):(16,'1111111110110011'),
                    ( 7, 9):(16,'1111111110110100'), ( 7,10):(16,'1111111110110101'),
                    ( 8, 1):( 9,'111111000'),        ( 8, 2):(15,'111111111000000'),
                    ( 8, 3):(16,'1111111110110110'), ( 8, 4):(16,'1111111110110111'),
                    ( 8, 5):(16,'1111111110111000'), ( 8, 6):(16,'1111111110111001'),
                    ( 8, 7):(16,'1111111110111010'), ( 8, 8):(16,'1111111110111011'),
                    ( 8, 9):(16,'1111111110111100'), ( 8,10):(16,'1111111110111101'),
                    ( 9, 1):( 9,'111111001'),        ( 9, 2):(16,'1111111110111110'),
                    ( 9, 3):(16,'1111111110111111'), ( 9, 4):(16,'1111111111000000'),
                    ( 9, 5):(16,'1111111111000001'), ( 9, 6):(16,'1111111111000010'),
                    ( 9, 7):(16,'1111111111000011'), ( 9, 8):(16,'1111111111000100'),
                    ( 9, 9):(16,'1111111111000101'), ( 9,10):(16,'1111111111000110'),
                    (10, 1):( 9,'111111010'),        (10, 2):(16,'1111111111000111'),
                    (10, 3):(16,'1111111111001000'), (10, 4):(16,'1111111111001001'),
                    (10, 5):(16,'1111111111001010'), (10, 6):(16,'1111111111001011'),
                    (10, 7):(16,'1111111111001100'), (10, 8):(16,'1111111111001101'),
                    (10, 9):(16,'1111111111001110'), (10,10):(16,'1111111111001111'),
                    (11, 1):(10,'1111111001'),       (11, 2):(16,'1111111111010000'),
                    (11, 3):(16,'1111111111010001'), (11, 4):(16,'1111111111010010'),
                    (11, 5):(16,'1111111111010011'), (11, 6):(16,'1111111111010100'),
                    (11, 7):(16,'1111111111010101'), (11, 8):(16,'1111111111010110'),
                    (11, 9):(16,'1111111111010111'), (11,10):(16,'1111111111011000'),
                    (12, 1):(10,'1111111010'),       (12, 2):(16,'1111111111011001'),
                    (12, 3):(16,'1111111111011010'), (12, 4):(16,'1111111111011011'),
                    (12, 5):(16,'1111111111011100'), (12, 6):(16,'1111111111011101'),
                    (12, 7):(16,'1111111111011110'), (12, 8):(16,'1111111111011111'),
                    (12, 9):(16,'1111111111100000'), (12,10):(16,'1111111111100001'),
                    (13, 1):(11,'11111111000'),      (13, 2):(16,'1111111111100010'),
                    (13, 3):(16,'1111111111100011'), (13, 4):(16,'1111111111100100'),
                    (13, 5):(16,'1111111111100101'), (13, 6):(16,'1111111111100110'),
                    (13, 7):(16,'1111111111100111'), (13, 8):(16,'1111111111101000'),
                    (13, 9):(16,'1111111111101001'), (13,10):(16,'1111111111101010'),
                    (14, 1):(16,'1111111111101011'), (14, 2):(16,'1111111111101100'),
                    (14, 3):(16,'1111111111101101'), (14, 4):(16,'1111111111101110'),
                    (14, 5):(16,'1111111111101111'), (14, 6):(16,'1111111111110000'),
                    (14, 7):(16,'1111111111110001'), (14, 8):(16,'1111111111110010'),
                    (14, 9):(16,'1111111111110011'), (14,10):(16,'1111111111110100'),
                    (15, 0):(11,'11111111001'),     #(ZRL)
                    (15, 1):(16,'1111111111110101'), (15, 2):(16,'1111111111110110'),
                    (15, 3):(16,'1111111111110111'), (15, 4):(16,'1111111111111000'),
                    (15, 5):(16,'1111111111111001'), (15, 6):(16,'1111111111111010'),
                    (15, 7):(16,'1111111111111011'), (15, 8):(16,'1111111111111100'),
                    (15, 9):(16,'1111111111111101'), (15,10):(16,'1111111111111110')}
                    
        #Table for chrominance AC coefficients
        acChrmTB = {( 0, 0):( 2,'00'), #EOB
                    ( 0, 1):( 2,'01'),               ( 0, 2):( 3,'100'),
                    ( 0, 3):( 4,'1010'),             ( 0, 4):( 5,'11000'),
                    ( 0, 5):( 5,'11001'),            ( 0, 6):( 6,'111000'),
                    ( 0, 7):( 7,'1111000'),          ( 0, 8):( 9,'111110100'),
                    ( 0, 9):(10,'1111110110'),       ( 0,10):(12,'111111110100'),
                    ( 1, 1):( 4,'1011'),             ( 1, 2):( 6,'111001'),
                    ( 1, 3):( 8,'11110110'),         ( 1, 4):( 9,'111110101'),
                    ( 1, 5):(11,'11111110110'),      ( 1, 6):(12,'111111110101'),
                    ( 1, 7):(16,'1111111110001000'), ( 1, 8):(16,'1111111110001001'),
                    ( 1, 9):(16,'1111111110001010'), ( 1,10):(16,'1111111110001011'),
                    ( 2, 1):( 5,'11010'),            ( 2, 2):( 8,'11110111'),
                    ( 2, 3):(10,'1111110111'),       ( 2, 4):(12,'111111110110'),
                    ( 2, 5):(15,'111111111000010'),  ( 2, 6):(16,'1111111110001100'),
                    ( 2, 7):(16,'1111111110001101'), ( 2, 8):(16,'1111111110001110'),
                    ( 2, 9):(16,'1111111110001111'), ( 2,10):(16,'1111111110010000'),
                    ( 3, 1):( 5,'11011'),            ( 3, 2):( 8,'11111000'),
                    ( 3, 3):(10,'1111111000'),       ( 3, 4):(12,'111111110111'),
                    ( 3, 5):(16,'1111111110010001'), ( 3, 6):(16,'1111111110010010'),
                    ( 3, 7):(16,'1111111110010011'), ( 3, 8):(16,'1111111110010100'),
                    ( 3, 9):(16,'1111111110010101'), ( 3,10):(16,'1111111110010110'),
                    ( 4, 1):( 6,'111010'),           ( 4, 2):( 9,'111110110'),
                    ( 4, 3):(16,'1111111110010111'), ( 4, 4):(16,'1111111110011000'),
                    ( 4, 5):(16,'1111111110011001'), ( 4, 6):(16,'1111111110011010'),
                    ( 4, 7):(16,'1111111110011011'), ( 4, 8):(16,'1111111110011100'),
                    ( 4, 9):(16,'1111111110011101'), ( 4,10):(16,'1111111110011110'),
                    ( 5, 1):( 6,'111011'),           ( 5, 2):(10,'1111111001'),
                    ( 5, 3):(16,'1111111110011111'), ( 5, 4):(16,'1111111110100000'),
                    ( 5, 5):(16,'1111111110100001'), ( 5, 6):(16,'1111111110100010'),
                    ( 5, 7):(16,'1111111110100011'), ( 5, 8):(16,'1111111110100100'),
                    ( 5, 9):(16,'1111111110100101'), ( 5,10):(16,'1111111110100110'),
                    ( 6, 1):( 7,'1111001'),          ( 6, 2):(11,'11111110111'),
                    ( 6, 3):(16,'1111111110100111'), ( 6, 4):(16,'1111111110101000'),
                    ( 6, 5):(16,'1111111110101001'), ( 6, 6):(16,'1111111110101010'),
                    ( 6, 7):(16,'1111111110101011'), ( 6, 8):(16,'1111111110101100'),
                    ( 6, 9):(16,'1111111110101101'), ( 6,10):(16,'1111111110101110'),
                    ( 7, 1):( 7,'1111010'),          ( 7, 2):(11,'11111111000'),
                    ( 7, 3):(16,'1111111110101111'), ( 7, 4):(16,'1111111110110000'),
                    ( 7, 5):(16,'1111111110110001'), ( 7, 6):(16,'1111111110110010'),
                    ( 7, 7):(16,'1111111110110011'), ( 7, 8):(16,'1111111110110100'),
                    ( 7, 9):(16,'1111111110110101'), ( 7,10):(16,'1111111110110110'),
                    ( 8, 1):( 8,'11111001'),         ( 8, 2):(16,'1111111110110111'),
                    ( 8, 3):(16,'1111111110111000'), ( 8, 4):(16,'1111111110111001'),
                    ( 8, 5):(16,'1111111110111010'), ( 8, 6):(16,'1111111110111011'),
                    ( 8, 7):(16,'1111111110111100'), ( 8, 8):(16,'1111111110111101'),
                    ( 8, 9):(16,'1111111110111110'), ( 8,10):(16,'1111111110111111'),
                    ( 9, 1):( 9,'111110111'),        ( 9, 2):(16,'1111111111000000'),
                    ( 9, 3):(16,'1111111111000001'), ( 9, 4):(16,'1111111111000010'),
                    ( 9, 5):(16,'1111111111000011'), ( 9, 6):(16,'1111111111000100'),
                    ( 9, 7):(16,'1111111111000101'), ( 9, 8):(16,'1111111111000110'),
                    ( 9, 9):(16,'1111111111000111'), ( 9,10):(16,'1111111111001000'),
                    (10, 1):( 9,'111111000'),        (10, 2):(16,'1111111111001001'),
                    (10, 3):(16,'1111111111001010'), (10, 4):(16,'1111111111001011'),
                    (10, 5):(16,'1111111111001100'), (10, 6):(16,'1111111111001101'),
                    (10, 7):(16,'1111111111001110'), (10, 8):(16,'1111111111001111'),
                    (10, 9):(16,'1111111111010000'), (10,10):(16,'1111111111010001'),
                    (11, 1):( 9,'111111001'),        (11, 2):(16,'1111111111010010'),
                    (11, 3):(16,'1111111111010011'), (11, 4):(16,'1111111111010100'),
                    (11, 5):(16,'1111111111010101'), (11, 6):(16,'1111111111010110'),
                    (11, 7):(16,'1111111111010111'), (11, 8):(16,'1111111111011000'),
                    (11, 9):(16,'1111111111011001'), (11,10):(16,'1111111111011010'),
                    (12, 1):( 9,'111111010'),        (12, 2):(16,'1111111111011011'),
                    (12, 3):(16,'1111111111011100'), (12, 4):(16,'1111111111011101'),
                    (12, 5):(16,'1111111111011110'), (12, 6):(16,'1111111111011111'),
                    (12, 7):(16,'1111111111100000'), (12, 8):(16,'1111111111100001'),
                    (12, 9):(16,'1111111111100010'), (12,10):(16,'1111111111100011'),
                    (13, 1):(11,'11111111001'),      (13, 2):(16,'1111111111100100'),
                    (13, 3):(16,'1111111111100101'), (13, 4):(16,'1111111111100110'),
                    (13, 5):(16,'1111111111100111'), (13, 6):(16,'1111111111101000'),
                    (13, 7):(16,'1111111111101001'), (13, 8):(16,'1111111111101010'),
                    (13, 9):(16,'1111111111101011'), (13,10):(16,'1111111111101100'),
                    (14, 1):(14,'11111111100000'),   (14, 2):(16,'1111111111101101'),
                    (14, 3):(16,'1111111111101110'), (14, 4):(16,'1111111111101111'),
                    (14, 5):(16,'1111111111110000'), (14, 6):(16,'1111111111110001'),
                    (14, 7):(16,'1111111111110010'), (14, 8):(16,'1111111111110011'),
                    (14, 9):(16,'1111111111110100'), (14,10):(16,'1111111111110101'),
                    (15, 0):(10,'1111111010'),       #(ZRL)
                    (15, 1):(15,'111111111000011'),  (15, 2):(16,'1111111111110110'),
                    (15, 3):(16,'1111111111110111'), (15, 4):(16,'1111111111111000'),
                    (15, 5):(16,'1111111111111001'), (15, 6):(16,'1111111111111010'),
                    (15, 7):(16,'1111111111111011'), (15, 8):(16,'1111111111111100'),
                    (15, 9):(16,'1111111111111101'), (15,10):(16,'1111111111111110')}
                        
        return (dcLumaTB, dcChroTB, acLumaTB, acChrmTB)
            
    def genQntb(self, qualy):
            
        '''
        # MPEG Encoder: \n
        Method: genQntb (self, qualy) -> qz \n
        About: Generates the standard quantization table. \n
        '''
        fact = qualy
        Z = np.array([[[16., 17., 17.], [11., 18., 18.], [10., 24., 24.], [16., 47., 47.], [124., 99., 99.], [140., 99., 99.], [151., 99., 99.], [161., 99., 99.]],
                  [[12., 18., 18.], [12., 21., 21.], [14., 26., 26.], [19., 66., 66.], [ 26., 99., 99.], [158., 99., 99.], [160., 99., 99.], [155., 99., 99.]],
                  [[14., 24., 24.], [13., 26., 26.], [16., 56., 56.], [24., 99., 99.], [ 40., 99., 99.], [157., 99., 99.], [169., 99., 99.], [156., 99., 99.]],
                  [[14., 47., 47.], [17., 66., 66.], [22., 99., 99.], [29., 99., 99.], [ 51., 99., 99.], [187., 99., 99.], [180., 99., 99.], [162., 99., 99.]],
                  [[18., 99., 99.], [22., 99., 99.], [37., 99., 99.], [56., 99., 99.], [ 68., 99., 99.], [109., 99., 99.], [103., 99., 99.], [177., 99., 99.]],
                  [[24., 99., 99.], [35., 99., 99.], [55., 99., 99.], [64., 99., 99.], [ 81., 99., 99.], [104., 99., 99.], [113., 99., 99.], [192., 99., 99.]],
                  [[49., 99., 99.], [64., 99., 99.], [78., 99., 99.], [87., 99., 99.], [103., 99., 99.], [121., 99., 99.], [120., 99., 99.], [101., 99., 99.]],
                  [[72., 99., 99.], [92., 99., 99.], [95., 99., 99.], [98., 99., 99.], [112., 99., 99.], [100., 99., 99.], [103., 99., 99.], [199., 99., 99.]]])
        if qualy < 1 : fact = 1
        if qualy > 99: fact = 99
        if qualy < 50:
            qualy = 5000 / fact
        else:
            qualy = 200 - 2*fact
            
        qZ = ((Z*qualy) + 50)/100
        qZ[qZ<1] = 1
        qZ[qZ>255] = 255
        
        return qZ

if __name__ == "__main__":
    root = Tk()
    root.withdraw()
    
    image = cv2.imread(askopenfilename(parent=root, title="Enter with a file name.").__str__())
    test = ep(image,15, 50)
    xm, ym, x, y = test.run()