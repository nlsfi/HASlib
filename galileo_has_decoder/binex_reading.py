#!/usr/bin/env python

'''
BINEX File Reading class

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

import struct
import math
from galileo_has_decoder.utils import bits2Bytes, gpst2time
from galileo_has_decoder.utils_binex import Binex_Record, splitStream
from galileo_has_decoder.has_classes import HAS_Storage
from galileo_has_decoder.ssr_converter import SSR_Converter
from galileo_has_decoder.tcp_server import TCP_Server

class FileError(Exception):
  #Base File Error class
  pass

class Binex_Reader:
  file = None
  def __init__(self, path, msgnum=0, skip=0):
    self.file = open(path, "rb")
    lines = self.file.readlines()
    lines = lines[int(skip*len(lines)):]
    self.pNum = math.ceil(len(lines) / 20000)
    self.fileC = b''.join(lines)
    self.pages = splitStream(self.fileC, self.pNum)
    self.has_storage = HAS_Storage()
    self.msgnum = msgnum
    self.pppWiz = False

  def read(self, path=None, converter=None, output=None, mode='m', x=None, compact=True, HRclk=False, lowerUDI=True, verbose=0):
    if mode != 'm':
        raise Exception("File Reading does only support message-number constraints")
    if x != None: self.msgnum = x
    if path != None:
      self.file = open(path, "rb")
      self.fileC = b''.join(self.file.readlines())
      self.pages = splitStream(self.fileC, self.pNum)

    if converter is not None:
        if converter.pppWiz:
            self.output = output
            self.pppWiz = True

    i = 0
    j = 0
    pC = 0
    content = self.pages[pC]
    cnavs = 0
    hasnum=0
    while j<self.msgnum or self.msgnum==0:
        j += 1
        if verbose >= 5:
            print("Message " + str(j))
        try:
            content, pC = self.findMessage(content, pC, i, verbose)
        except FileError:
            if verbose >= 1:
                print("EOF REACHED: Ending operation")
            break
        i = 1
        if verbose >= 5:
            print("   Found start of block")
        binex = Binex_Record()
        i = binex.readBlock(content)
        if binex.decodeBlock(verbose):
            cnavs+=1
            if self.has_storage.feedMessage(binex.returnBinary(), binex.subrecord.tow, verbose=verbose):
                hasnum += 1
                if converter != None:
                    decoded_msg = self.has_storage.lastMessage
                    tow = self.has_storage.lastMessage_tow
                    converted = converter.convertMessage(decoded_msg, compact=compact, HRclk=HRclk, tow=tow, lowerUDI=lowerUDI, verbose=verbose)
                    if output != None and converted != None:
                        for msg_conv in converted:
                            msg_bytes = bits2Bytes(msg_conv)
                            if self.pppWiz:
                                output.write(msg_bytes, 2, 1, binex.subrecord.epochTime())
                            else:
                                output.write(msg_bytes)   
        elif verbose >= 5:
            print("   Err: Non-CNAV block.")
    if verbose>=1:
        print("Out of "+str(j)+" messages, "+str(cnavs)+" were C/Nav messages. "+str(hasnum)
          +" HAS messages have successfully been decoded and converted.")

  def findMessage(self, stream, pC, i, verbose=0):
    syncbytes = [0xc2, 0xe2, 0xd2, 
                 0xf2, 0xb4, 0xb0]
    self.checkEnd(stream, i, pC)
    while True:
        while stream[i] not in syncbytes:
            i += 1
            if self.checkEnd(stream, i, pC):
                pC += 1
                stream = stream[i:] + self.pages[pC]
                i = 0
                if verbose >= 2:
                    print("Next page")
                continue
        if (stream[i+1] == 1 and stream[i] in syncbytes[:-2]) or (stream[i] in syncbytes[-2:]):
            break
        i+=1
    if self.pppWiz and i>0:
        self.output.write(stream[:i], 1, 10)
    return stream[i:], pC

  def checkEnd(self, stream, i, pC):
      if len(stream[i:]) < 78:
        if pC >= self.pNum-1:
            raise FileError("EOF REACHED: Ending operation")
        return True
      return False