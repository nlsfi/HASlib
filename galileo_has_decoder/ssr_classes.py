#!/usr/bin/env python

'''
SSR structure classes

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

from galileo_has_decoder.utils import sign, bidict, findNth
import numpy as np

class HAS_Error(Exception):
  #Base SSR Error class
  pass 
  

class Header:
  toh = maskID = IODsetID = None
  msgContent = None
  def __init__(self, msg, i=0):
    #Header Message length should be 24
    self.toh, i = int(msg[i:i+12],2), i+12
    self.msgContent, i = self.readContent(msg[i:i+6]), i+6
    self.reserved, i = msg[i:i+4], i+4
    self.maskID, i = int(msg[i:i+5],2), i+5
    self.IODsetID, i = int(msg[i:i+5],2), i+5

  def readContent(self, msg):
    content = {}
    content["mask"]      = msg[0]=="1"
    content["orb"]       = msg[1]=="1"
    content["clockFull"] = msg[2]=="1"
    content["clockSub"]  = msg[3]=="1"
    content["codeB"]     = msg[4]=="1"
    content["phaseB"]    = msg[5]=="1"
    return content

class Mask:
  id = None #4bit
  satMask = None #40bit
  sigMask = None #16bit
  dnuMask = None
  cellMaskFlag = None #1bit flag, 0=all sigs for all sats
  cellMask = None #n_sat*n_sig bit mask
  navMsg = None #3bit
  nsat = None
  totalSignals = None
  def __init__(self):
    self.dnuMask = 40*"0"
    pass
  def readData(self, msg, i):
    self.id, i = int(msg[i:i+4], 2), i+4
    self.satMask, i = msg[i:i+40], i+40
    self.sigMask, i = msg[i:i+16], i+16
    self.cellMaskFlag, i = msg[i]=="1", i+1
    satnum, signum = self.satMask.count("1"), self.sigMask.count("1")
    self.nsat = satnum
    cellMaskSize = satnum*signum*self.cellMaskFlag
    if self.cellMaskFlag: 
      self.cellMask, i = msg[i:i+cellMaskSize], i+cellMaskSize
    self.navMsg, i = int(msg[i:i+3], 2), i+3
    return i

  def setDNU(self, n, dnu=True):
    satID = self.satID(n)-1
    self.dnuMask = self.dnuMask[:satID] + str(dnu*1) + self.dnuMask[satID+1:]

  def getDNU(self, n):
    satID = self.satID(n)-1
    return self.dnuMask[satID]=="1"

  def satID(self, n):
    return [j for j, ltr in enumerate(self.satMask) if ltr == "1"][n]+1

  def sigID(self, n):
    return [j for j, ltr in enumerate(self.sigMask) if ltr == "1"][n]

  def printData(self):
    print("  HAS Mask Data:")
    print("  System:", self.id)
    print("    Satellite Mask:", self.satMask)
    print("    ", self.nsat,"satellites corrected.")
    print("    Signal Mask:", self.sigMask)
    if self.cellMaskFlag:
      print("    Cell Mask available, subset:", self.cellMask[:20])
    else:
      print("    Cell mask unavailable, all signals for all satellites included.")
    print("    DNU mask:", self.dnuMask)

class Masks:
  nSys = None
  gnss = None
  keys = None
  def __init__(self):
    self.gnss = np.array([], dtype=object)
  def readData(self, msg, i):
    self.nSys, i = int(msg[i:i+4], 2), i+4
    for _j in range(self.nSys):
      mask = Mask()
      i = mask.readData(msg, i)
      self.gnss = np.append(self.gnss, mask)
    _reserved, i = msg[i:i+6], i+6
    self.keys = [m.id for m in self.gnss]
    return i
  
  def satNums(self):
    systems = {}
    for sys in self.gnss:
      systems[sys.id] = sys.satMask.count("1")
    nums = np.zeros(max(systems.keys())+1, dtype=int)
    for j in range(max(systems.keys())+1):
      try:
        nums[j] = systems[j]
      except KeyError:
        nums[j] = 0
    return nums 

  def getSatNum(self, sys, n):
    for j in range(len(self.gnss)):
      if self.gnss[j].id==sys:
        gnssnum = j
        break
    return self.gnss[gnssnum].satID(n)

  def getMask(self, sys):
    for j in range(len(self.gnss)):
      if self.gnss[j].id==sys:
        return self.gnss[j]
    return -1

  def printData(self):
    for s in self.gnss:
      s.printData()

class SatOrbit:
  iod = None
  deltaRad = None
  deltaInTrack = None
  deltaCrossTrack = None
  NAcount = None
  system = None
  iodS = None #IOD size, 10bits for Galileo, 8 bits for GPS
  def __init__(self, _system):
    self.NAcount = 0
    self.system = _system
    if _system==2: self.iodS = 10
    elif _system==0: self.iodS = 8
    else: raise HAS_Error("Unknown System encountered: " + str(_system))

  def readData(self, msg, i):
    self.iod, i = int(msg[i:i+self.iodS], 2), i+self.iodS
    dRad, i = msg[i:i+13], i+13
    if dRad == "1000000000000":
      self.deltaRad="N/A"
      self.NAcount += 1
    else:
      self.deltaRad = sign(dRad)*0.0025

    dIn, i = msg[i:i+12], i+12
    if dIn == "100000000000" : 
      self.deltaInTrack="N/A"
      self.NAcount += 1
    else:
      self.deltaInTrack = sign(dIn)*0.008 
    
    dCross, i = msg[i:i+12], i+12
    if dCross == "100000000000" : 
      self.deltaCrossTrack="N/A"
      self.NAcount += 1
    else:
      self.deltaCrossTrack = sign(dCross)*0.008
    return i

  def printData(self):
    print("   ", self.system, "IOD:",self.iod, "# Rad", self.deltaRad, "# InT", 
    self.deltaInTrack, "# CrossT", self.deltaCrossTrack)

class Orbits:
  satNum = None
  orbits = None
  validityIdx = None
  IODs = None
  def __init__(self, _satNum):
    self.orbits = []
    self.IODs = []
    self.satNum = _satNum

  def readData(self, msg, i):
    self.validityIdx, i = int(msg[i:i+4], 2), i+4
    for sys in range(len(self.satNum)):
      self.orbits += [[]]
      self.IODs += [[]]
      for _sat in range(self.satNum[sys]):
        orb = SatOrbit(sys)
        i = orb.readData(msg, i)
        self.orbits[sys] += [orb]
        self.IODs[sys] += [orb.iod]
    return i

  def printData(self):
    print("  HAS Orbit Data:")
    for sys in self.orbits:
      for sat in sys:
        sat.printData()

class ClockFull:
  validityIdx = None
  mults = None
  corrections = None
  satNums = None
  dnu = None
  def __init__(self, satNum, masks):
    self.satNums = satNum
    self.mults = {}
    self.corrections = []
    self.masks = masks
  
  def readData(self, msg, i,):
    self.validityIdx, i = int(msg[i:i+4], 2), i+4
    for j in range(len(self.satNums)):
      if self.satNums[j]>0:
        mult, i = int(msg[i:i+2], 2)+1, i+2
        self.mults[j] = mult
    for j in range(len(self.satNums)):
      self.corrections += [[]]
      for y in range(self.satNums[j]):
        deltaClock, i = sign(msg[i:i+13])*0.0025*self.mults[j], i+13
        if deltaClock == sign("1000000000000")*0.0025*self.mults[j]:
          deltaClock = "N/A"
        elif deltaClock == sign("0111111111111")*0.0025*self.mults[j]:
          deltaClock = "DNU"
          if self.masks!=None:
            self.masks.gnss[self.masks.keys.index(j)].setDNU(y)
        self.corrections[j] += [deltaClock]
    return i

  def printData(self):
    print("  HAS Clock Data (Full):")
    for sys in self.corrections:
      for sat in sys:
        print("   ", sat)


class ClockSub:
  validityIdx = None
  mults = None
  corrections = None
  satNums = None
  satNumsSub = None
  subMasks = None
  nSys = None
  satIDs = None

  def __init__(self, satNums, masks):
    self.satNums = satNums
    self.satNumsSub = satNums * 0
    self.mults = {}
    self.corrections = [[]]*len(satNums)
    self.subMasks = {}
    self.satIDs = {}
    self.masks = masks

  def readData(self, msg, i):
    self.validityIdx, i = int(msg[i:i+4], 2), i+4
    self.nSys, i = int(msg[i:i+4], 2), i+4
    for _j in range(self.nSys):
      sysID, i = int(msg[i:i+4], 2), i+4
      mult, i = int(msg[i:i+2], 2)+1, i+2
      self.mults[sysID] = mult
      self.subMasks[sysID], i = msg[i:i+self.satNums[sysID]], i+self.satNums[sysID]
      self.satNumsSub[sysID] = self.subMasks[sysID].count("1")
      for y in range(self.satNumsSub[sysID]):
        deltaClock, i = sign(msg[i:i+13])*0.0025*mult, i+13
        if deltaClock == sign("1000000000000")*0.0025*mult:
          deltaClock = "N/A"
        elif deltaClock == sign("0111111111111")*0.0025*mult:
          deltaClock = "DNU"
          prn = ([j for j, ltr in enumerate(self.subMasks[sysID]) if ltr == "1"][y])
          self.masks.gnss[self.masks.keys.index(sysID)].setDNU(prn)
          #ToDo: Remove do-not-use sats from ssr
        self.corrections[sysID] = self.corrections[sysID] + [deltaClock]
    return i
  
  def storeIDs(self, mask):
    for j in range(len(self.satNumsSub)):
      if self.satNumsSub[j] > 0:
        self.satIDs[j] = []
        for y in range(self.satNums[j]):
          if self.subMasks[j][y] == "1":
            self.satIDs[j] = self.satIDs[j] + [mask.getSatNum(j, y)]

  def printData(self):
    print("  HAS Clock Data (Sub):")
    for i in range(len(self.satNumsSub)):
      if len(self.corrections[i]) > 0:
        print("    System:", i)
        for sat in self.corrections[i]:
          print(sat)

class GNSSBiases:
  biases = None
  cMask = None
  mask = None
  mode = None
  def __init__(self, _mode, _mask,):
    self.biases = {}
    self.mode = _mode #can be 'c' for code biases or 'p' for phase biases
    satnum, self.signum = _mask.satMask.count("1"), _mask.sigMask.count("1")
    self.mask = _mask
    if _mask.cellMaskFlag:
      self.cMask = _mask.cellMask #Cell mask
    else:
      self.cMask = (satnum * self.signum) * "1"
    for sat in range(satnum):
      sigs = self.cMask[sat*self.signum:(sat+1)*self.signum].count("1") 
      self.biases[_mask.satID(sat)] = {"num":sigs}

  def readData(self, msg, i):
    xC = 0
    for sat in self.biases:
      for sig in range(self.biases[sat]["num"]):
        if self.mode == 'c':
          bias, i = sign(msg[i:i+11])*0.02, i+11
          correctedSig = findNth(self.cMask[xC*self.signum:(xC+1)*self.signum], "1", sig)
          if bias == -20.48:
            bias = "N/A"
          self.biases[sat][self.mask.sigID(correctedSig)] = bias
        elif self.mode == 'p':
          bias, i = sign(msg[i:i+11])*0.01, i+11
          if bias == -10.24:
            bias = "N/A"
          discont, i = int(msg[i:i+2],2), i+2
          correctedSig = findNth(self.cMask[xC*self.signum:(xC+1)*self.signum], "1", sig)
          self.biases[sat][self.mask.sigID(correctedSig)] = [bias, discont]
      xC += 1
    return i

  def printData(self):
    for sat in self.biases.keys():
      print("      Sat", sat, "-", self.biases[sat])

class Biases:
  nSys = None
  mode = None
  biases = None
  biases_dict = None
  validityIdx = None
  def __init__(self, _masks, _mode):
    self.nSys = _masks.nSys
    self.biases = np.array([], dtype=object)
    self.biases_dict = {}
    self.mode = _mode
    for mask in _masks.gnss:
      self.biases_dict[mask.id] = GNSSBiases(_mode, mask)
  
  def readData(self, msg, i):
    self.validityIdx, i = int(msg[i:i+4], 2), i+4
    for b in self.biases_dict.keys():
      i = self.biases_dict[b].readData(msg, i)
    return i

  def printData(self):
    print("  HAS Bias Data:")
    print("    Mode:", self.mode)
    for sys in self.biases_dict.keys():
      print("    System:", sys)
      self.biases_dict[sys].printData()

class SSR:
  IODs = None
  read = None
  header = None
  masks = None
  orbits = None
  clockFull = None
  clockSub = None
  codeBiases = None
  phaseBiases = None
  sysKeys = bidict({"GPS": 0, "GAL": 2})
  def __init__(self):
    pass

  def printData(self):
    print("######################################\n     HAS Printouts. ToH:", self.header.toh)
    if self.masks != None:
      self.masks.printData()
    if self.orbits != None:
      self.orbits.printData()
    if self.clockFull != None:
      self.clockFull.printData()
    if self.clockSub != None:
      self.clockSub.printData()
    if self.codeBiases != None:
      self.codeBiases.printData()
    if self.phaseBiases != None:
      self.phaseBiases.printData()



class SSR_HAS:
  ssr = None
  valid = None
  HAS_MASKS = np.empty(32, dtype=object)
  HAS_IODs = np.empty(32, dtype=object)
  def __init__(self, msg, ssr=None, verb=0):
    self.valid = False
    if ssr==None:
      self.ssr = SSR()
    else:
      self.ssr = ssr
    self.ssr.read = {0:self.rdMasks, 1:self.rdOrbits, 
            2:self.rdClockFull, 3:self.rdClockSub, 
            4:self.rdCodeBias, 5:self.rdPhaseBias}
    self.ssr.header = Header(msg)
    i = 32
    blocks = list(zip(self.ssr.header.msgContent.values(), range(6)))
    if blocks[0][0]:
      maskID = self.ssr.header.maskID
      i = self.rdMasks(msg, i)
      self.HAS_MASKS[maskID] = self.ssr.masks
      mask_avail = True
    else:
      mask_avail = self.retrieveMasks()
    if blocks[1][0]:
      iod_avail=True
    else:
      iod_avail = (self.HAS_IODs[self.ssr.header.IODsetID] != None)
    if mask_avail and iod_avail:
      self.valid = True
      for c in blocks[1:]:
        if c[0]:
          i = self.ssr.read[c[1]](msg, i)
          if verb>=6:
            print(i)
      if verb >= 3: 
        print("Message read. Parsed bits:", i)
    elif verb>=1:
      print("Mask not available, message discarded")
    
  def retrieveMasks(self, maskID=None):
    if maskID == None:
      maskID = self.ssr.header.maskID
    masks = self.HAS_MASKS[maskID]
    self.ssr.masks = masks
    return self.ssr.masks != None

  def rdMasks(self, msg, i):
    self.ssr.masks = Masks()
    i = self.ssr.masks.readData(msg, 32)
    return i
  
  def rdOrbits(self, msg, i):
    self.ssr.orbits = Orbits(self.ssr.masks.satNums())
    i = self.ssr.orbits.readData(msg, i)
    self.HAS_IODs[self.ssr.header.IODsetID] = self.ssr.orbits.IODs
    self.ssr.IODs = self.ssr.orbits.IODs
    return i
  
  def rdClockFull(self, msg, i):
    self.ssr.clockFull = ClockFull(self.ssr.masks.satNums(), self.ssr.masks)
    i = self.ssr.clockFull.readData(msg, i)
    return i
  
  def rdClockSub(self, msg, i):
    self.ssr.clockSub = ClockSub(self.ssr.masks.satNums(), self.ssr.masks)
    i = self.ssr.clockSub.readData(msg, i)
    self.ssr.clockSub.storeIDs(self.ssr.masks)
    return i
  
  def rdCodeBias(self, msg, i):
    self.ssr.codeBiases = Biases(self.ssr.masks, 'c')
    i = self.ssr.codeBiases.readData(msg, i)
    return i
  
  def rdPhaseBias(self, msg, i):
    self.ssr.phaseBiases = Biases(self.ssr.masks, 'p')
    i = self.ssr.phaseBiases.readData(msg, i)
    return i

  def printData(self):
    self.ssr.printData()
