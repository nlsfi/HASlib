#!/usr/bin/env python

'''
File output classes

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

import math

class File_Writer:
    path = "ssr_messages.out"
    file = None

    def __init__(self, path=None):
        if path != None:
            self.path = path
        self.file = open(self.path, "wb")

    def write(self, msg):
        self.file.write(msg)

    def close(self):
        self.file.close()

class PPP_Wiz_Writer(File_Writer):
    path = "ssr_messages.out"
    def __init__(self, path=None, epch=0, mode=3):
        self.mode = mode
        if mode == 3:
            if path != None:
                self.path = path
            self.file = open(self.path, "w")
        self.epch = int(epch)

    def write(self, msg, n, fmt, epch=0):
        if epch != 0: self.epch = int(epch)
        for i in range(math.ceil(len(msg)/50)):
            subs = msg[i*50:(i+1)*50]
            out = "{0} {1} {2} {3}\n".format(n, fmt, self.epch, "".join(['0x{0:0{1}X}'.format(x,2)[2:] for x in subs]))
            if self.mode == 3:
                self.file.write(out)
            elif self.mode == 4:
                print(out, end="")