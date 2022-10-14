#!/usr/bin/env python

'''
BINEX reading & storing utils

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
Modified 15/09/2022 by Tuomo Malkamaki / FGI to notify the user of IndexError exceptio readForward function
'''

import struct
import datetime
import numpy as np
PAGELENGTH = 64

class BinexError(Exception):
    #Base class for Binex errors
    pass

def splitStream(stream, x):
  l = len(stream)
  pL = int(l/x)
  split = []
  for i in range(x):
    split += [stream[i*pL:(i+1)*pL]]
  return split

def readUbnxi(msg, j=0, bigE=True):
    ubnxi = 0
    for i in range(j, j+4):
        if i-j<3:
            flag = (msg[i] & 128) >> 7
            if bigE:
                ubnxi = (ubnxi << 7) + (msg[i] & 127)
            else:
                ubnxi = (ubnxi) + ((msg[i] & 127)<< (7*i))
            if not flag:
                break
        else:
            ubnxi = (ubnxi) + (msg[i] << 21)
    return ubnxi, i+1

class Binex_Record:

    syncByte = None
    recordID = None
    recordLen = None
    bitFlippedLen = None
    message = None
    parity = None
    layout = None
    termBytes = {0xd2:0xb4, 0xf2:0xb0, 0xd8:0xe4, 0xf8:0xe0,
                 0xb4:0xd2, 0xb0:0xf2, 0xe4:0xd8, 0xe0:0xd8}
    syncbytes = [0xc2, 0xe2, 0xd2,
                 0xf2, 0xb4, 0xb0]
    def __init__(self):
        pass

    def readBlock(self, msg, i=0):
        self.syncByte = msg[i]
        i += 1
        self.layout = self.detLayout(self.syncByte)
        if self.layout[1]:
            raise BinexError("Enhanced CRC records not yet supported")
        if self.layout[2]: i = self.readForward(msg, i)
        else: i = self.readBackward(msg, i)
        return i

    def returnBinary(self):
        return self.subrecord.returnBinary()

    def decodeBlock(self, verbose=0):
        if self.message != None:
            self.subrecord = Binex_Subrecord_Block()
            suc = self.subrecord.readBinex(self.message, verbose=verbose)
            return suc
        return False

    def readForward(self, msg, i, readSimple=False):
        self.recordID, i = readUbnxi(msg, i, self.layout[3])
        self.length , i = readUbnxi(msg, i, self.layout[3])
        if len(msg)<self.length+20:
            raise BinexError("Warn: Buffer ran out while reading message")
        if self.layout[1]:
            self.bitFlippedLen, i = readUbnxi(msg, i, self.layout[3])
        self.message, i = msg[i:i+self.length], i+self.length
        try:
            self.parity, i = self.readCRC(msg, i, self.layout[3])
        except IndexError:
            print("Index Error exception raised in utils_binex.py readForward function")
            #pass
        if not self.layout[0] and not readSimple:
            while msg[i] != self.termBytes[self.syncByte]:
                i += 1
        return i

    def readBackward(self, msg, i):
        self.length_rev, i = readUbnxi(msg, i, self.layout[3])
        if len(msg)<self.length_rev+20:
            raise BinexError("Warn: Buffer ran out while reading message")
        fullMess, i =  msg[i:i+self.length_rev], i+self.length_rev
        msg_rev = fullMess[::-1]
        self.readForward(msg_rev, 0, readSimple=True)
        return i

    def crcLen(self, l=None):
        if l == None:
            if type(self) == int:
                l = self
                if l<120:
                    return 1
                elif l<4088:
                    return 2
                return 16
            l = self.length
        if not self.layout[1] or l!=None:
            if l<120:
                return 1
            elif l<4088:
                return 2
            return 16

    def readCRC(self, msg, i=0, bigE=True):
        l = i - 1
        if l < 128:
            return msg[i], i+1
        elif not bigE:
            if l < 4096:
                return (msg[i+1]<<8)+msg[i], i+2
            elif l < 1048576:
                return (msg[i+3]<<24)+(msg[i+2]<<16)+(msg[i+1]<<8)+msg[i], i+4
        elif bigE:
            if l < 4096:
                return (msg[i]<<8)+msg[i+1], i+2
            elif l < 1048576:
                return (msg[i]<<24)+(msg[i+1]<<16)+(msg[i+2]<<8)+msg[i+3], i+4
        raise BinexError("Messages longer than ~1MB not supported")

    def detLayout(self, syncB):
        forwardSync = [0xc2, 0xe2, 0xc8, 0xe8]
        reverseSync = [0xd2, 0xf2, 0xd8, 0xf8]
        #reverseTerm = [0xb4, 0xb0, 0xe4, 0xe0]
        forward = syncB in forwardSync or syncB in reverseSync
        begin = True
        if forward: enhanced = bool(syncB & 8)
        else:
            begin = syncB in reverseSync
            if begin: enhanced = bool(syncB & 2)
            else: enhanced = bool(syncB & 64)
        if begin: bigE = bool(syncB & 32)
        else: bigE = not bool(syncB & 4)
        return forward, enhanced, begin, bigE

class Binex_Subrecord_Block:
    pLen = {2:29, 7:31, 11:29, 20:62}
    subrecord = None
    transTime = None
    transTime_ms = None
    prn = None
    source = None
    crc_passed = None
    mID_avail = None
    mID = None
    navbits = None
    def __init__(self):
        pass

    def readBinex(self, msg, i=0, verbose=0):
        self.subrecord, i = readUbnxi(msg, i)
        if self.subrecord != 0x44:
            if verbose >= 3:
                print("Other rec:",self.subrecord)
            return 0
        data, i = struct.unpack(">IHBB", msg[i:i+8]), i+8
        self.transTime = data[0]
        self.transTime_ms = data[1]
        self.tow = self.timeOfWeek(data[0], data[1])
        self.prn = data[2]
        self.source = data[3]&31 -1 #-1 is a guess
        self.crc_passed = (data[3]&32)>>5
        self.mID_avail = (data[3]&64)>>6
        if self.source != 20:
            return 0
        if self.mID_avail:
            self.mID, i = readUbnxi(msg, i)
        self.navbits = msg[i:i+self.pLen[self.source]]
        return self.crc_passed #i+self.pLen[self.source]

    def returnBinary(self, cutRes=False):
        msg = ""
        for b in self.navbits:
            msg = msg + np.binary_repr(b,8)
        return msg[14*cutRes:]

    def epochTime(self, minutes=None, millis=None):
        if minutes == None or millis == None:
            return int(self.transTime*60+315964800+self.transTime_ms/1000)
        return int(minutes*60+315964800+millis/1000)

    def timeOfWeek(self, minutes, millis):
        bot = datetime.datetime(1980, 1, 6)
        ms = datetime.timedelta(milliseconds=millis)
        sSinceBot = datetime.timedelta(minutes=minutes)
        t = bot + sSinceBot
        w_begin = t - datetime.timedelta(t.weekday(), hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond)
        tow = (sSinceBot - (w_begin-bot)) + ms
        return(tow.total_seconds())
