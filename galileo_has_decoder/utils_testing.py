#!/usr/bin/env python

'''
Simple testing utils

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

from galileo_has_decoder.utils import bytes2bits, bytesFromList, splitStringBytes
import numpy as np
from reedsolo import RSCodec
def construct32s(pages):
  words = {}
  for i in range(53):
    word = bytearray()
    for p in pages[:min(len(pages), 32)]:
      word = word+p[i]#int(p[i], 2).to_bytes(1,"big")
    if len(pages) < 32:
      word = word + bytearray([0])*(32-len(pages))
    words[i] = word
  return words

#SOURCE: https://www.geeksforgeeks.org/modulo-2-binary-division/
# Returns XOR of 'a' and 'b'
# (both of same length)
def xor(a, b):
 
    # initialize result
    result = []
 
    # Traverse all bits, if bits are
    # same, then XOR is 0, else 1
    for i in range(1, len(b)):
        if a[i] == b[i]:
            result.append('0')
        else:
            result.append('1')
 
    return ''.join(result)

# Performs Modulo-2 division
def mod2div(divident, divisor):
 
    # Number of bits to be XORed at a time.
    pick = len(divisor)
 
    # Slicing the divident to appropriate
    # length for particular step
    tmp = divident[0 : pick]
 
    while pick < len(divident):
 
        if tmp[0] == '1':
 
            # replace the divident by the result
            # of XOR and pull 1 bit down
            tmp = xor(divisor, tmp) + divident[pick]
 
        else:   # If leftmost bit is '0'
            # If the leftmost bit of the dividend (or the
            # part used in each step) is 0, the step cannot
            # use the regular divisor; we need to use an
            # all-0s divisor.
            tmp = xor('0'*pick, tmp) + divident[pick]
 
        # increment pick to move further
        pick += 1
 
    # For the last n bits, we have to carry it out
    # normally as increased value of pick will cause
    # Index Out of Bounds.
    if tmp[0] == '1':
        tmp = xor(divisor, tmp)
    else:
        tmp = xor('0'*pick, tmp)
 
    checkword = tmp
    return checkword

# Function used at the sender side to encode
# data by appending remainder of modular division
# at the end of data.
def crc(data, key, check=False, verbose=False, leadbytes=False):
    if type(data) == bytearray:
      data = bytes2bits(data)
    l_key = len(key)
    if leadbytes:
      data = (l_key-1)*"1" + data
 
    # Appends n-1 zeroes at end of data
    appended_data = data + '0'*(l_key-1)
    remainder = mod2div(appended_data, key)
 
    # Append remainder in the original data
    codeword = data + remainder
    if verbose:
      print("Remainder : ", remainder)
      print("Encoded Data (Data + Remainder) : ",
            codeword)
    if check:
      return(remainder)
    return(remainder, codeword)

def rsEncode(octets, _rscoder=None):
  if(_rscoder == None):
    rscoder = RSCodec(nsym=223, fcr=1)
  else:
    rscoder = _rscoder
  codes = {}
  for i in range(len(octets)):
    codes[i] = rscoder.encode(octets[i])
  return codes

def constructHAS(codes):
  messages = {}
  for i in range(len(codes[0])):
    messages[i] = bytearray()
    for j in range(len(codes)):
      messages[i] = messages[i] + codes[j][i].to_bytes(1,"big")
  return messages

def encodeHAS(pages):
  rscoder = RSCodec(nsym=223, fcr=1)
  octets = construct32s(pages)
  codes = rsEncode(octets, rscoder)
  messages = constructHAS(codes)
  return messages, octets, rscoder

def constructPageHeader(
    mid, #Message ID, 0-31
    pid, #Page ID of current, encoded message
    msize, #Total, decoded Message size (1-32)
    mt="mt1", #Message type, currently only MT1 exists
    dtype="s"): #Datatype: s for bitstring or b for bytearray
    
  header = ""
  if mt == "mt1":
    header += "00" #Status: test mode
    header += "00" #Reserved
    header += "01" #Message type MT1
    header += np.binary_repr(mid, width=5) #Message ID representation
    header += np.binary_repr(msize, width=5) #Message size representation
    header += np.binary_repr(pid, width=8) #Page ID (1-255)
  else:
    pass
  if dtype == "b": #datatype: bytes
    header = bytesFromList(splitStringBytes(header))
  return header

def constructHASmsg(content, verb=0, dataAvailable=False, sys="GAL"):
  header = ["", ""]
  contentB = ["", "", "", "", "", ""]
  header[0] = "001001011000"
  header[1] = "00000000100001"
  contentB[0] = "00010010110110110000000000000000000000000000000010101000000000001111110111101111011000000000"
  contentB[1] = "0101000001111110000000000001000000000001000000000000000011111100000000000010000000000010000000000000000111111000000000000100000000000100000000000000001111110000000000001000000000001000000000000000011111100000000000010000000000010000000000000000111111000000000000100000000000100000000000"
  contentB[2] = "010101100001000000001111111111111000000100000100000000010010010000000001100000000000"
  contentB[3] = "010100010010111010111000000000000010001011010101111111111111001101001010"
  contentB[4] = "0101010101100101010111010010101110100010101100101010111010010101110100010101100110101011000001010110010010101100001010111010001010110010101011101000101011001101010110010"
  contentB[5] = "0101010101100100010101110100000101011001101010101100100010101110100001010111010000010101100110101010110010000101011001010010101100110110101110100110101011001000010101100110101010110011000101011001010"
  if dataAvailable:
    print("Making some data available")
    contentB[1] = "0101000001111111000000000001000000010001001000000000000011111011000000000010000001100010101000000000000111111000000000000100000000000100000000000000001111110000000000001000000000001000000000000000011111100000000000010000000000010000000000000000111111000000000111111010000000100000110100"
    contentB[2] = "010101100001000000001111110111111000000100000100000000010010010000000001100000000000"
  if sys=="GPS":
    print("Switching to GPS Message")
    contentB[0] = "00010000110110110000000000000000000000000000000010101000000000001111110111101111011000000000"
    contentB[1] = "0101000011111100000000000100000001000100100000000000011110110000000000100000011000101010000000000011111000000000000100000000000100000000000000011111000000000000100000000000100000000000000011111000000000000100000000000100000000000000011111000000000111111010000000100000110100"
    
  
  msg = header[0] + content + header[1]
  lens = []
  for s in range(len(contentB)):
    if int(content[s]):
      lens += [len(contentB[s])]
      msg = msg+contentB[s]
  if verb>=1:
    print(lens)
  return msg
