#!/usr/bin/env python

'''
Main library interface class

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
Modified 2023-09-29  Jaakko Yliaho / Uwasa to add NOV_Reader
'''

from galileo_has_decoder.sbf_reading import SBF_Reader
from galileo_has_decoder.binex_reading import Binex_Reader
from galileo_has_decoder.tcp_sbf_reading import TCP_SBF_Reader
from galileo_has_decoder.tcp_binex_reading import TCP_Binex_Reader
from galileo_has_decoder.serial_reading import Serial_SBF_Reader, Serial_Binex_Reader
from galileo_has_decoder.nov_reading import NOV_Reader
from galileo_has_decoder.tcp_server import TCP_Server
from galileo_has_decoder.ssr_converter import SSR_Converter
from galileo_has_decoder.file_write import File_Writer, PPP_Wiz_Writer
import serial

class Source_Error(Exception):
    #The source could not be determined or there was an error
    pass
class Mode_Error(Exception):
    #Basic error when determining the mode of the converter
    pass

class HAS_Converter:
    reader = None
    converter = None
    tcp = None
    def __init__(self, source, target, outFormat, modeIn=None, modeOut=None, port=None, baudrate=115200, skip=0.0, mute=0):
        #Source Initialization
        if modeIn == None:
            if str(source).replace(".", "").isnumeric() or 'localhost' in str(source).lower():
                modeIn = 5
            elif "." in source:
                if ".sbf" in str(source).lower():
                    modeIn = 1
                elif ".bnx" in str(source).lower():
                    modeIn = 2
            else: 
                raise Source_Error("Error: For serial communication, please specify modeIn to be [3, 4] for SBF or BINEX")
        self.modeIn = modeIn = int(modeIn)
        if modeIn == 1:
            inp = "SBF file"
            self.reader = SBF_Reader(source, skip=float(skip))
        elif modeIn == 2:
            inp = "BINEX file"
            self.reader = Binex_Reader(source, skip=float(skip))
            pass
        elif modeIn == 3:
            inp = "Serial SBF Stream on port " + str(source)
            try:
                self.reader = Serial_SBF_Reader(source, int(baudrate))
            except serial.serialutil.SerialException:
                raise Source_Error("Error: There was an error opening the SBF serial port indicated.")
        elif modeIn == 4:
            inp = "Serial BINEX Stream on port " + str(source)
            try:
                self.reader = Serial_Binex_Reader(source, int(baudrate))
            except serial.serialutil.SerialException:
                raise Source_Error("Error: There was an error opening BINEX the serial port indicated.")
        elif modeIn == 5:
            inp = "SBF TCP stream on " + str(source)
            self.reader = TCP_SBF_Reader(source)
        elif modeIn == 6:
            inp = "BINEX TCP stream on " + str(source)
            self.reader = TCP_Binex_Reader(source)
        elif modeIn == 7:
            inp = "Novatel GALCNAVRAWPAGE ASCII file"
            self.reader = NOV_Reader(source, skip=float(skip))
        #Target Initialization
        if modeOut == None:
            if target.replace(".", "").isnumeric() or target == 'localhost':
                modeOut = 1
            elif target == 'console':
                modeOut = 4
            else:
                modeOut = 2
        modeOut = int(modeOut)
        if modeOut == 1:
            if port==None: port = 6947
            else: port = int(port)
            self.output = TCP_Server(target, port)
            out = "TCP server on address " + str(target) + ", port " + str(port)
        elif modeOut == 2:
            self.output = File_Writer(target)
            out = "file named " + str(target)
        elif modeOut == 3:
            self.output = PPP_Wiz_Writer(target, mode=3)
            out = "PPP Wizard file named " + str(target)
        elif modeOut == 4:
            out = "stream in PPP Wizard format"
            self.output = PPP_Wiz_Writer(target, mode=4)
        else:
            raise Mode_Error("The output mode could not be recognized. Possibilities are: [1:TCP, 2:File, 3:PPP Wizard Stream]")

        #Converter Initialization
        if outFormat == 1 or str(outFormat).upper() == "IGS" or outFormat == "1":
            self.converter = SSR_Converter(1, True, pppWiz=(modeOut==3 or modeOut==4))
            fmt = "IGS messages"
        elif outFormat == 2 or str(outFormat).upper() == "RTCM" or outFormat == "2":
            self.converter = SSR_Converter(2, True, pppWiz=(modeOut==3 or modeOut==4))
            fmt = "RTCM 3.0 messages"
        else:
            raise Mode_Error("The output format could not be recognized. Possibilities are: [1:IGS, 2:RTCM3]")
        
        if modeOut != 4 and not mute:
            print("--- Set up converter ---\nReading HAS messages from a " + inp
                + " and converting to " + fmt + ". Output will be written to a " + out + ".")

    def convertAll(self, compact=True, HRclk=False, lowerUDI=True, verbose=0):
        #Convert all messages available from the source
        if verbose != 0 and self.converter != None:
            self.converter.setVerbose(verbose)
        if self.modeIn == 1 or self.modeIn == 2 or self.modeIn == 5 or self.modeIn == 6 or self.modeIn == 7:
            self.reader.read(converter=self.converter, output=self.output, compact=compact, HRclk=HRclk, verbose=verbose)
        elif self.modeIn == 3 or self.modeIn == 4:
            self.reader.read(converter=self.converter, output=self.output, compact=compact, HRclk=HRclk, verbose=verbose)
        pass

    def convertX(self, x, compact=True, HRclk=False, lowerUDI=True, verbose=0):
        if verbose != 0 and self.converter != None:
            self.converter.setVerbose(verbose)
        #Convert X messages from the source
        if self.modeIn == 1 or self.modeIn == 2 or self.modeIn == 5 or self.modeIn == 6 or self.modeIn == 7:
            self.reader.read(converter=self.converter, output=self.output, x=x, compact=compact, HRclk=HRclk, verbose=verbose)
        elif self.modeIn == 3 or self.modeIn == 4:
            self.reader.read(converter=self.converter, output=self.output, x=x, compact=compact, HRclk=HRclk, verbose=verbose)
        pass

    def convertUntil(self, s, compact=True, HRclk=False, lowerUDI=True, verbose=0):
        if verbose != 0 and self.converter != None:
            self.converter.setVerbose(verbose)
        #Convert messages from the source for s seconds
        if self.modeIn == 1 or self.modeIn == 2 or self.modeIn == 7:
            raise Mode_Error("ERROR: Timed constraint not available for file reading.")
        elif self.modeIn >= 3 and self.modeIn <= 6:
            self.reader.read(converter=self.converter, output=self.output, mode="t", x=s, compact=compact, HRclk=HRclk, verbose=verbose)
        pass

    
