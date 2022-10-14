#!/usr/bin/env python

'''
Serial reading classes

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

import serial
import struct
import time
from galileo_has_decoder.utils import bits2Bytes
from galileo_has_decoder.utils_sbf import SBF_Block, IONO_Block
from galileo_has_decoder.utils_binex import Binex_Record, readUbnxi, BinexError
from galileo_has_decoder.has_classes import HAS_Storage
from galileo_has_decoder.ssr_converter import SSR_Converter
from galileo_has_decoder.tcp_server import TCP_Server

class FileError(Exception):
  #Base File Error class
  pass

class Serial_SBF_Reader:
  serial = None
  def __init__(self, port, baudr, msgnum=0):
    self.serial = serial.Serial(port, baudrate=baudr)
    self.has_storage = HAS_Storage()
    self.msgnum = msgnum
    self.pppWiz = False

  def read(self, converter=None, output=None, mode='m', x=None, compact=True, HRclk=False, lowerUDI=True, verbose=0):
    j = cnavs = hasnum = 0
    timecurr = timestop = 0
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
    while (mode=="m" and (j<self.msgnum or self.msgnum==0)) or (mode=="t" and timecurr < timestop):
      if timecurr != 0:
        timecurr = time.time()
      j += 1
      if verbose >= 4:
        print("Message " + str(j))
      _data = self.serial.read_until(b'$@')
      if self.pppWiz and len(_data)>0:
        self.output.write(_data, 1, 12)
      if verbose >= 4:
        print("   Found start of block")
      i = 0
      header = self.serial.read(6)
      if self.pppWiz and len(header)>0:
        self.output.write(header, 1, 12)
      header, i = struct.unpack("<HHH", header), i+6
      header = list(header)
      if header[2] % 4 != 0:
        if verbose >= 4:
          print("Invalid header, continuing search...")
        continue
      _crc = header[0]
      blockType = header[1]
      blockLength = header[2]-8
      block = self.serial.read(blockLength)
      if self.pppWiz and len(block)>0:
        self.output.write(block, 1, 12)
      if blockType&65528 == 4024:
        if blockType&7 == 0:
          #_______________________
          #4024 Block: HAS Message
          cnavs += 1
          hasbyteL = 4+2+6*1+16*4
          pad = blockLength-hasbyteL
          line = list(struct.unpack("<IHBBBBBB16I"+str(pad)+"x", block))
          if verbose >= 4:
            print("   CNAV Block")
          #Use Septentrio CRC check
          if line[3] == 1:
            sbf = SBF_Block(header, line)
            has_msg = sbf.returnBinary()
            #sbf.printNavBits()
            if self.has_storage.feedMessage(has_msg, line[0]/1000, verbose=verbose):
              hasnum += 1
              decoded_msg = self.has_storage.lastMessage  
              if converter != None:
                tow = self.has_storage.lastMessage_tow
                converted = converter.convertMessage(decoded_msg, compact=compact, HRclk=HRclk, tow=tow, lowerUDI=lowerUDI, verbose=verbose)
                if output != None and converted != None:
                  for msg_conv in converted:
                    msg_bytes = bits2Bytes(msg_conv)
                    output.write(msg_bytes)
              pass
          else:
            if verbose >= 4:
                print("CRC error: "+str(line[3]))
          #_______________________
        elif blockType&7 == 6:
          #_______________________
          #4030 Block: Galileo Ionosphere
          #Ionosphere blocks are not yet supported
          # hasbyteL = 4+2+2*1+3*4+1
          # pad = blockLength-hasbyteL
          # line = list(struct.unpack("<IHBB3fB"+str(pad)+"x"))
          if verbose >= 5:
            print("   IONO Block")
          # if CRC Passed:
          # self.iono_msgs += [IONO_Block(header, line)]
          #_______________________
        elif verbose >= 5:
          print("   Err: Other Nav block: " + str(blockType))
      elif verbose >= 5:
        print("   Err: Non-CNAV block: " + str(blockType))
    if verbose>=1:
      print("Out of "+str(j)+" messages, "+str(cnavs)+" were C/Nav messages. "+str(hasnum)
          +" HAS messages have successfully been decoded and converted.")

class Serial_Binex_Reader:
  serial = None
  def __init__(self, port, baudr=115200, msgnum=0):
    self.serial = serial.Serial(port, baudrate=baudr)
    self.has_storage = HAS_Storage()
    self.msgnum = msgnum
    self.pppWiz = False

  def read(self, converter=None, output=None, mode='m', x=None, compact=True, HRclk=False, lowerUDI=True, verbose=0):
    j = cnavs = hasnum = 0
    timecurr = timestop = 0
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
    while (mode=="m" and (j<self.msgnum or self.msgnum==0)) or (mode=="t" and timecurr < timestop):
      if timecurr != 0:
        timecurr = time.time()
      j += 1
      if verbose >= 4:
          print("Message " + str(j))
      block = self.serial.read_until(b'\x01')
      if self.pppWiz and len(block)>0:
        self.output.write(block, 1, 10)
      if verbose >= 5:
        print("  Pontential Block found")
      if len(block)>=2:
        if block[-2] in Binex_Record.syncbytes[:-2]:
          #Forward readable record found. Now read length & then rest
          block = block[-2:] + self.serial.read(4)
          length, _ = readUbnxi(block, 2)
          block += self.serial.read(length + Binex_Record.crcLen(length))
          if block[0] in Binex_Record.syncbytes[2:]:
            try:
              block += self.serial.read_until(Binex_Record.termBytes[block[0]], 5)
            except TypeError:
              continue
          if self.pppWiz and len(block[2:])>0:
            self.output.write(block[2:], 1, 10)
        else:
          temp = self.serial.read(size=1)
          if self.pppWiz and len(temp)>0:
            self.output.write(temp, 1, 10)
          if temp in Binex_Record.syncbytes[-2:]:
            #Reverse readable record found. Read reverse length & then drop all but message
            block += temp
            total_length, i = readUbnxi(block[-6:-2][::-1])
            if self.pppWiz and len(block[:-2-i-total_length])>0:
              self.output.write(block[-2-i-total_length], 1, 10)
            block = block[-2-i-total_length:]
          else: block = None
      else: 
        if self.pppWiz and len(block)>0:
          self.output.write(block, 1, 10)
        block = None
      if block != None:
        if verbose >= 5:
            print("   Found start of block")
        binex = Binex_Record()
        try:
          binex.readBlock(block)
        except BinexError:
          continue
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
            print("     Faulty- or non-C/Nav block")
      else: j-= 1
    if verbose>=1:
      print("Out of "+str(j)+" messages, "+str(cnavs)+" were C/Nav messages. "+str(hasnum)
          +" HAS messages have successfully been decoded and converted.")
