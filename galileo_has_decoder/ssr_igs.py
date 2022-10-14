#!/usr/bin/env python

'''
IGS SSR message class

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''
import numpy as np
from galileo_has_decoder import crc
from galileo_has_decoder.utils import bidict, bits2Bytes
import math

HAS_PROVIDER_ID = 270 #Placeholder

class SSR_Error(Exception):
  #Base SSR Error class
  pass
class CorrectionNotAvailable(SSR_Error):
  #Raised when a requested correction is not available
  pass


class SSR_IGS:
  # IGS message constructor class.
  # Relevant messages:
  #   IGM01 - Orbit
  #   IGM02 - Clock
  #   IGM03 - Orbit + Clock
  #   IGM04 - High-rate Clock
  #   IGM05 - Code Bias
  #   IGM06 - Phase Bias
  #   IGM07 - URA
  # Sub-Types:
  #    21- 40 - GPS
  #    41- 60 - GLONASS
  #    61- 80 - Galileo
  #    81-100 - QZSS
  #   101-121 - BDS
  #   121-141 - SBAS
  #   201     - Iono VTEC


  systems = {"GPS": 1, "GLO": 2, "GAL": 3, "QZSS": 4, "BDS": 5, "SBAS": 6}
  udi = bidict({0:1, 1:2, 2:5, 3:10, 4:15, 5:30, 
       6:60, 7:120, 8:240, 9:300, 10:600, 
       11:900, 12:1800, 13:3600, 14:7200, 15:10800})
  HAScode2IGScode = {"GPS": {0:0, 3:3, 4:4, 5:[3,4], 
                            6:7, 7:8, 8:[7,8],9:10,
                            11:14,12:15,13:[14,15]},
                     "GAL": {0:1, 1:2, 2:[1,2], 3:5,
                             4:6, 5:[5,6], 6:8, 7:9,
                             8:[8,9], 12:15, 13:16,
                             14:[15,16]}}
  HAScode2PPPcode = {"GPS": {0:0, 3:17, 4:18, 5:19, 
                              6:7, 7:8, 8:9, 9:10, 
                              11:14, 12:15, 13:16},
                     "GAL": {0:1, 1:2, 2:3, 3:5,
                             4:6, 5:7, 6:8, 7:9,
                             8:10, 9:11, 10:12, 11:13,
                             12:15, 13:16, 14:17}}
  #cycleLens: the length of a cycle of a signal in mm     
  cycleLens = {"GPS":{0:190, 1:190, 2:190, 3:190, 4:190, 
                     5:244, 6:244, 7:244, 8:244, 10:244, 
                     11:244, 14:255, 15:255},
               "GAL":{0:190, 1:190, 2:190, 5:255, 6:255,
                     8:248, 9:248, 14:234, 15:234, 16:234}}
  def __init__(self):
    pass
  
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

  def IGM01(self, sys, ssr, tow, lowerUDI=True):
    # Orbit correction message is constructed without header first
    msg = ""
    # 6bit no. of satellites
    try:
      orbs = ssr.orbits.orbits[ssr.sysKeys[sys]]
      satNo = ssr.orbits.satNum[ssr.sysKeys[sys]]
    except IndexError:
      raise CorrectionNotAvailable("HAS orbit corrections are not available!")
    nSat = satNo
    for sat in range(satNo):
      # __Sat. Specific__
      dnu = ssr.masks.gnss[ssr.masks.keys.index(ssr.sysKeys[sys])].getDNU(sat)
      if orbs[sat].NAcount == 0 and not dnu: 
        # 6bit Sat. ID
        prn = ssr.masks.getSatNum(ssr.sysKeys[sys], sat)
        msg += np.binary_repr(prn, 6)
        # 8bit GNSS IOD
        iod = orbs[sat].iod &255
        msg+= np.binary_repr(iod, 8)
        # 22bit Delta Orb. Radial
        # 20bit Delta Orbit Along-Track
        # 20bit Delta Orbit Cross-Track
        orbitCorr = self.translateOrbit(orbs[sat])
        msg += orbitCorr
        # 21bit Dot Orb. Radial  <- Not possible
        # 19bit Dot Orbit Along-Track  <- Not possible
        # 19bit Dot Orbit Cross-Track  <- Not possible
        msg += "0"*59
      else:
        nSat -= 1
    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 79)
    for i in range(len(pages)-1):
      # 79bit header(msgnum)
      hdr = self.const_common_header(sys, ssr, 1, tow, nSat, True, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 1, tow, nSat, False, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages

  def IGM02(self, sys, ssr, tow, lowerUDI=True):
    # Clock correction message
    msg = ""
    sub = False
    # is constructed without header first
    # 6bit no. of satellites
    clocks = ssr.clockFull
    if clocks!= None: 
      satNo = ssr.masks.satNums()[ssr.sysKeys[sys]]
    else:
      clocks = ssr.clockSub
      if clocks==None:
        raise CorrectionNotAvailable("HAS clock corrections are not available!")
      sub = True
      satNo = clocks.satNumsSub[ssr.sysKeys[sys]]
    nSat = satNo
    for sat in range(satNo):
      # __Sat. Specific__
      if type(clocks.corrections[ssr.sysKeys[sys]][sat])!= str:
        # 6bit Sat. ID
        if not sub:
          prn = ssr.masks.getSatNum(ssr.sysKeys[sys], sat)
        else:
          prn = clocks.satIDs[ssr.sysKeys[sys]][sat]
        msg += np.binary_repr(prn, 6)
        # 22bit Delta Clock C0
        c0 = self.translateClock(clocks.corrections[ssr.sysKeys[sys]][sat], sys, prn, tow)
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
    pages = self.splitPages(msg, 78)
    for i in range(len(pages)-1):
      # 78bit header(msgnum)
      hdr = self.const_common_header(sys, ssr, 2, tow, nSat, True, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 2, tow, nSat, False, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages


  def translateClock(self, clock, sys, prn, tow):
    c0 = round(clock / 0.0001)
    return np.binary_repr(c0, 22)

  def IGM03(self, sys, ssr, tow, lowerUDI=True):
    # Combined Orbit + Clock correction message
    msg = ""
    sub = False
    # __Header__
    # 79bit header (constructed without for now)
    # 6bit no. of satellites
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
    for sat in range(satNo):
      sat_clk = clocks.corrections[ssr.sysKeys[sys]][sat]
      if orbs[sat].NAcount == 0 and type(sat_clk)!= str:
        # __Sat. Specific__
        # 6bit Sat. ID
        if not sub:
          prn = ssr.masks.getSatNum(ssr.sysKeys[sys], sat)
        else:
          prn = clocks.satIDs[ssr.sysKeys[sys]][sat]
        msg += np.binary_repr(prn, 6)
        # 8bit GNSS IOD
        iod = orbs[sat].iod &255
        msg+= np.binary_repr(iod, 8)
        # 22bit Delta Orb. Radial
        # 20bit Delta Orbit Along-Track
        # 20bit Delta Orbit Cross-Track
        orbitCorr = self.translateOrbit(orbs[sat])
        msg += orbitCorr
        # 21bit Dot Orb. Radial  <- Not possible
        # 19bit Dot Orbit Along-Track  <- Not possible
        # 19bit Dot Orbit Cross-Track  <- Not possible
        msg += "0"*59
        # 22bit Delta Clock C0
        clk = self.translateClock(sat_clk, sys, prn, tow)
        msg += clk
        # 21bit Delta Clock C1  <- Not available
        # 27bit Delta Clock C2  <- Not available
        msg += 48*"0"
      else:
        nSat -= 1
    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 79)
    for i in range(len(pages)-1):
      # 79bit header(msgnum)
      hdr = self.const_common_header(sys, ssr, 3, tow, nSat, True, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 3, tow, nSat, False, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages

  def IGM04(self, sys, ssr, tow, lowerUDI=True):
    # Alternative HR Clock correction message
    msg = ""
    sub = False
    # is constructed without header first
    # 6bit no. of satellites
    clocks = ssr.clockFull
    if clocks!= None: 
      satNo = ssr.masks.satNums()[ssr.sysKeys[sys]]
    else:
      clocks = ssr.clockSub
      if clocks==None:
        raise CorrectionNotAvailable("HAS clock corrections are not available!")
      sub = True
      satNo = clocks.satNumsSub[ssr.sysKeys[sys]]
    nSat = satNo
    for sat in range(satNo):
      # __Sat. Specific__
      if type(clocks.corrections[ssr.sysKeys[sys]][sat])!= str:
        # 6bit Sat. ID
        if not sub:
          prn = ssr.masks.getSatNum(ssr.sysKeys[sys], sat)
        else:
          prn = clocks.satIDs[ssr.sysKeys[sys]][sat]
        msg += np.binary_repr(prn, 6)
        # 22bit Delta Clock C0
        c0 = self.translateClock(clocks.corrections[ssr.sysKeys[sys]][sat], sys, prn, tow)
        msg += c0
      else:
        nSat -= 1
    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 78)
    for i in range(len(pages)-1):
      # 78bit header(msgnum)
      hdr = self.const_common_header(sys, ssr, 4, tow, nSat, True, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 4, tow, nSat, False, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages

  def IGM05(self, sys, ssr, tow, lowerUDI=True):
    #Code bias message
    msg = ""
    # 78bit header (constructed without at first)
    # 6bit no. of satellites
    try:
      codes = ssr.codeBiases.biases_dict[ssr.sysKeys[sys]]
    except TypeError:
      raise CorrectionNotAvailable("HAS Code Biases not available!")
    satNo = codes.mask.nsat
    sats = list(codes.biases.keys())
    assert satNo == len(sats)
    nSat = satNo
    for sat in range(satNo):
      # __Sat. Specific__
      # 6bit Sat. ID
      prn = sats[sat]
      msg += np.binary_repr(prn, 6)
      # 5bit No. of biases
      satCodes = list(codes.biases[prn].keys())
      codeNo = len(satCodes)
      for i in satCodes:
        if codes.biases[prn][i] == "N/A":
          codeNo -= 1
        else:
          if sys=="GPS" and i in [5, 8, 13]:
            codeNo += 1
          elif sys=="GAL" and i in [2, 5, 8, 14]:
            codeNo += 1
          elif i not in self.HAScode2PPPcode[sys].keys():
            codeNo -= 1
      dnu = ssr.masks.gnss[ssr.masks.keys.index(ssr.sysKeys[sys])].getDNU(sat)
      if codeNo > 0 and not dnu:
        msg += np.binary_repr(codeNo, 5)
        # __Bias Specific__
        for code in satCodes:
          if codes.biases[prn][code] != "N/A":
            if code in self.HAScode2PPPcode[sys].keys():
              # 5bit Signal&Tracking mode identifier
              codeID = self.HAScode2PPPcode[sys][code]
              if type(codeID)==list:
                bias = self.translateBias(codes.biases[prn][code], "c")
                for c in codeID:
                  msg += np.binary_repr(c, 5)
                  # 14bit Code Bias
                  msg += np.binary_repr(bias, 14)
              else:
                msg += np.binary_repr(codeID, 5)
                # 14bit Code Bias
                bias = self.translateBias(codes.biases[prn][code], "c")
                msg += np.binary_repr(bias, 14)
      else:
        nSat -= 1
        msg = msg[:len(msg)-6]
    
    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 78)
    for i in range(len(pages)-1):
      # 78bit header(msgnum)
      hdr = self.const_common_header(sys, ssr, 5, tow, nSat, True, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 5, tow, nSat, False, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages

  def IGM06(self, sys, ssr, tow, lowerUDI=True):
    # Phase biases correction message
    msg = ""
    # __Header__
    # 78bit header (added later)
    # 6bit no. of satellites
    try:
      phases = ssr.phaseBiases.biases_dict[ssr.sysKeys[sys]]
    except TypeError:
      raise CorrectionNotAvailable("HAS Phase Biases not available!")
    satNo = phases.mask.nsat
    sats = list(phases.biases.keys())
    assert satNo == len(sats)
    nSat = satNo
    for sat in range(satNo):
      # __Sat. Specific__
      # 6bit Sat. ID
      prn = sats[sat]
      msg += np.binary_repr(prn, 6)
      # 5bit No. of biases
      satPhases = list(phases.biases[prn].keys())
      phaseNo = len(satPhases)
      for i in satPhases:
        if i not in self.HAScode2PPPcode[sys].keys():
          phaseNo -= 1
        elif phases.biases[prn][i][0] == "N/A":
          phaseNo -= 1
        elif sys=="GPS" and i in [5, 8, 13]:
          phaseNo += 1
        elif sys=="GAL" and i in [2, 5, 8, 14]:
          phaseNo += 1
      dnu = ssr.masks.gnss[ssr.masks.keys.index(ssr.sysKeys[sys])].getDNU(sat)
      if phaseNo > 0 and not dnu:
        msg += np.binary_repr(phaseNo, 5)
        # 9bit Yaw angle
        # 8bit Yaw rate
        msg += "0"*(9+8)
        for phase in satPhases:
          if phase != "num":
            if phases.biases[prn][phase][0] != "N/A":
              #   __Bias Specific__
              if phase in self.HAScode2PPPcode[sys].keys():
                # 5bit Signal&Tracking mode identifier
                phaseID = self.HAScode2PPPcode[sys][phase]
                if type(phaseID)==list:
                  bias = self.translateBias(phases.biases[prn][phase][0], "p", sys, phaseID[0])
                  discont = phases.biases[prn][phase][1]
                  for p in phaseID:
                    msg += np.binary_repr(p, 5)
                    # 1bit Signal Integer Ind.
                    # 2bit Signals Wide-Lane Integer Ind.
                    # In the Galileo HAS SIS ICD 1.4, these properties are inevident
                    msg += "000"
                    # 4bit Signal Discont. Counter
                    msg += np.binary_repr(discont, 4)
                    # 20bit Phase Bias
                    msg += np.binary_repr(bias, 20)
                else:
                  msg += np.binary_repr(phaseID, 5)
                  # 1bit Signal Integer Ind.
                  # 2bit Signals Wide-Lane Integer Ind.
                  # In the Galileo HAS SIS ICD 1.4, these properties are inevident
                  msg += "000"
                  # 4bit Signal Discont. Counter
                  discont = phases.biases[prn][phase][1]
                  msg += np.binary_repr(discont, 4)
                  # 20bit Phase Bias
                  bias = self.translateBias(phases.biases[prn][phase][0], "p", sys, phaseID)
                  msg += np.binary_repr(bias, 20)
      else:
        nSat -= 1
        msg = msg[:len(msg)-6]
    #In case the combination of header and message would be longer than the maximum length
    #saveable in 10bits (1024bytes), split message in pages
    if nSat == 0:
      return []
    pages = self.splitPages(msg, 80)
    for i in range(len(pages)-1):
      # 80bit header(msgnum)
      hdr = self.const_common_header(sys, ssr, 6, tow, nSat, True, lowerUDI) 
      pages[i] = self.frame(hdr + pages[i])
    hdr = self.const_common_header(sys, ssr, 6, tow, nSat, False, lowerUDI) 
    pages[-1] = self.frame(hdr + pages[-1])
    return pages
    
  def translateBias(self, HASbias, mode, sys=None, signal=None):
    if mode=="c":
      IGSbias = round(HASbias / 0.01)
    elif mode=="p":
      cycles = HASbias
      #Converting cycles (HAS) to m (IGS): cycles*wavelength[mm] / 0.1
      #/0.1 for IGS resolution of 0.0001m
      IGSbias = round(cycles * self.cycleLens[sys][signal] / 0.1)
    return IGSbias

  def IGM07(self, sys, ssr, tow):
    # URA message, not possible via HAS
    # __Header__
    # 78bit header(msgnum)
    # 6bit no. of satellites
      # __Sat. Specific__
      # 6bit Sat. ID
      # 6bit URA
    raise CorrectionNotAvailable("HAS messages do not contain URA corrections yet")

  def VTEC(self, sys, ssr):
    # Atmospheric correction message, not yet implemented in HAS
    # __Header__
    # 78bit header(msgnum)
    # 9bit VTEC Quality Ind.
    # 2bit No. ionospheric layers
      # __Layer Header__
      # 8bit Height Iono. Layer
      # 4bit Spherical Harmonics Degree
      # 4bit Spherical Harmonics Order
        # __Cosine Coeffs__
        # 16bit Sph.Harm. Coeff. C
      #
        # __Sine Coeffs__
        # 16bit Sph.Harm. Coeff. S
    raise CorrectionNotAvailable("HAS messages do not contain atmospheric corrections yet")

  def const_common_header(self, sys, ssr, msgNum, tow, nSat, multMess=False, lowerUDI=True):
    hdr = ""
    # __Header__
    # 12bit RTCM Message number (always 4076)
    hdr += "111111101100"
    # 3bit IGS SSR version (current document: v1.0)
    hdr += "001"
    # 8bit Sub-type number, dep on system
    subtype = self.systems[sys]*20+msgNum if type(msgNum)==int else 201
    hdr += np.binary_repr(subtype, 8)
    # 20bit SSR epoch time, 1s
    hdr += self.calc_tow(ssr, tow)
    # 4bit update interval       
    # User flag to choose upper or lower UDI when in doubt: Use opt. lowerUDI
    udi = self.ret_udi(self.ssr_block(ssr, msgNum), lowerUDI=lowerUDI)
    hdr += np.binary_repr(udi, 4)
    # 1bit multiple message indicator
    hdr += np.binary_repr(multMess*1,1)
    # 4bit IOD SSR
    iod = 1 #This code is v1.0 of the SSR generation
    hdr += np.binary_repr(iod, 4)
    # 16bit Provider ID
    providID = HAS_PROVIDER_ID
    hdr += np.binary_repr(providID, 16)
    # 4bit solution ID
    hdr += np.binary_repr(0, 4)
    if msgNum == 1 or msgNum == 3:
      # 1bit global/regional crs indicator
      hdr += "0"
    elif msgNum == 6:
      # 1bit Dispersive Bias Consist. ind.
      # 1bit MW Consistency Ind.
      # In the Galileo HAS SIS ICD 1.4, these properties are inevident
      hdr += "00"
    # 6bit number of satellites
    hdr += np.binary_repr(nSat, 6)
    # ---78-80bit---
    return hdr

  def translateOrbit(self, orb):
    dRad = round(orb.deltaRad / 0.0001)
    dRad = np.binary_repr(dRad, 22)
    dAlong = round(orb.deltaInTrack / 0.0004)
    dAlong = np.binary_repr(dAlong, 20)
    dCross = round(orb.deltaCrossTrack / 0.0004)
    dCross = np.binary_repr(dCross, 20)
    return dRad + dAlong + dCross

  def calc_tow(self, ssr, tow):
    tow_h = int(tow / 3600)
    toh_rec = tow % 3600 /60
    toh_has = ssr.header.toh
    if toh_rec <= 10 and toh_has/60 >= 50:
      tow_h -= 1
    tow = tow_h*3600 + toh_has
    return np.binary_repr(tow, 20)

  def ssr_block(self, ssr, msgNum):
    read = {0:ssr.masks, 1:ssr.orbits, 
            2:[ssr.clockFull, ssr.clockSub],
            3:[ssr.orbits, ssr.clockFull, ssr.clockSub], 
            5:ssr.codeBiases, 6:ssr.phaseBiases}
    return read[msgNum]

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

  def frame(self, msg):
    padded = msg + (8-(len(msg)%8))*"0"
    mLen = int(len(padded)/8)
    frame = "11010011" #Preamble, 11010011 (0xD3)
    frame = frame + "000000" #zeros
    frame = frame + np.binary_repr(mLen, 10)
    parity = np.binary_repr(crc.crc24q(bits2Bytes(frame+padded), mLen+3), 24)
    framed = frame + padded + parity
    return framed
