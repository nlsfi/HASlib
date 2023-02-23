import sys, getopt
from galileo_has_decoder import conv
from galileo_has_decoder.utils import bidict
optDict = bidict({"s":"source", "t":"target", "f":"outFormat", "i":"modeIn", "o":"modeOut", "p":"port", "b":"baudrate", "v":"verbose", "m":"mute", "h":"help"})

def printHelp():
    print("The HAS_Decoder.py offers easy access to most of the functionalities of the Galileo HAS Decoder. Below, available arguments are presented. For more options, please refer to the library documentation.\n")
    print("Usage: python3 HAS_Decoder.py -s SOURCE -t TARGET -f OUTFORMAT [-i MODEIN -o MODEOUT -p PORT -b BAUDRATE -x MESSAGES -v VERBOSELEVEL --skip SKIPPERCENT --mute]\n")
    print("-s arg    : Source stream to decode messages from")
    print("-t arg : Target stream to decode messages to")
    print("-f opt : Format to convert HAS messages to. Options are [1:IGS, 2:RTCM3]")
    print("-i opt : Input mode, specifying the type of input stream. Options are :",
        "\n         [1:SBF File, 2:BINEX File, 3:SBF Serial, 4:BINEX Serial, 5:SBF TCP, 6:BINEX TCP]")
    print("-o opt : Output mode, specifying the type of output stream. Options are:",
        "\n         [1:TCP, 2:File, 3:PPPWiz File, 4:PPPWiz Stream]")
    print("-p arg : Optional for TCP output. If not set, uses port 6947")
    print("-b arg : Optional for serial input, specifying the baudrate of the stream. If not set, uses 115200")
    print("-v arg : Optional, specifying the verbose level for the process")
    print("-m     : Optional, used to mute verbose-independent messages")
    print("-h     : Displaying this help message")  
    print("--source arg    : Source stream to decode messages from")
    print("--target arg    : Target stream to decode messages to")
    print("--outFormat opt : Format to convert HAS messages to. Options are [1:IGS, 2:RTCM3]")
    print("--modeIn opt    : Input mode, specifying the type of input stream. Options are :",
        "\n                  [1:SBF File, 2:BINEX File, 3:SBF Serial, 4:BINEX Serial, 5:SBF TCP, 6:BINEX TCP]")
    print("--modeOut opt   : Output mode, specifying the type of output stream. Options are:",
        "\n                  [1:TCP, 2:File, 3:PPPWiz File, 4:PPPWiz Stream]")
    print("--port arg      : Optional for TCP output. If not set, uses port 6947")
    print("--baudrate arg  : Optional for serial input, specifying the baudrate of the stream. If not set, uses 115200")
    print("--skip arg      : Optional, used to skip some initial portion of a read file.")
    print("--verbose arg   : Optional, specifying the verbose level for the process")
    print("--mute          : Optional, used to mute verbose-independent messages")
    print("--help          : Displaying this help message")
    exit()

try:
    options, remainder = getopt.getopt(sys.argv[1:], 's:t:f:i:o:p:b:x:v:hm:mm:', ['source=', 
                                                        'target=',
                                                        'outFormat=',
                                                        'modeIn=',
                                                        'modeOut=',
                                                        'port=',
                                                        'baudrate=',
                                                        'verbose=',
                                                        'skip=',
                                                        'help',
                                                        'mute',
                                                        ])
except getopt.GetoptError:
    raise Exception("Options not recognized. Correct usage:\nHAS_Decoder.py -s SOURCE -t TARGET -f OUTFORMAT [-i MODEIN -o MODEOUT -p PORT -b BAUDRATE -x MESSAGES]")
opts = {}
adds = {}
for o in options:
    if len(o[0]) > 2:
        try:
            opts[optDict.inverse[o[0][2:]][0]] = o[1]
        except KeyError:
            adds[o[0][2:]] = o[1]
    else:
        opts[o[0][1:]] = o[1]
inputs = opts.keys()
if "h" in inputs:
    printHelp()

if "s" not in inputs or "t" not in inputs or "f" not in inputs:
    raise Exception("Too few options. Provide at least a source, a target and a output format. Correct usage:\nconv.py -s SOURCE -t TARGET -f OUTFORMAT [-i MODEIN -o MODEOUT -p PORT -b BAUDRATE -x MESSAGES]")
args = ["s","t","f","i","o","p"]
brate = opts["b"] if "b" in opts.keys() else 115200
skip = adds["skip"] if "skip" in adds.keys() else 0.0
mute = opts["m"] if "m" in opts.keys() else 0

converter = conv.HAS_Converter(*[opts[x] if x in opts.keys() else None for x in args], baudrate=brate, skip=skip, mute=mute)
if 'h' in inputs or "help" in inputs:
    #Print help message
    pass
if "x" in inputs:
    converter.convertX(int(opts["x"]), verbose=int(opts["v"]) if "v" in inputs else 0)
else:
    converter.convertAll(verbose=int(opts["v"]) if "v" in inputs else 0)
