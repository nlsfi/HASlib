#!/usr/bin/env python

'''
Novatel GALCNAVRAWPAGE file reading class

VER   DATE        AUTHOR
1.0.x   2023-09-29  Jaakko Yliaho / Uwasa
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

  # Calculate CRC for single byte
  @staticmethod
  def crc(byte):
    for j in range(8):
      if ((byte & 1) & 0xFF):
        byte = ((byte >> 1)) ^ 0xEDB88320
      else:
        byte = (byte >> 1)
    return byte
  
  # Calculate CRC for bytestream
  @staticmethod
  def CalculateBlockCRC32(bytestream):
    result = 0x00000000
    for byte in bytestream:
      temp1 = (result >> 8) & 0x00FFFFFF
      temp2 = NOV_Reader.crc((result ^ byte ) & 0xFF)
      result = temp1 ^ temp2
    return result

  def read(self, path=None, converter=None, output=None, mode='m', x=None, compact=True, HRclk=False, lowerUDI=True, verbose=0):
    if mode != 'm':
      raise Exception("File Reading does only support message-number constraints")
    if x != None: self.msgnum = x
    
    if converter is not None:
      if converter.pppWiz:
        self.output = output
        self.pppWiz = True

    cnavs = 0
    hasnum=0
    currentLineNumber=0

    for logMessage in self.lines:
      logMessageFields=logMessage.split(";")
      if len(logMessageFields) != 2:
        if verbose >= 5:
          print("NOV-A Reader: Invalid line format on line " + str(currentLineNumber+1))
        currentLineNumber+=1
        continue

      headerFields=logMessageFields[0].split(",")
      if len(headerFields) != 10:
        if verbose >= 5:
          print("NOV-A Reader: Invalid line format, wrong number of header fields, on line " + str(currentLineNumber+1))
        currentLineNumber+=1
        continue

      dataCrcFields=logMessageFields[1].split("*")
      if len(dataCrcFields) != 2:
        if verbose >= 5:
          print("NOV-A Reader: Invalid line format, CRC missing, on line " + str(currentLineNumber+1))
        currentLineNumber+=1
        continue

      dataFields=dataCrcFields[0].split(",")
      crcField=str.rstrip(dataCrcFields[1])

      headerMessage=headerFields[0]
      if headerMessage != "#GALCNAVRAWPAGEA" and "#GALCNAVRAWPAGEA" in headerMessage:
        headerMessage="#GALCNAVRAWPAGEA"

      if headerMessage != "#GALCNAVRAWPAGEA":
        if verbose >= 6:
          print("NOV-A Reader, line "+str(currentLineNumber)+", not a raw C/NAV page: "+str(headerMessage))
        currentLineNumber+=1
        continue

      # Compute and check log message CRC
      # C/NAV raw data CRC has already been checked by the receiver.
      # Only C/NAV messages that pass CRC validation are outputted by logging
      messageToCheck=headerMessage[1:]+','+','.join(headerFields[1:])+';'+','.join(dataFields)
      calculatedCrc=NOV_Reader.CalculateBlockCRC32(bytes(messageToCheck, 'utf-8'))
      if (binascii.unhexlify(crcField) != int.to_bytes(calculatedCrc, 4, 'big')):
        if verbose >= 5:
          print("NOV-A Reader: Invalid CRC on line " + str(currentLineNumber+1))
        currentLineNumber+=1
        continue

      if len(dataFields) != 5 and len(dataFields) != 4:
        if verbose >= 5:
          print("NOV-A Reader: Invalid line format, wrong number of data fields, on line " + str(currentLineNumber+1))
        currentLineNumber+=1
        continue

      headerPort=headerFields[1]
      headerSequence=headerFields[2]
      headerIdleTime=headerFields[3]
      headerTimeStatus=headerFields[4]
      headerWeek=headerFields[5]
      headerSeconds=headerFields[6]
      headerReceiverStatus=headerFields[7]
      headerReserved=headerFields[8]
      headerReceiverSWVersion=headerFields[9]

      dataSignalChannel=dataFields[0]
      dataPRN=dataFields[1]
      dataMessageID=dataFields[2]
      dataPageID=""
      dataRawCNAV=""

      # SW version 17022(7.08.14) implemented new ASCII logging format with four data fields before raw C/NAV data
      # Before version 17022 it was only three data fields before C/NAV raw data
      # Check that logged software version matches the number of data fields logged
      if int(headerReceiverSWVersion) < 17022:
        if len(dataFields) != 4:
          if verbose >= 5:
            print("NOV-A Reader: Invalid line format, wrong number of data fields, on line " + str(currentLineNumber+1))
          currentLineNumber+=1
          continue

        dataPageID=""
        dataRawCNAV=dataFields[3]
      else:
        dataPageID=dataFields[3]
        dataRawCNAV=dataFields[4]

      # All the checks done. This is an OK raw C/NAV page, increase the counter
      cnavs+=1

      rawCNAVBinaryString=''.join(format(x, '08b') for x in binascii.unhexlify(dataRawCNAV))
      # Remove the two extra bits at the end that are added for the ascii-hex representation of 464 bits instead of the C/NAV 462
      rawCNAVBinaryString=rawCNAVBinaryString[0:-2]

      if verbose >= 6:
        print("NOV-A Reader, line "+str(currentLineNumber+1)+", header: "+str(headerFields)+", data: "+str(dataFields)+", crc: "+crcField+", bin: "+rawCNAVBinaryString)

      if self.has_storage.feedMessage(rawCNAVBinaryString, float(headerSeconds), verbose=verbose):
        hasnum+=1
        if converter != None:
          decoded_msg = self.has_storage.lastMessage
          tow = self.has_storage.lastMessage_tow
          if verbose >= 6:
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
