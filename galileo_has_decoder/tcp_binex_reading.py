#!/usr/bin/env python

'''
BINEX TCP reading class

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

import struct
import math
import time
from galileo_has_decoder.utils import bits2Bytes, gpst2time
from galileo_has_decoder.utils_binex import Binex_Record, readUbnxi, BinexError
from galileo_has_decoder.has_classes import HAS_Storage
from galileo_has_decoder.ssr_converter import SSR_Converter
from galileo_has_decoder.tcp_server import TCP_Server

class StreamError(Exception):
  #Base File Error class
  pass

class TCP_Binex_Reader:
  tcp = None
  def __init__(self, src, msgnum=0):
    addr, port = src.split(":")
    self.source = TCP_Server(addr, int(port))
    self.has_storage = HAS_Storage()
    self.msgnum = msgnum
    self.pppWiz = False

  def read(self, src=None, converter=None, output=None, mode='m', x=None, compact=True, HRclk=False, lowerUDI=True, verbose=0):
    j = cnavs = hasnum = 0
    timecurr = timestop = 0
    if src != None:
      self.source.close()
      addr, port = src.split(":")
      self.source = TCP_Server(addr, int(port))
    if converter is not None:
      if converter.pppWiz:
        self.output = output
        self.pppWiz = True
    if x != None: 
      if mode == "m":
        self.msgnum = x
      elif mode=="t":
        timecurr = time.time() 
        timestop = x + time.time()

    j = 0
    content = self.receiveData(b'', verbose=verbose)
    cnavs = 0
    hasnum=0
    while (mode=="m" and (j<self.msgnum or self.msgnum==0)) or (mode=="t" and timecurr < timestop):
      if timecurr != 0:
        timecurr = time.time()
      j += 1
      if verbose >= 5:
          print("Message " + str(j))
      try:
          content = self.findMessage(content, verbose)
      except StreamError:
          j-=1
          print("Warning: EOS reached")
          break
      if verbose >= 5:
          print("   Found start of block")
      binex = Binex_Record()
      while True:
        try:
          i = binex.readBlock(content)
          break
        except IndexError:
          content = self.receiveData(content, verbose=verbose)
        except BinexError:
          content = self.receiveData(content, verbose=verbose)
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
      content = content[i:]
    if verbose>=1:
        print("Out of "+str(j)+" messages, "+str(cnavs)+" were C/Nav messages. "+str(hasnum)
          +" HAS messages have successfully been decoded and converted.")

  def findMessage(self, stream, verbose=0):
    syncbytes = [0xc2, 0xe2, 0xd2, 
                 0xf2, 0xb4, 0xb0]
    i=0
    mode = -1
    idxs = [-1,-1,-1]
    while True:
        idxs[0] = i+stream[i:].find(b'\x01')
        idxs[1] = i+stream[i:].find(b'\xb4')
        idxs[2] = i+stream[i:].find(b'\xb0')
        if idxs[0]!= -1 and (idxs[0]< idxs[1] or idxs[1]==-1) and (idxs[0]< idxs[2] or idxs[2]==-1):
          if stream[idxs[0]+1] not in syncbytes and stream[idxs[0]-1] not in syncbytes:
            i = idxs[0]+1
            continue
          if (stream[idxs[0]-1] in syncbytes[:-2]):
            mode = 0
            break
        elif idxs[1] != -1 and (idxs[1]< idxs[2] or idxs[2]==-1):
          mode = 1
          break
        elif idxs[2] != -1:
          mode = 2
          break
        else: 
          stream = self.receiveData(stream, verbose=verbose)
    if self.pppWiz and idxs[mode]>0:
        self.output.write(stream[:idxs[mode]], 1, 10)
    if mode == 0:
      return stream[idxs[mode]-1:]
    return stream[idxs[mode]:]

  def receiveData(self, stream, x=1024, verbose=0):
    if self.source.alive:
        rec = self.source.read(x, 0.1)
        if rec == -1: 
            if verbose>2:
                print("WARNING: Running out of data. Shutting down in 300s")
            rec = self.source.read(x, 300)
            if rec == -1:
                self.source.close()
                raise StreamError("EOS reached: Ending operation.")
        stream += rec
        if rec == b"":
            self.source.close()
            raise StreamError("WARNING: Empty string received, closing TCP and finishing work.")
        return stream
    raise StreamError("EOS reached: Ending operation.")