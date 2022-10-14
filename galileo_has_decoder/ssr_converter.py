#!/usr/bin/env python

'''
General SSR converter class

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

import datetime
from galileo_has_decoder.ssr_igs import SSR_IGS
from galileo_has_decoder.ssr_rtcm import SSR_RTCM
from galileo_has_decoder.ssr_classes import SSR, SSR_HAS
class ConversionError(Exception):
  #Base class for converter errors
  pass

class SSR_Converter:
  ssr = None
  ssr_has = None
  ssr_igs = None
  ssr_rtcm = None
  msg_in = None
  msg_out = None
  content = None
  pppWiz = None
  verbose = None
  def __init__(self, mode=None, compact=None, pppWiz=False, verbose=0):
    self.verbose = 0
    if mode != None:
      self.mode = mode
    if compact != None:
      self.compact = compact
    if verbose != None:
      self.verbose = verbose
    self.pppWiz = pppWiz
    pass

  def feedMessage(self, msg):
    #Input msg: Bitstring of decoded HAS message
    self.ssr = SSR()
    self.ssr_has = SSR_HAS(msg, self.ssr, self.verbose)
    self.content = list(self.ssr.header.msgContent.values())
    self.msg_in = msg
    self.msg_out = []
    if self.verbose>3:
      self.ssr.printData()

  def convertMessage(self, msg, mode=None, compact=True, HRclk=False, tow=None, lowerUDI=True, verbose=None):
    self.feedMessage(msg)
    return self.convert(mode, compact=compact, HRclk=HRclk, tow=tow, verbose=verbose)

  def setVerbose(self, verbose):
    self.verbose = verbose

  def convert(self, mode=None, compact=True, HRclk=False, tow=None, lowerUDI=True, verbose=None):
    if mode == None:
      try:
        mode = self.mode
      except AttributeError:
        raise ConversionError("No mode selected. Please select 1 for IGS or 2 for RTCM3")
    if "compact" in self.__dict__:
      compact = self.compact
    if verbose == None:
      verbose = self.verbose
    if tow == None:
      tod = datetime.datetime.today()
      begin = tod - datetime.timedelta(tod.weekday(), hours=tod.hour, minutes=tod.minute, seconds=tod.second, microseconds=tod.microsecond)
      tow = int((tod-begin).total_seconds())
    if verbose>=3:
      print("Current ToW:", tow)
    if self.ssr_has.valid:
      #Modes: {1,2}; target format (igs, rtcm)
      self.msg_out = []
      #IGS Messages
      if mode == 1:
        self.ssr_igs = SSR_IGS()
        for s in self.ssr.masks.gnss:
          sys = self.ssr.sysKeys.inverse[s.id][0]
          if compact:
            if self.content[1] and self.content[2]:
              if verbose>=1:
                print("Creating combined Orbit+Clock Message")
              self.msg_out += self.ssr_igs.IGM03(sys, self.ssr, tow, lowerUDI)
            else:
              if self.content[1]:
                if verbose>=1:
                  print("Creating Orbit Message")
                self.msg_out += self.ssr_igs.IGM01(sys, self.ssr, tow, lowerUDI)
              if self.content[2] or self.content[3]:
                if HRclk:
                  if verbose>=1:
                    print("Creating HR Clock Message")
                  self.msg_out += self.ssr_igs.IGM04(sys, self.ssr, tow, lowerUDI)
                else:
                  if verbose>=1:
                    print("Creating Clock Message")
                  self.msg_out += self.ssr_igs.IGM02(sys, self.ssr, tow, lowerUDI)
          else:
            if self.content[1]:
              if verbose>=1:
                print("Creating Orbit Message")
              self.msg_out += self.ssr_igs.IGM01(sys, self.ssr, tow, lowerUDI)
            if self.content[2] or self.content[3]:
              if HRclk:
                if verbose>=1:
                  print("Creating HR Clock Message")
                self.msg_out += self.ssr_igs.IGM04(sys, self.ssr, tow, lowerUDI)
              else:
                if verbose>=1:
                  print("Creating Clock Message")
                self.msg_out += self.ssr_igs.IGM02(sys, self.ssr, tow, lowerUDI)
          if self.content[4]:
            if verbose>=1:
              print("Creating Code Bias Message")
            self.msg_out += self.ssr_igs.IGM05(sys, self.ssr, tow, lowerUDI)
          if self.content[5]:
            if verbose>=1:
              print("Creating Phase Bias Message")
            self.msg_out += self.ssr_igs.IGM06(sys, self.ssr, tow, lowerUDI)
      #RTCM Messages
      elif mode == 2:
        self.ssr_rtcm = SSR_RTCM()
        for s in self.ssr.masks.gnss:
          try:
            sys = self.ssr.sysKeys.inverse[s.id][0]
          except KeyError:
            print("WARNING: Faulty system key encountered: ["+str(s.id)+"]. Proceeding.")
            continue
          if compact:
            if self.content[1] and self.content[2]:
              if verbose>=1:
                print("Creating combined Orbit+Clock Message")
              self.msg_out += self.ssr_rtcm.ssr4(sys, self.ssr, tow, lowerUDI)
            else:
              if self.content[1]:
                if verbose>=1:
                 print("Creating Orbit Message")
                self.msg_out += self.ssr_rtcm.ssr1(sys, self.ssr, tow, lowerUDI)
              if self.content[2] or self.content[3]:
                if HRclk:
                  if verbose>=1:
                    print("Creating HR Clock Message")
                  self.msg_out += self.ssr_rtcm.ssr6(sys, self.ssr, tow, lowerUDI)
                else:
                  if verbose>=1:
                    print("Creating Clock Message")
                  self.msg_out += self.ssr_rtcm.ssr2(sys, self.ssr, tow, lowerUDI)
          else:
            if self.content[1]:
              if verbose>=1:
                print("Creating Orbit Message")
              self.msg_out += self.ssr_rtcm.ssr1(sys, self.ssr, tow, lowerUDI)
            if self.content[2] or self.content[3]:
              if HRclk:
                if verbose>=1:
                  print("Creating HR Clock Message")
                self.msg_out += self.ssr_rtcm.ssr6(sys, self.ssr, tow, lowerUDI)
              else:
                if verbose>=1:
                  print("Creating Clock Message")
                self.msg_out += self.ssr_rtcm.ssr2(sys, self.ssr, tow, lowerUDI)
          if self.content[4]:
            if verbose>=1:
              print("Creating Code Bias Message")
            self.msg_out += self.ssr_rtcm.ssr3(sys, self.ssr, tow, lowerUDI)
          if self.content[5]:
            if verbose>=1:
              print("Creating Phase Bias Message")
            self.msg_out += self.ssr_rtcm.ssrp(sys, self.ssr, tow, lowerUDI)
      return self.msg_out
    else: return []
