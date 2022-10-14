#!/usr/bin/env python

'''
SBF file reading class

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

import struct
import math
from galileo_has_decoder.utils import bits2Bytes, gpst2time
from galileo_has_decoder.utils_sbf import splitStream, SBF_Block, IONO_Block
from galileo_has_decoder.has_classes import HAS_Storage
from galileo_has_decoder.ssr_converter import SSR_Converter
from galileo_has_decoder.tcp_server import TCP_Server

class FileError(Exception):
  #Base File Error class
  pass

class SBF_Reader:
  file = None
  has_storage = None
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
        print("Message no. " + str(j))
      try:
        content, pC = self.findMessage(content, pC, verbose)
      except(FileError):
        j-=1
        if verbose >= 1:
          print("EOF REACHED: Ending operation")
        break
      if verbose >= 5:
        print("   Found start of block")
      i = 0
      header, i = struct.unpack("<HHH", content[i:i+6]), i+6
      header = list(header)
      if header[2] % 4 != 0:
        if verbose >= 5:
          print("SBF Reader: Invalid header, continuing search...")
        continue
      _crc = header[0]
      blockType = header[1]
      blockLength = header[2]-8
      if blockType&65528 == 4024:
        block = content[i:i+blockLength]
        content = content[i+blockLength:]
        if blockType&7 == 0:
          #_______________________
          #4024 Block: C/NAV Message
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
                    gpst2time(line[1], line[0]/1000)
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
            print("   SBF IONO Block")
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

  def findMessage(self, stream, pC, verbose=0):
    prefix = bytearray([36, 64])
    while True:
        idx = stream.find(prefix)
        if len(stream[idx:]) < 84 or idx == -1:
          if pC >= self.pNum-1:
            raise FileError("EOF REACHED: Ending operation")
          else:
            pC += 1
            stream = stream + self.pages[pC]
            #test
            if verbose >= 3:
              print("SBF File: Next page, " + str(pC+1) + "/" + str(self.pNum))
            continue
        elif idx > -1:
          if self.pppWiz and idx>1:
            self.output.write(prefix + stream[:idx], 1, 12)
          return stream[idx+2:], pC
