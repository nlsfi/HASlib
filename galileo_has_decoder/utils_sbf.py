#!/usr/bin/env python

'''
SBF reading & storing utils

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

import numpy as np
LIMIT = 1025

def splitStream(stream, x):
  l = len(stream)
  pL = int(l/x)
  split = []
  for i in range(x):
    split += [stream[i*pL:(i+1)*pL]]
  return split

def satNum(num):
  if num < 1:
    return -1
  elif num < 38:
    return "GPS" + str(num)
  elif num < 62:
    return "GLO" + str(num-37)
  elif num == 62:
    return "GLO, unknown"
  elif num < 71:
    return -1
  elif num < 107:
    return "GAL" + str(num-70)
  elif num < 120:
    return -1
  elif num < 139:
    return "SBAS" + str(num)
  elif num == 141:
    return "COMPASS M1"
  
class SBF_Block:
  crc = None
  id = None
  length = None
  tow = None
  week = None
  svid = None
  crc_passed = None
  viterbi_count = None
  source = None
  freq_nr = None
  reserved = None
  navbits = None
  def __init__(self, header, line):
    self.crc = header[0]
    self.id = header[1]
    self.length = header[2]
    self.tow = line[0]
    self.week = line[1]
    self.svid = line[2]
    self.crc_passed = line[3]
    self.viterbi_count = line[4]
    self.source = line[5]
    self.freq_nr = line[6]
    self.reserved = line[7]
    self.navbits = line[8:]

  def printInfo(self):
    print("## SBF Block Info ##\n"
    + "  CRC: " + str(self.crc)
    + "\n  ID: " + str(self.id)
    + "\n  Length: " + str(self.length)
    + "\n  Time of Week: " + str(self.tow)
    + "\n  Week: " + str(self.week)
    + "\n  SVID: " + str(self.svid)
    + "\n  CRC Passed: " + str(self.crc_passed)
    + "\n  Viterbi Count: " + str(self.viterbi_count)
    + "\n  Source: " + str(self.source)
    + "\n  Frequency Number: " + str(self.freq_nr))
  def printNavBits(self):
    print("## SBF Block Navigation Bits ##\n"
    + "  Hex:")
    for b in self.navbits:
      print("    " + str(hex(b))[2:])

  def returnBinary(self, cutRes=False):
    msg = ""
    for b in self.navbits:
      msg = msg + np.binary_repr(b,32)
    return msg[14*cutRes:-20]

class IONO_Block:
  crc = None
  id = None
  length = None
  tow = None
  week = None
  svid = None
  source = None
  a_i0 = None
  a_i1 = None
  a_i2 = None
  #Flags[0:5] stores the StormFlags[1:6] in ascening order. 
  flags = None
  def __init__(self, header, line):
    self.crc = header[0]
    self.id = header[1]
    self.length = header[2]
    self.tow = line[0]
    self.week = line[1]
    self.svid = line[2]
    self.source = line[3]
    self.a_i0 = line[4]
    self.a_i1 = line[5]
    self.a_i2 = line[6]
    self.flags = self.extractFlags(line[7])
  def extractFlags(self, f):
    flags = [0,0,0,0,0]
    for i in range(3,8):
      flags[7-i] = (f&(2**i)>0)
    return flags