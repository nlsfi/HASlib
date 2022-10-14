#!/usr/bin/env python

'''
SBF TCP reading class

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

import struct
import math
import time
from galileo_has_decoder.utils import bits2Bytes, gpst2time
from galileo_has_decoder.utils_sbf import splitStream, SBF_Block, IONO_Block
from galileo_has_decoder.has_classes import HAS_Storage
from galileo_has_decoder.ssr_converter import SSR_Converter
from galileo_has_decoder.tcp_server import TCP_Server

#Testimport
import time

class StreamError(Exception):
  #Base Stream Error class
  pass

class TCP_SBF_Reader:
  has_storage = None
  def __init__(self, src, msgnum=0):
    addr, port = src.split(":")
    self.source = TCP_Server(addr, int(port))
    self.has_storage = HAS_Storage()
    self.msgnum = msgnum
    self.pppWiz = False

  def read(self, src=None, converter=None, output=None, mode='m', x=None, compact=True, HRclk=False, lowerUDI=True, verbose=0):
    i = 0
    content = b''
    timecurr = timestop = 0
    j = cnavs = hasnum = 0
    if x != None: 
      if mode == "m":
        self.msgnum = x
      elif mode=="t":
        timecurr = time.time() 
        timestop = x + time.time()
    if src != None:
      self.source.close()
      addr, port = src.split(":")
      self.source = TCP_Server(addr, int(port))
    
    if converter is not None:
      if converter.pppWiz:
        self.output = output
        self.pppWiz = True

    while (mode=="m" and (j<self.msgnum or self.msgnum==0)) or (mode=="t" and timecurr < timestop):
      if timecurr != 0:
        timecurr = time.time()
      j += 1
      if verbose >= 5:
        print("Message no. " + str(j))
      try:
        content = self.findMessage(content, verbose, j==1)
      except(StreamError):
        j-=1
        print("TCP closed and last message read: Ending operation")
        break
      if verbose >= 5:
        print("   Found start of block")
      i = 0
      while len(content)<6:
        content = self.receiveData(content, verbose=verbose)
      header, i = struct.unpack("<HHH", content[i:i+6]), i+6
      header = list(header)
      if header[2] % 4 != 0:
        if verbose >= 5:
          print("SBF Reader: Invalid header, continuing search...")
        continue
      _crc = header[0]
      blockType = header[1]
      if blockType>10000:
        continue
      blockLength = header[2]-8
      while(len(content[6:])<blockLength):
        content = self.receiveData(content, verbose=verbose)
      if blockType&65528 == 4024:
        block = content[i:i+blockLength]
        content = content[i+blockLength:]
        if blockType&7 == 0:
          #_______________________
          #4024 Block: HAS Message
          cnavs += 1
          hasbyteL = 4+2+6*1+16*4
          pad = blockLength-hasbyteL
          line, i = list(struct.unpack("<IHBBBBBB16I"+str(pad)+"x", block[:i+blockLength])), i+blockLength 
          if verbose >= 5:
            print("   CNAV Block")
          #Use Septentrio CRC check
          if line[3] == 1:
            sbf = SBF_Block(header, line)
            has_msg = sbf.returnBinary()
            if self.has_storage.feedMessage(has_msg, line[0]/1000, verbose=verbose):
              hasnum += 1
              if converter != None:
                decoded_msg = self.has_storage.lastMessage
                tow = self.has_storage.lastMessage_tow
                converted = converter.convertMessage(decoded_msg, compact=compact, HRclk=HRclk, tow=tow, lowerUDI=lowerUDI, verbose=verbose)
                if output != None and converted != None:
                  for msg_conv in converted:
                    msg_bytes = bits2Bytes(msg_conv)
                    if self.pppWiz:
                      output.write(msg_bytes, 2, 1, gpst2time(line[1], line[0]/1000))
                    else:
                      output.write(msg_bytes)
              pass
          else:
            if verbose >= 5:
                print("SBF Reader: CRC error: "+str(line[3]))
          #_______________________
        elif blockType&7 == 6:
          #_______________________
          #4030 Block: Galileo Ionosphere
          #hasbyteL = 4+2+2*1+3*4+1
          #pad = blockLength-hasbyteL
          #line, i = list(struct.unpack("<IHBB3fB"+str(pad)+"x", block[i:i+blockLength])), i+blockLength 
          if verbose >= 5:
            print("   IONO Block")
          # if CRC Passed:
          #self.iono_msgs += [IONO_Block(header, line)]
          #_______________________
        elif verbose >= 5:
          print("   Err: Other Nav block: " + str(blockType))
        else:
          pass
      else:
        i = i+blockLength
        if verbose >= 5:
          print("   Err: Non-CNAV block: " + str(blockType))
    if verbose>=1:
      print("Out of "+str(j)+" messages, "+str(cnavs)+" were C/Nav messages. "+str(hasnum)
          +" HAS messages have successfully been decoded and converted.")

  def findMessage(self, stream, verbose=0, start=False):
    prefix = bytearray([36, 64])
    noRes = False
    while True:
      if self.source.alive:
        rec = self.source.read(1024, 0.001)
        if rec == -1 and (len(stream)<8 or noRes) and not start: 
          if verbose>2:
            print("WARNING: Running out of data. Shutting down in 300s")
          rec = self.source.read(1024, 300)
          if rec == -1:
            self.source.close()
            raise StreamError("EOS reached: Ending operation.")
        if rec != -1:
          stream += rec
        if rec == b"":
          if verbose>=1:
            print("WARNING: Empty string received, closing TCP and finishing work.")
          self.source.close()
      idx = stream.find(prefix)
      if idx > -1:
        if self.pppWiz:
          self.output.write(stream[:idx+2], 1, 12)
        return stream[idx+2:]
      if not self.source.alive:
        raise StreamError("TCP closed and last message read: Ending operation")
      noRes = True

  def receiveData(self, stream, verbose=0):
    if self.source.alive:
      rec = self.source.read(1024, 0.1)
      if rec == -1: 
        if verbose>2:
          print("WARNING: Running out of data. Shutting down in 300s")
        rec = self.source.read(1024, 300)
        if rec == -1:
          self.source.close()
          raise StreamError("EOS reached: Ending operation.")
      stream += rec
      if rec == b"":
        self.source.close()
        raise StreamError("WARNING: Empty string received, closing TCP and finishing work.")
      return stream
    raise StreamError("EOS reached: Ending operation.")

if __name__ == "__main__":
  print("Start")

  converter = SSR_Converter(mode=1, verbose=1)
  sbf_reader = TCP_SBF_Reader("localhost:6948", 3000)
  sbf_reader.read(converter=converter)