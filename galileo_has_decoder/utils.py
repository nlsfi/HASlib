#!/usr/bin/env python

'''
General utility functions

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
1.0.1 23/02/2023  Enabling of operational mode (flag on line 148) by FGI
'''

import numpy as np

# def splitString(string, length):
#     return (string[0+i:length+i] for i in range(0, len(string), length))

def splitStringBytes(string, length=8):
    return list(int(string[0+i:length+i],2).to_bytes(1,"big") for i in range(0, len(string), length))

def bytesFromList(bs):
  barr = bytearray()
  for b in bs:
    barr += b
  return barr

def bits2Bytes(string):
  return bytesFromList(splitStringBytes(string))

def gpst2time(week, tow):
  # Beginning of epoch time + weeks & seconds
  # NOT TO BE USED FOR EXACT MEASUREMENTS
  return 315964800.0 + 86400*7*week + tow
 
def bytes2bits(msg, bitw=8):
  if bitw==8:
    num = np.array(msg, dtype="u1")
  else:
    num = np.array(msg)
  bits=""
  if type(bitw) is int:
    for w in num:
      bits = bits + np.binary_repr(w, width=bitw)
  else:
    for w in zip(num, bitw):
      bits = bits + np.binary_repr(w[0], width=w[1])
  return bits

#Inspiration: https://www.geeksforgeeks.org/modulo-2-binary-division/
# Returns XOR of 'a' and 'b'
# (both of same length)
def xor_int(a, b):
    _a = bin(a)
    _b = bin(b)
    a = np.binary_repr(a, max(len(_a), len(_b)))
    b = np.binary_repr(b, max(len(_a), len(_b)))
    # initialize result
    result = []
 
    # Traverse all bits, if bits are
    # same, then XOR is 0, else 1
    for i in range(1, len(b)):
        if a[i] == b[i]:
            result.append('0')
        else:
            result.append('1')
 
    return int(''.join(result),2)

def sign(n):
  return int(n[1:],2)-(2**(len(n)-1))*int(n[0])

def readContent(msg):
  content = {}
  content["mask"]      = msg[0]=="1"
  content["orb"]       = msg[1]=="1"
  content["clockFull"] = msg[2]=="1"
  content["clockSub"]  = msg[3]=="1"
  content["codeB"]     = msg[4]=="1"
  content["phaseB"]    = msg[5]=="1"
  return content

def findNth(string, sub, n):
  nth = string.find(sub)
  while nth>=0 and n>0:
    nth = string[nth+1:].find(sub)+nth+1
    n-=1
  return nth

#Credit to: https://stackoverflow.com/users/1422096/basj
class bidict(dict):
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value,[]).append(key) 

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key) 
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value,[]).append(key)        

    def __delitem__(self, key):
        self.inverse.setdefault(self[key],[]).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]: 
            del self.inverse[self[key]]
        super(bidict, self).__delitem__(key)

def printHASinfo(_msg, _subset=-1):
  mt = int(_msg[18:20],2)
  mID = int(_msg[20:25],2)
  mS = int(_msg[25:30],2)
  pID = int(_msg[30:38],2)
  if _subset == -1:
    print("## HAS Header Info ##"
    + "\n  mType: " + str(mt)
    + "\n  mID: " + str(mID)
    + "\n  mSize: " + str(mS)
    + "\n  pID: " + str(pID))
  else: 
    print("## HAS Header Info ##")
    if _subset[0]:
      print("  mType: " + str(mt))
    if _subset[1]:
      print("  mID: " + str(mID))
    if _subset[2]:
      print("  mSize: " + str(mS))
    if _subset[3]:
      print("  pID: " + str(pID))

def readHeader(msg, verb=False):
  status = msg[:2]
  res = msg[2:4]
  mt = msg[4:6]
  mid = int(msg[6:11], 2)
  ms = int(msg[11:16], 2)+1
  pid = int(msg[16:24], 2)+1
  if verb:
    print(status, res, mt, mid, ms, pid)
  return [status, res, mt, mid, ms, pid]

def dataValid(data, hdr, verbose=0):
  if int(data[14:38], 2) == 0xaf3bc3:
    if verbose >= 4:
      print("     Dummy HAS message received")
    return False
  if data[:14] != "11111111111111":
    return False
  if hdr[0] != "00" and hdr[0] != "01":  # test (00) and operational modes (01) accepted
    return False
  if hdr[2] != "01":
    return False
  return True
