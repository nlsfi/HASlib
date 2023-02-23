#!/usr/bin/env python

'''
HAS message classes

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
1.0.1 23/02/2023  Discarding redundant HAS pages. Bugfix by FGI
'''

from reedsolo import RSCodec, ReedSolomonError
import pkg_resources
import numpy as np
import galois
import time
# import os

from galileo_has_decoder.utils import bits2Bytes, bytes2bits, dataValid, readHeader

class HAS:
  #Simple HAS message class, used in the decoding part on a transmission and assembly level
  TIMELIMIT = 20 #window of time[s] to receive valid pages
  GF = galois.GF(256)
  genMat = None
  status = None
  mID = None
  mType = None
  mSize = None
  pages = None
  pages_l = None
  t0 = None
  rec = None

  def __init__(self, msg=None):
    stream = pkg_resources.resource_stream(__name__, 'resources/genMatrix.txt')
    self.genMat = np.genfromtxt(stream, dtype="u1", delimiter=",")
    self.pages = np.zeros(255, dtype=object)-1
    self.rec = []
    if msg != None:
      self.addPage(msg[0])
      self.status = msg[0][:2]
      self.mType = msg[0][4:6]
      self.mID = int(msg[0][6:11], base=2)
      self.mSize = int(msg[0][12:16], base=2)+1      

  def addPage(self, msg, pid=None, t=None, verb=0):
    if self.mID == None:
      self.status = msg[:2]
      self.mType = msg[4:6]
      self.mID = int(msg[6:11], base=2)
      self.mSize = int(msg[12:16], base=2)+1

    if self.t0 == None:
      if t != None: self.t0 = t 
      else: self.t0 = time.time()
    else:
      if t != None: 
        if t-self.t0 > self.TIMELIMIT:
          raise Page_timeout_Error("The given page's timestamp does exceed the timelimit!")
      else: 
        if time.time()-self.t0 > self.TIMELIMIT:
          raise Page_timeout_Error("The given page's timestamp does exceed the timelimit!")
    if pid is None:      
      pageID = int(msg[16:24], base=2)
    else:
      pageID = pid    
    
    if (pageID-1) in self.rec and self.pages[pageID-1] != bits2Bytes(msg[24:]):
        raise HAS_Error( "received a new version of an existing page id, but with different data!" )
        
    if pageID == 0 or (pageID-1) in self.rec :   # 0 is reserved
        return len(self.rec)>=self.mSize
    
    self.rec += [pageID-1]
    if verb>4:
      print("Page ID to add: ", pageID)
    if verb>6:
      print(bits2Bytes(msg[24:]))
    if self.pages[pageID-1] == -1:
      self.pages[pageID-1] = bits2Bytes(msg[24:])
    return len(self.rec)>=self.mSize
  
  def complete(self):
    return (len(self.rec) >= self.mSize)

  def available(self):
    return self.rec

  def missing(self):
    missingP = []
    for p in range(255):
      if self.pages[p] == -1:
        missingP = missingP + [p]
    return missingP

  def decode(self, mode=1, _fcr=1, verbose=0):
    # Modes: [0: reed solomon decoder; 1: fast matrix multiplication]
    if verbose>=5:
      print("HAS Message complete. Pages received:")
      for p in self.available():
        print("Page "+str(p)+":", self.pages[p])
    missingPages = self.missing()
    toDeco = np.array(self.pages, dtype=object)
    decoded = self.assembleMessage(toDeco, missingPages, mode=mode, _fcr=_fcr)
    decoded = bytes2bits(decoded)
    return decoded[:self.mSize*424]

  def assembleMessage(self, msgs, missing=None, mode=1, _fcr=1):
    if missing is None:
      missing = self.missing()
    HASmsg = bytearray()
    decodedM = []
    if mode == 0:
      rscoder = RSCodec(nsym=223, fcr=_fcr)
      for i in range(53):
        msg = bytearray()
        for j in range(len(msgs)):
          if j not in missing:
            msg = msg + msgs[j][i].to_bytes(1,"big")
          else: 
            msg = msg + b'\x00'
        decoded = rscoder.decode(msg, erase_pos=missing)
        decodedM[i] = decoded[0]
    elif mode == 1: 
      _decodedM = []
      _idxs = self.available()[-self.mSize:]
      _decoPages = self.GF(np.array([np.array(x) for x in self.pages[_idxs]]))
      _decoMat = np.linalg.inv(self.GF(self.genMat[_idxs, :self.mSize]))
      for i in range(53):
        decodedM += [_decoMat @ _decoPages[:, i]]

    HASmsg = bytearray(np.array(decodedM).T.tobytes())
    return(HASmsg)

class HAS_Storage:
    HASobjects = None
    HASmessages = None
    lastMID = None
    lastMessage = None
    lastMessage_tow = None
    def __init__(self):
        self.HASobjects = np.empty(32, dtype=object)
        self.HASmessages = np.empty(32, dtype=object)
        self.lastMID = -1
        self.lastMessage = ""
        self.lastMessage_tow = 0
        for i in range(32):
            self.HASobjects[i] = HAS()

    def feedMessage(self, has_msg, _time, verbose=0):
        hdr = readHeader(has_msg[14:])
        if not dataValid(has_msg, hdr, verbose=verbose):
            return 0
        incoming_nav = has_msg[14:492-30]
        mID = hdr[3]
        if mID == self.lastMID:
            return 0
        try:
            if self.HASobjects[mID].addPage(incoming_nav, t=_time):
                deco = self.HASobjects[mID].decode(verbose=verbose)
                self.HASmessages[mID] = deco 
                self.lastMID = mID
                if verbose>=2:
                    print("Message",mID,"received")
                self.lastMessage = deco
                self.lastMessage_tow = self.HASobjects[mID].t0
                self.HASobjects[mID] = HAS()
                return 1
            return 0
        except Page_timeout_Error:
            print("A timeout error has occurred for message", mID, ". Message will be reinitialized.")
            self.HASobjects[mID] = HAS()

class HAS_Warning(Warning):
  #Base HAS Warning class
  pass
class Page_timeout_Warning(HAS_Warning):
  #Page timeout warning class
  pass
class HAS_Error(Exception):
  #Base HAS Error
  pass
class Page_timeout_Error(HAS_Error):
  #Page Timeout error
  pass
