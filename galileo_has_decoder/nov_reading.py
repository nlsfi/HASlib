#!/usr/bin/env python

'''
Novatel GALCNAVRAWPAGE file reading class

VER   DATE        AUTHOR
1.0.x   09/29/2023  Jaakko Yliaho / Uwasa
'''

import struct
import math
import binascii
from galileo_has_decoder.utils import bits2Bytes, gpst2time
from galileo_has_decoder.has_classes import HAS_Storage
from galileo_has_decoder.ssr_converter import SSR_Converter
from galileo_has_decoder.tcp_server import TCP_Server

class FileError(Exception):
  #Base File Error class
  pass

class NOV_Reader:
  file = None
  has_storage = None
  def __init__(self, path, msgnum=0, skip=0):
    self.file = open(path, "r")
    lines = self.file.readlines()
    self.lines = lines[int(skip):]
    self.numberOfRawPages = len(self.lines)
    self.has_storage = HAS_Storage()
    self.msgnum = msgnum
    self.pppWiz = False

  def read(self, path=None, converter=None, output=None, mode='m', x=None, compact=True, HRclk=False, lowerUDI=True, verbose=0):
    if mode != 'm':
      raise Exception("File Reading does only support message-number constraints")
    if x != None: self.msgnum = x
    
    if converter is not None:
      if converter.pppWiz:
        self.output = output
        self.pppWiz = True

    i = 0
    j = 0
    cnavs = 0
    hasnum=0
    currentLineNumber=0

    for logMessage in self.lines:
      logMessageFields=logMessage.split(";")
      if len(logMessageFields) != 2:
        if verbose >= 5:
          print("NOV-A Reader: Invalid line format on line " + str(currentLineNumber))
        currentLineNumber+=1
        continue

      headerFields=logMessageFields[0].split(",")
      if len(headerFields) != 10:
        if verbose >= 5:
          print("NOV-A Reader: Invalid line format, wrong number of header fields, on line " + str(currentLineNumber))
        currentLineNumber+=1
        continue

      dataCrcFields=logMessageFields[1].split("*")
      if len(dataCrcFields) != 2:
        if verbose >= 5:
          print("NOV-A Reader: Invalid line format, CRC missing, on line " + str(currentLineNumber))
        currentLineNumber+=1
        continue

      dataFields=dataCrcFields[0].split(",")
      crcField=str.rstrip(dataCrcFields[1])

      headerMessage=headerFields[0]
      if headerMessage != "#GALCNAVRAWPAGEA" and "#GALCNAVRAWPAGEA" in headerMessage:
        headerMessage="#GALCNAVRAWPAGEA"

      if headerMessage != "#GALCNAVRAWPAGEA":
        if verbose >= 5:
          print("NOV-A Reader, line "+str(currentLineNumber)+", not a raw C/NAV page: "+str(headerMessage))
        currentLineNumber+=1
        continue

      # This is a raw C/NAV page, increase the counter
      cnavs+=1

      if len(dataFields) != 4:
        if verbose >= 5:
          print("NOV-A Reader: Invalid line format, wrong number of data fields, on line " + str(currentLineNumber))
        currentLineNumber+=1
        continue

      # TODO: implement CRC calculation and check it

      headerPort=headerFields[1]
      headerSequence=headerFields[2]
      headerIdleTime=headerFields[3]
      headerTimeStatus=headerFields[4]
      headerWeek=headerFields[5]
      headerSeconds=headerFields[6]
      headerReceiverStatus=headerFields[7]
      headerReserver=headerFields[8]
      headerReceiverSWVersion=headerFields[9]

      dataSignalChannel=dataFields[0]
      dataPRN=dataFields[1]
      dataMessageID=dataFields[2]
      dataRawCNAV=dataFields[3]

      rawCNAVBinaryString=''.join(format(x, '08b') for x in binascii.unhexlify(dataRawCNAV))
      # Remove the two extra bits at the end that are added for the ascii-hex representation of 464 bits instead of the C/NAV 462
      rawCNAVBinaryString=rawCNAVBinaryString[0:-2]

      if verbose >= 5:
        print("NOV-A Reader, line "+str(currentLineNumber)+", header: "+str(headerFields)+", data: "+str(dataFields)+", crc: "+crcField+", bin: "+rawCNAVBinaryString)

      if self.has_storage.feedMessage(rawCNAVBinaryString, float(headerSeconds), verbose=verbose):
        hasnum += 1
        if converter != None:
          decoded_msg = self.has_storage.lastMessage
          tow = self.has_storage.lastMessage_tow
          if verbose >= 5:
            print("NOV-A Reader, decoded_msg "+str(decoded_msg)+", tow: "+str(tow)+", tow2: "+str(float(headerSeconds)))
          converted = converter.convertMessage(decoded_msg, compact=compact, HRclk=HRclk, tow=tow, lowerUDI=lowerUDI, verbose=verbose)
          if output != None and converted != None:
            for msg_conv in converted:
              msg_bytes = bits2Bytes(msg_conv)
              gpst2time(int(headerWeek), float(headerSeconds))
              if self.pppWiz:
                output.write(msg_bytes, 2, 1, gpst2time(int(headerWeek), float(headerSeconds)))
              else:
                output.write(msg_bytes)

      currentLineNumber+=1
      continue

    if verbose>=1:
      print("Out of "+str(currentLineNumber)+" messages, "+str(cnavs)+" were C/Nav messages. "+str(hasnum)
            +" HAS messages have successfully been decoded and converted.")
