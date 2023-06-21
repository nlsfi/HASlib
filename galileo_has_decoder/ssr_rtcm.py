#!/usr/bin/env python

'''
RTCM3 SSR message class

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
1.0.2 31/05/2023  Martti Kirkko-Jaakkola / FGI
'''

from galileo_has_decoder.utils import bidict, bits2Bytes
from galileo_has_decoder.ssr_classes import SSR
from galileo_has_decoder import crc
import math
import numpy as np


HAS_PROVIDER_ID = 270 #Placeholder

class SSR_Error(Exception):
  #Base SSR Error class
  pass
class CorrectionNotAvailable(SSR_Error):
  #Raised when a requested correction is not available
  pass


class SSR_RTCM():
  blocks = None
  ssr = None
  udi = bidict({0:1, 1:2, 2:5, 3:10, 4:15, 5:30, 
      6:60, 7:120, 8:240, 9:300, 10:600, 
      11:900, 12:1800, 13:3600, 14:7200, 15:10800})
  HAScode2PPPcode = {"GPS": {0:0, 3:17, 4:18, 5:19, 
                              6:7, 7:8, 8:9, 9:10, 
                              11:14, 12:15, 13:16},
                     "GAL": {0:1, 1:2, 2:3, 3:5,
                             4:6, 5:7, 6:8, 7:9,
                             8:10, 9:11, 10:12, 11:13,
                             12:15, 13:16, 14:17}}
  #cycleLens: the length of a cycle of a signal in mm                       
  cycleLens = {"GPS":{0:190, 3:190, 4:190, 5:190,
                    6:244, 7:244, 8:244, 9:244,
                    11:255, 12:255, 13:255},
              "GAL":{0:190, 1:190, 2:190, 3:255, 
                    4:255, 5:255, 6:248, 7:248, 
                    8:248, 9:252, 10:252, 11:252, 
                    12:234, 13:234, 14:234}}
  def __init__(self, ssr=None):
    if ssr==None:
      self.ssr = SSR()
    else:
      self.ssr = ssr     
    pass
  
  def msgNum(self, msg, sys):
    if type(msg)==int:
      if sys=="GPS": base = 1056
      elif sys=="GAL": base = 1239
      return base + msg
    elif msg=="p":
      if sys=="GPS": return 1265 #11
      elif sys=="GAL": return 1267 #12
    else:
      try:
        return self.msgNum(int(msg), sys)
      except ValueError:
        raise SSR_Error("Invalid message number requested")

  def block(self, ssr, msgNum):
    blockDict = {"p": ssr.phaseBiases, 1:ssr.orbits, 
      2:[ssr.clockFull, ssr.clockSub], 
      3:ssr.codeBiases, 5: None, 6:[ssr.clockFull, ssr.clockSub],
      4:[ssr.orbits, ssr.clockFull, ssr.clockSub]}
    return blockDict[msgNum]

  def pages(self, msg, headerL):
    if len(msg)<=(8192-headerL):
      return 1
    else:
      return math.ceil(len(msg)/(8192-headerL))

  def splitPages(self, msg, headerL):
    pages = []
    pL = 8192-(headerL+3*8)
    pageNum = self.pages(msg, headerL)
    for i in range(pageNum):
      i_page = msg[i*pL:(i+1)*pL]
      pages += [i_page]
    return pages

  def translateClock(self, clock):
    c0 = round(clock / 0.0001)
    return np.binary_repr(c0, 22)

  def ssr1(self, sys, ssr, tow, lowerUDI=True):
    #Orbit correction message
    #Try to obtain requested type of corrections from the HAS object
    try:
      orbs = ssr.orbits.orbits[ssr.sysKeys[sys]]
      satNo = ssr.orbits.satNum[ssr.sysKeys[sys]]
    except IndexError:
      raise CorrectionNotAvailable("HAS orbit corrections are not available!")
    #Message generation
    msg = ""
    #per satellite:
    nSat = satNo
    for sat in range(satNo):
      dnu = ssr.masks.gnss[ssr.masks.keys.index(ssr.sysKeys[sys])].getDNU(sat)
      if orbs[sat].NAcount == 0 and not dnu:
        #6bit PRN
        prn = ssr.masks.getSatNum(ssr.sysKeys[sys], sat)
        msg += np.binary_repr(prn, 6)
        #10bit IODE GAL, 8bit IOD GPS
        iode = orbs[sat].iod
        if sys == "GPS":
          iode = iode & 255
          msg+= np.binary_repr(iode, 8)
        elif sys == "GAL":
          msg+= np.binary_repr(iode, 10)
        #22bit dEph[0]
        #20bit dEph[1]
        #20bit dEph[2]
        orbitCorr = self.translateOrbit(orbs[sat])
        msg += orbitCorr
        #21bit ddEph[0] <- Not possible
        #19bit ddEph[1] <- Not possible
        #19bit ddEph[2] <- Not possible
        msg += "0"*59
      else:
        nSat -= 1

    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 68)
    for i in range(len(pages)-1):
      hdr = self.const_common_header(sys, ssr, 1, True, tow, nSat, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 1, False, tow, nSat, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages

  def translateOrbit(self, orb):
    # Because of different sign convention between HAS and RTCM-SSR, invert the signs
    dRad = -round(orb.deltaRad / 0.0001)
    dAlong = -round(orb.deltaInTrack / 0.0004)
    dCross = -round(orb.deltaCrossTrack / 0.0004)
    dRad = np.binary_repr(dRad, 22)
    dAlong = np.binary_repr(dAlong, 20)
    dCross = np.binary_repr(dCross, 20)
    return dRad + dAlong + dCross

  def ssr2(self, sys, ssr, tow, lowerUDI=True):
    #Clock correction message
    msg = ""
    sub = False
    clocks = ssr.clockFull
    if clocks!= None: 
      satNo = ssr.masks.satNums()[ssr.sysKeys[sys]]
    else:
      clocks = ssr.clockSub
      if clocks==None:
        raise CorrectionNotAvailable("HAS clock corrections are not available!")
      sub = True
      satNo = clocks.satNumsSub[ssr.sysKeys[sys]]
    #per satellite:
    nSat = satNo
    for sat in range(satNo):
      if type(clocks.corrections[ssr.sysKeys[sys]][sat])!= str:
        # 6bit PRN
        if not sub:
          prn = ssr.masks.getSatNum(ssr.sysKeys[sys], sat) 
        else:
          prn = clocks.satIDs[ssr.sysKeys[sys]][sat]
        msg += np.binary_repr(prn, 6)
        # 22bit Delta Clock C0
        c0 = self.translateClock(clocks.corrections[ssr.sysKeys[sys]][sat])
        msg += c0
        # 21bit Delta Clock C1  <- Not available
        # 27bit Delta Clock C2  <- Not available
        msg += 48*"0"
      else:
        nSat -= 1

    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 67)
    for i in range(len(pages)-1):
      #12bit MT + 49bit Header
      hdr = self.const_common_header(sys, ssr, 2, True, tow, nSat, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 2, False, tow, nSat, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages 

  def ssr3(self, sys, ssr, tow, lowerUDI=True):
    #Code bias correction message
    msg = ""
    #12bit MT + 49bit Header (added later)
    #6bit no. of satellites
    try:
      codes = ssr.codeBiases.biases_dict[ssr.sysKeys[sys]]
    except TypeError:
      raise CorrectionNotAvailable("HAS Code Biases not available!")
    satNo = codes.mask.nsat
    sats = list(codes.biases.keys())
    assert satNo == len(sats)
    nSat = satNo
    #per satellite:
    for sat in range(satNo):
      #6bit PRN
      prn = sats[sat]
      msg += np.binary_repr(prn, 6)
      #5bit nbias
      satCodes = list(codes.biases[prn].keys())
      codeNo = len(satCodes)
      for i in satCodes:
        if codes.biases[prn][i] == "N/A":
          codeNo -= 1
        elif i not in self.HAScode2PPPcode[sys].keys():
          #should practically not occur (except HAS keys/extent changes)
          codeNo -= 1
      dnu = ssr.masks.gnss[ssr.masks.keys.index(ssr.sysKeys[sys])].getDNU(sat)
      if codeNo > 0 and not dnu:
        msg += np.binary_repr(codeNo, 5)
        #per bias:
        for code in satCodes:
          if codes.biases[prn][code] != "N/A":
            if code in self.HAScode2PPPcode[sys].keys():
              #5bit mode
              codeID = self.HAScode2PPPcode[sys][code]
              msg += np.binary_repr(codeID, 5)
              #14bit bias
              bias = self.translateBias(codes.biases[prn][code], "c")
              msg += np.binary_repr(bias, 14)
      else:
        nSat -= 1
        msg = msg[:len(msg)-6]

    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 67)
    for i in range(len(pages)-1):
      # 12bit MT + 49bit Header
      hdr = self.const_common_header(sys, ssr, 3, True, tow, nSat, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 3, False, tow, nSat, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages

  def ssr4(self, sys, ssr, tow, lowerUDI=True):
    #Combined Orbit + Clock correction message
    msg = ""
    sub = False
    #12bit MT + 50bit Header (constructed later)
    #6bit number of satellites
    try:
      orbs = ssr.orbits.orbits[ssr.sysKeys[sys]]
      satNo = ssr.orbits.satNum[ssr.sysKeys[sys]]
      clocks = ssr.clockFull
      if clocks==None: 
        clocks = ssr.clockSub
        if clocks==None:
          raise CorrectionNotAvailable("HAS clock corrections are not available!")
        sub = True
        satNo = clocks.satNumsSub[ssr.sysKeys[sys]]
    except IndexError:
      raise CorrectionNotAvailable("HAS orbit corrections are not available!")
    nSat = satNo
    #per satellite:
    for sat in range(satNo):
      sat_clk = clocks.corrections[ssr.sysKeys[sys]][sat]
      if orbs[sat].NAcount == 0 and type(sat_clk)!= str:
        #6bit PRN
        if not sub:
          prn = ssr.masks.getSatNum(ssr.sysKeys[sys], sat)
        else:
          prn = clocks.satIDs[ssr.sysKeys[sys]][sat]
        msg += np.binary_repr(prn, 6)
        #10bit IODE GAL, 8bit IOD GPS
        iode = orbs[sat].iod
        if sys == "GPS":
          iode = iode & 255
          msg+= np.binary_repr(iode, 8)
        elif sys == "GAL":
          msg+= np.binary_repr(iode, 10)
        #62bit dEph
        orbitCorr = self.translateOrbit(orbs[sat])
        msg += orbitCorr
        #59bit ddEph; Not available in HAS
        msg += "0"*59
        #70bit dClk, C1&C2 not available in HAS
        c0 = self.translateClock(sat_clk)
        msg += c0
        msg += 48*"0"
      else:
        nSat -= 1

    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 68)
    for i in range(len(pages)-1):
      # 12bit MT + 49bit Header
      hdr = self.const_common_header(sys, ssr, 4, True, tow, nSat, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 4, False, tow, nSat, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages

  def ssr5(self, sys, ssr, tow):
    #URA correction message
    raise CorrectionNotAvailable("HAS messages do not contain URA corrections yet")

  def ssr6(self, sys, ssr, tow, lowerUDI=True):
    #Alternative HR Clock correction message
    msg = ""
    sub = False
    clocks = ssr.clockFull
    if clocks!= None: 
      satNo = ssr.masks.satNums()[ssr.sysKeys[sys]]
    else:
      clocks = ssr.clockSub
      if clocks==None:
        raise CorrectionNotAvailable("HAS clock corrections are not available!")
      sub = True
      satNo = clocks.satNumsSub[ssr.sysKeys[sys]]
    #per satellite:
    nSat = satNo
    for sat in range(satNo):
      if type(clocks.corrections[ssr.sysKeys[sys]][sat])!= str:
        # 6bit PRN
        if not sub:
          prn = ssr.masks.getSatNum(ssr.sysKeys[sys], sat) 
        else:
          prn = clocks.satIDs[ssr.sysKeys[sys]][sat]
        msg += np.binary_repr(prn, 6)
        # 22bit Delta Clock C0
        c0 = self.translateClock(clocks.corrections[ssr.sysKeys[sys]][sat])
        msg += c0
      else:
        nSat -= 1

    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 67)
    for i in range(len(pages)-1):
      #12bit MT + 49bit Header
      hdr = self.const_common_header(sys, ssr, 6, True, tow, nSat, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 6, False, tow, nSat, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages 

  def ssrp(self, sys, ssr, tow, lowerUDI=True, version=3.2):
    # Phase biases correction message
    msg = ""
    #12bit MT + 51bit Header (constructed later)
    #6bit number of satellites
    try:
      phases = ssr.phaseBiases.biases_dict[ssr.sysKeys[sys]]
    except TypeError:
      raise CorrectionNotAvailable("HAS Phase Biases not available!")
    satNo = phases.mask.nsat
    sats = list(phases.biases.keys())
    assert satNo == len(sats)
    nSat = satNo
    #per satellite:
    for sat in range(satNo):
      #6bit PRN
      prn = sats[sat]
      msg += np.binary_repr(prn, 6)
      #5bit nbias
      satPhases = list(phases.biases[prn].keys())
      phaseNo = len(satPhases)
      for i in satPhases:
        if i not in self.HAScode2PPPcode[sys].keys():
          #Catches "num" entry
          #should else practically not occur (except HAS keys/extent changes)
          phaseNo -= 1
        elif phases.biases[prn][i][0] == "N/A":
          phaseNo -= 1
      dnu = ssr.masks.gnss[ssr.masks.keys.index(ssr.sysKeys[sys])].getDNU(sat)
      if phaseNo > 0 and not dnu:
        msg += np.binary_repr(phaseNo, 5)
        #9bit yaw angle
        #8bit yaw rate
        msg += "0"*(9+8)
        #per bias:
        for phase in satPhases:
          if phase != "num":
            if phases.biases[prn][phase][0] != "N/A":
              if phase in self.HAScode2PPPcode[sys].keys():
                #5bit mode
                phaseID = self.HAScode2PPPcode[sys][phase]
                msg += np.binary_repr(phaseID, 5)
                #1bit integer
                #2bit WLI
                # In the Galileo HAS SIS ICD 1.4, these properties are inevident
                msg += "000"
                #4bit discontinuity counter
                discont = phases.biases[prn][phase][1]
                msg += np.binary_repr(discont, 4)
                #20bit bias
                bias = self.translateBias(phases.biases[prn][phase][0], "p", sys, phase)
                msg += np.binary_repr(bias, 20)
                #17bit std-dev
                if version==3.3:
                  msg += "0"*17
      else:
        nSat -= 1
        msg = msg[:len(msg)-6]

    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 69)
    for i in range(len(pages)-1):
      # 72bit common Header(msgnum)
      hdr = self.const_common_header(sys, ssr, "p", True, tow, nSat, lowerUDI)  
      # 1bit Dispersive Bias Consist. ind.
      # 1bit MW Consistency Ind.
      # In the Galileo HAS SIS ICD 1.4, these properties are inevident
      msg += "00"
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, "p", False, tow, nSat, lowerUDI) 
    # 1bit Dispersive Bias Consist. ind.
    # 1bit MW Consistency Ind.
    hdr += "00"
    pages[-1] = self.frame(hdr + pages[-1])
    return pages

  def translateBias(self, HASbias, mode, sys=None, signal=None):
    if mode == "c":
      RTCMbias = round(HASbias / 0.01)
    elif mode == "p":
      cycles = HASbias
      #Converting cycles (HAS) to m (IGS): wavelength[mm]*cycles / 0.1
      #/0.1 for RTCM resolution of 0.0001m (0.1mm)
      RTCMbias = round(self.cycleLens[sys][signal] * cycles / 0.1)
    return RTCMbias

  def frame(self, msg):
    padded = msg + (8-(len(msg)%8))*"0"
    mLen = int(len(padded)/8)
    intro = "11010011" + "000000" + np.binary_repr(mLen, 10)
    _crc = crc.crc24q(bits2Bytes(intro+padded), mLen+3)
    parity = np.binary_repr(_crc, 24)
    framed = intro + padded + parity
    return framed

  #existing types are: 1,2,3,4,5,6,p
  def const_common_header(self, sys, ssr, msgNum, _sync, tow, nSat, lowerUDI=True):
    #Common part of all headers (+ refd for 1&4)
    hdr = ""
    #12bit Message Number
    hdr += np.binary_repr(self.msgNum(msgNum, sys), 12)
    #20bit time
    hdr += self.calc_tow(ssr, tow) 
    #4bit UDI
    udi = self.ret_udi(self.block(ssr, msgNum), lowerUDI=lowerUDI)
    hdr+= np.binary_repr(udi, 4)
    #1bit Sync flag (message following?)
    sync = _sync #as 0/1 bit
    hdr += np.binary_repr(sync*1, 1)
    if msgNum == 1 or msgNum == 4:
      #1bit ITRF (standard Galileo reference datum)
      refd = "0" 
      hdr += refd
    #This code is v1.0 of the SSR generation
    iod = 1
    hdr += np.binary_repr(iod, 4)
    #16bit provider ID
    providID = HAS_PROVIDER_ID
    hdr += np.binary_repr(providID, 16)
    #4bit Solution ID: one service in HAS, so ID 1
    solid = "0001"
    hdr += solid
    #6bit number of satellites
    hdr += np.binary_repr(nSat, 6)
    return hdr

  def calc_tow(self, ssr, _tow):
    tow_h = int(_tow / 3600)
    toh_has = ssr.header.toh
    if tow_h*3600 + toh_has > _tow:
      tow_h -= 1
    tow = tow_h*3600 + toh_has
    return np.binary_repr(tow, 20)

  def ret_udi(self, ssr_block, lowerUDI=True):
    has_keys = {0:5, 1:10, 2:15, 3:20, 4:30, 5:60, 
       6:90, 7:120, 8:180, 9:240, 10:300, 
       11:600, 12:900, 13:1800, 14:3600, 15:-1}
    udi = 0
    has_udi = 15
    if type(ssr_block) == list:
      blocks = ssr_block
    else:
      blocks = [ssr_block]
    for i in range(len(blocks)):
      if blocks[i]!= None:
        if blocks[i].validityIdx < has_udi:
          has_udi = blocks[i].validityIdx
    has_udi = has_keys[has_udi]
    try: 
      udi = self.udi.inverse[has_udi][0]
    except KeyError:
      for i in range(len(self.udi)):
        if self.udi[i]>has_udi:
          break
      udi = i-lowerUDI*1
    return udi