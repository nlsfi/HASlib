# Galileo HAS Decoder & Converter Documentation

| VER | DATE | AUTHOR |
| --- | ---- | ------ |
| 1.0 | 09/12/2021 | Oliver Horst / FGI |
| 1.0.2 | 31/05/2023 | Martti Kirkko-Jaakkola / FGI |

## Basic Usage
### HAS_Converter
Basic class for using the library. Can be used for the whole pipeline from data reading over decoding to outputting converted messages in IGS or RTCM format.

>**HAS_Converter**(*source, target, outFormat, modeIn, modeOut, port, baudrate, skip, mute*)  
*source*: The source. Can be a filename/path or portname.   
*target*: The output target. Can be a filename/path or an IP address for a TCP server.  
*out_format*: The format of the output. Options are [1:IGS, 2:RTCM3].  
*modeIn*: Optional. Determining the mode of input. If not set, looks for file endings. Options are [1:SBF File, 2:BINEX File, 3:SBF Serial, 4:BINEX Serial, 5:SBF TCP, 6:BINEX TCP]   
*modeOut*: Optional. Determining the mode of output. If not set, decides based on all-numeric IP (excl. dots) or not. Options are: [1:TCP, 2:File, 3:PPPWiz File, 4:PPPWiz Stream]  
*port*: Optional for TCP output. If not set, uses port 6947.   
*baudrate*: Optional for serial input. If not set, uses 115200.  
*skip*: Optional for file input. Used to skip an initial portion of the file.  
*mute*: Optional. Pass _True_ or _1_ to suppress verbose-independent messages.

>*HAS_Converter*.**convertAll**(*compact, HRclk, lowerUDI, verbose*)  
Used to decode and convert all available messages from a file or a serial port.  
*compact*: Optional. Truth value whether to prefer combined (Orb+Clk) over individual messages. Default:True.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Verbose level for the process.

>*HAS_Converter*.**convertX**(*x, compact, HRclk, lowerUDI, verbose*)  
Used to decode and convert a number of messages from a file or a serial port.  
*x*: Number of messages to decode and convert. Please note that this limit includes non-HAS messages.  
*compact*: Optional. Truth value whether to prefer combined (Orb+Clk) over individual messages. Default:True.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Verbose level for the process.

>*HAS_Converter*.**convertUntil**(*s, compact, HRclk, lowerUDI, verbose*)  
Only available for serial port input. Decodes and converts incoming messages for a specified timespan.  
*s*: Timespan [s] to run.  
*compact*: Optional. Truth value whether to prefer combined (Orb+Clk) over individual messages. Default:True.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Verbose level for the process.
___

## Advanced Usage
Most of the libraries work can be done in the background with little need to dig into the deeper bits of the library. However, if needed for e.g. further development, the following presents the important classes and their interfacing.

### Binex_Reader
Reader class for Binex files, reading out C/Nav messages. Can be used on various levels, from just decoding HAS messages to also outputting converted messages.
>**Binex_Reader**(*path, msgnum, skip*)  
*path*: Path of the BINEX file to open.  
*msgnum*: Optional. Used to specify the default number of messages to read at once. If not set, the default is to read all available messages.  
*skip*: Optional. Used to skip a portion of the file (0.0 - 1.0) before processing.  

>*Binex_Reader*.**read**(*path, converter, output, mode, x, compact, HRclk, lowerUDI, verbose*)  
On default, reads x messages from a file as indicated on initialization. Can be modified using optional parameters.  
*path*: Optional. Used to open a new BINEX file.  
*converter*: Optional. If passed an instance of type *SSR_Converter*, can convert decoded messages.  
*output*: Optional. If passed an instance of *TCP_Server* or *File_Writer*, outputs converted messages to the channel indicated.  
*mode*: Optional. Indicating the mode of operation. Only "m" is supported for *Binex_Reader*.  
*x*: Optional. Used to indicate the number of messages to read.  
*compact*: Optional. Truth value whether to prefer combined (Orb+Clk) over individual messages. Default:True.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Verbose level for the process.

>*Binex_Reader*.**findMessage**(*stream, pC, i, verbose*)   
Function to find the start of the next message in a bytearray-like structure.  
*stream*: The file/datastream to search in  
*pC*: current pagecount. Large files can be split in multiple pages, pC indicating the current page  
*i*: The position of the "carriage" in the stream  
*verbose*: Optional. Verbose level for the process.  
Returns (stream, pC), with stream being modified to begin at the start of the new message and pC being the updated current page number.

### Serial_Binex_Reader
Reader class for BINEX datastreams on a serial port. Besides the change in source, behaves the same as the *Binex_Reader*.
>**Serial_Binex_Reader**(*port, baudr, msgnum*)  
*port*: Portname of the port used by the device sending the serial stream.  
*baudr*: Optional. The baudrate to use. Default is the Septentrio baudrate 115200.  
*msgnum*: Optional. Used to specify the default number of messages to read at once. If not set, the default is to read all available messages.

>*Serial_Binex_Reader*.**read**(*converter, output, mode, x, compact, HRclk, lowerUDI, verbose*)  
On default, reads x messages from a serial port as indicated on initialization. Can be modified using optional parameters.  
*converter*: Optional. If passed an instance of type *SSR_Converter*, can convert decoded messages.  
*output*: Optional. If passed an instance of *TCP_Server* or *File_Writer*, outputs converted messages to the channel indicated.  
*mode*: Optional. Used to indicate the mode of operation: [m:message numbers, t:time limit].  
*x*: Optional. Used to indicate the number of messages to read.  
*compact*: Optional. Truth value whether to prefer combined (Orb+Clk) over individual messages. Default:True.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Verbose level for the process.  

### TCP_Binex_Reader
Reader class for BINEX datastreams from a TCP client. Besides the change in source, behaves the same as the *Binex_Reader*.
>**TCP_Binex_Reader**(*src, msgnum*)  
*src*: The address and port to open a TCP server on. Indicate in the following format: "address:port"   
*msgnum*: Optional. Used to specify the default number of messages to read at once. If not set, the default is to read all available messages.

>*TCP_Binex_Reader*.**read**(*src, converter, output, mode, x, compact, HRclk, lowerUDI, verbose*)  
On default, reads x messages from a TCP stream as indicated on initialization. Can be modified using optional parameters.  
*src*: Optional. Used if the source to read from should differ from the one indicated in advance.
*converter*: Optional. If passed an instance of type *SSR_Converter*, can convert decoded messages.  
*output*: Optional. If passed an instance of *TCP_Server* or *File_Writer*, outputs converted messages to the channel indicated.  
*mode*: Optional. Used to indicate the mode of operation: [m:message numbers, t:time limit].  
*x*: Optional. Used to indicate the number of messages to read.  
*compact*: Optional. Truth value whether to prefer combined (Orb+Clk) over individual messages. Default:True.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Verbose level for the process.

### SBF_Reader
Reader class for SBF files, reading out C/Nav messages. Can be used on various levels, from just decoding HAS messages to also outputting converted messages.
>**SBF_Reader**(*path, msgnum, skip*)  
*path*: Path of the SBF file to open.  
*msgnum*: Optional. Can already be used to specify a number of messages to read on default.  
*skip*: Optional. Used to skip a portion of the file (0.0 - 1.0) before processing.

>*SBF_Reader*.**read**(*path, converter, output, mode, x, compact, HRclk, lowerUDI, verbose*)  
On default, reads x messages from a file as indicated on initialization. Can be modified using optional parameters.  
*path*: Optional. Used to open a new SBF file.  
*converter*: Optional. If passed an instance of type *SSR_Converter*, can convert decoded messages.  
*output*: Optional. If passed an instance of *TCP_Server* or *File_Writer*, outputs converted messages to the channel indicated.  
*mode*: Optional. Used to indicate the mode of operation. Only "m" is supported for *SBF_Reader*.  
*x*: Optional. Used to indicate the number of messages to read.  
*compact*: Optional. Truth value whether to prefer combined (Orb+Clk) over individual messages. Default:True.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Verbose level for the process.

>*SBF_Reader*.**findMessage**(*stream, pC, verbose*)   
Function to find the start of the next message in a bytearray-like structure.  
*stream*: The file/datastream to search in.  
*pC*: current pagecount. Large files can be split in multiple pages, pC indicating the current page.   
*verbose*: Optional. Verbose level for the process.  
Returns (stream, pC), with stream being modified to begin at the start of the new message and pC being the updated current page number.

### Serial_SBF_Reader
Reader class for SBF datastreams on a serial port. Besides the change in source, behaves the same as the *SBF_Reader*.
>**Serial_SBF_Reader**(*port, baudr, msgnum*)  
*port*: Portname of the port used by the device sending the serial stream.  
*baudr*: Optional. The baudrate to use. Default is the Septentrio baudrate 115200.  
*msgnum*: Optional. Used to specify the default number of messages to read at once. If not set, the default is to read all available messages.

>*Serial_SBF_Reader*.**read**(*converter, output, mode, x, compact, HRclk, lowerUDI, verbose)  
On default, reads x messages from a serial port as indicated on initialization. Can be modified using optional parameters.  
*converter*: Optional. If passed an instance of type *SSR_Converter*, can convert decoded messages.  
*output*: Optional. If passed an instance of *TCP_Server* or *File_Writer*, outputs converted messages to the channel indicated.  
*mode*: Optional. Used to indicate the mode of operation: [m:message numbers, t:time limit].  
*x*: Optional. Used to indicate the number of messages to read.  
*compact*: Optional. Truth value whether to prefer combined (Orb+Clk) over individual messages. Default:True.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Verbose level for the process.

### TCP_SBF_Reader
Reader class for SBF datastreams from a TCP client. Besides the change in source, behaves the same as the *SBF_Reader*.
>**TCP_SBF_Reader**(*src, msgnum*)  
*src*: The address and port to open a TCP server on. Indicate in the following format: "address:port"   
*msgnum*: Optional. Used to specify the default number of messages to read at once. If not set, the default is to read all available messages.

>*TCP_SBF_Reader*.**read**(*src, converter, output, mode, x, compact, HRclk, lowerUDI, verbose*)  
On default, reads x messages from a TCP stream as indicated on initialization. Can be modified using optional parameters.  
*src*: Optional. Used if the source to read from should differ from the one indicated in advance.
*converter*: Optional. If passed an instance of type *SSR_Converter*, can convert decoded messages.  
*output*: Optional. If passed an instance of *TCP_Server* or *File_Writer*, outputs converted messages to the channel indicated.  
*mode*: Optional. Used to indicate the mode of operation: [m:message numbers, t:time limit].  
*x*: Optional. Used to indicate the number of messages to read.  
*compact*: Optional. Truth value whether to prefer combined (Orb+Clk) over individual messages. Default:True.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Verbose level for the process.

### SSR_Converter
Basic converter for HAS messages, used to construct IGS and RTCM3 messages from decoded HAS messages. Please note that while a mode {1:IGS, 2:RTCM3} can be set at either point in the process, it *has* to be set at some point.

>**SSR_Converter**(*mode, compact, pppWiz, verbose*)  
*mode*: Optional. Used to set a default mode for the converter. Options are {1:IGS, 2:RTCM3}.  
*compact*: Optional. Used to set a default setting to prefer compact (Clk+Orbits) or individual messages.  
*pppWiz*: Optional. Used to indicate the output to be in PPP Wizard format (only in combination with the \**_Reader* classes).  
*verbose*: Optional. Set the default verbose level for this instance.

>*SSR_Converter*.**convertMessage**(*msg, mode, compact, HRclk, tow, lowerUDI, verbose*)  
Bundling all subfunctions of the class for simple conversion of a HAS message into one of the two possible formats.  
*msg*: The HAS message to convert. Bitstring object.  
*mode*: Optional. The mode for the converter. Options are {1:IGS, 2:RTCM3}.  
*compact*: Optional. Set a preferance for compact (Clk+Orbits) or individual messages.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*tow*: Time of week in seconds.  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Set the verbose level for the process.  
Returns a list of converted messages.

>*SSR_Converter*.**feedMessage**(*msg*)  
Used to input a new HAS message into the buffer and read the information into *SSR* format, but not convert it yet.  
*msg*: The message to read. Bitstring object.

>*SSR_Converter*.**convert**(*mode, compact, HRclk, tow, lowerUDI, verbose*)  
Convert the current message in the buffer into a specified format.  
*mode*: Optional. The mode for the converter. Options are {1:IGS, 2:RTCM3}.  
*compact*: Optional. Set a preferance for compact (Clk+Orbits) or individual messages.  
*HRclk*: Optional. Truth value whether to output full clock correction messages (with zeroed terms) instead of high-rate ones. Default:False  
*tow*: Time of week in seconds.  
*lowerUDI*: Optional. Indicating the use of the lower (or higher) UDI in case of non-aligning UDIs.  
*verbose*: Optional. Set the verbose level for the process.  
Returns a list of converted messages.

### HAS_Storage
A message container used for all HAS messages during the receival phase. Checks received pages on validity and sorts them into the correct *HAS* objects and takes care of decoding complete messages.

>*HAS_Storage*.**feedMessage**(*has_msg, _time, verbose*)  
Stores a page in the right *HAS* object if the received message is a valid HAS page. If a new HAS message was complete, stores the decoded message and corresponding ToW in *lastMessage* and *lastMessage_tow*, respectively.  
*has_msg*: A received HAS message page.  
*_time*: The receival time of the received message.  
*verbose*: Optional. The verbose level for the process.  
Returns *True* if a new HAS message was complete and *False* otherwise.

### HAS
Simple HAS message class, used in the decoding part on a transmission and assembly level. Stores received pages of a single message ID and is able of decoding them once enough messages are received. Please note that while two decoding modes are possible, in the usual usecase, which takes into account the CRC parity, it is advised to use fast matrix multiplication.

>**HAS**(*msg*)  
*msg*: Optional. Can be used to read a first page already together with the information from the header.

>*HAS*.**addPage**(*msg, pid, t, verb*)  
Add a received page to the object. May raise a *Page_Timeout_Error* if a page is received after the timeout (default is 4min).  
*msg*: The received page to add to the buffer. Bitstring object.  
*pid*: Optional. The page ID of the received page. Can also be read from the message.  
*t*: Optional. Can be used to pass on the receival time of the page in order to account for lost messages and timeouts.  
*verb*: Optional. Set the verbose level for the process.  
Returns *True* if enough messages for decoding are available and *False* if not.

>*HAS*.**decode**(*mode, fcr, verbose*)  
Decode the message in the object using the received pages.  
*mode*: Optional. Select a mode for the decoder. Default is *[1:Fast Matrix Multiplication]*. Mode *[0:Reed Solomon Decoder]* may be used when faulty messages are used, but is not advised to use else.  
*fcr*: Optional. The first consecutive root setting used for the reed solomon decoder.  
*verbose*: Optional. The verbose level for the process.  
Returns the decoded message as a bitstring.

>*HAS*.**complete**()  
Used to check whether enough pages are received for decoding.  
Returns *True* or *False*

>*HAS*.**available**()  
Returns the page IDs of received/available pages.

>*HAS*.**missing**()  
Returns the page IDs of unavailable messages.

>*HAS*.**assembleMessage**(*msgs, missing, mode, fcr*)  
Actual decoding of the HAS message, taking into account the outer layer encoding of the message.   
*msgs*: The received pages in a 2D array.  
*missing*: Optional. List of missing pages.  
*mode*: Optional. The mode used for decoding.  
*fcr*: Optional. The first consecutive root setting for the reed solomon decoder.  
Returns the full decoded message in a bytearray.

### SSR Classes
Classes to read and store the information of a decoded HAS message. The classes can be understood as containers for the information coming with a HAS message, where the message can be composed of different combinations of the following 6 contents: *Masks, Orbit Corrections, Full-Set Clock Corrections, Sub-Set Clock Corrections, Code Bias Corrections, Phase Bias Corrections*. The classes themselves normally have little functionality beyond the storing of information. The data are stored with the sign conventions of the HAS format; any necessary conversions are on the responsibility of the output class.

#### **SSR**
Basic container for SSR corrections. Can save a set of IODs along with the other contained SSR information.
>**SSR**()  
Upon construction, an SSR is empty.

>*SSR*.**printData**()  
Print all SSR data.   

#### **Header**
Storing the information of the HAS header.
>**Header**(*msg, i*)  
*msg*: The HAS message to read. Bitstring object.  
*i*: Optional. Can be used as a "carriage" in the passed message.

>*Header*.**readContent**(*msg*)  
Read a 6bit content string and return a dict with corresponding bools.  
*msg*: The 6bit content string from the HAS header.

#### **Mask**
Storing the information of a HAS mask.

>*Mask*.**readData**(*msg, i*)  
Read the mask data from a given message string.  
*msg*: The HAS message bitstring.  
*i*: Optional. Can be used as a "carriage" in the passed message.  
Returns: the updated position of the "carriage" (i).

>*Mask*.**setDNU**(*n, dnu*)  
Set the do-not-use value for a specific satellite in the mask.  
*n*: Indicator to set the nth satellite of the mask.  
*dnu*: Optional. Can be used to set the dnu flag to *True* (default) or *False*.

>*Mask*.**getDNU**(*msg*)  
Retrieve the do-not-use value for a specific satellite in the mask.  
*n*: Indicator to get the nth satellites value.  
Returns do-not-use *True* or *False*.

>*Mask*.**satID**(*n*)  
Get the PRN / Satellite ID of the nth satellite in the mask.   
*n*: Indicator for the nth satellite.  
Returns the PRN (*int*).

>*Mask*.**sigID**(*n*)  
Get the Signal ID of the nth signal in the mask.   
*n*: Indicator for the nth signal.  
Returns the signal ID (*int*).

>*Mask*.**printData**()  
Print mask data.   

#### **Masks**
Container for storing the multiple masks contained in a single HAS message.
>*Masks*.**readData**(*msg, i*)  
*msg*: The HAS message to read. Bitstring object.  
*i*: Optional. Can be used as a "carriage" in the passed message.  
Returns: the updated position of the "carriage" (i).

>*Masks*.**satNums**()  
Returns the number of satellites in the stored masks for each system in ascending system ID order.

>*Masks*.**getSatNum**(*sys, n*)  
Get the PRN / Satellite ID of the nth satellite in the mask of a specific mask.  
*sys*: The system ID of the system in question (according to HAS convention).  
*n*: Specifying the nth satellite.  
Returns a PRN (*int*).

>*Masks*.**getMask**(*sys*)  
Get the HAS mask of a specific system.  
*sys*: The system ID of the system in question (according to HAS convention).  
Returns the *Mask* of the system.

>*Masks*.**printData**()  
Print mask data.   

#### **SatOrbit**
Storing the information of a single satellites orbit correction.
>**SatOrbit**(*system*)  
*system*: The system the satellite is associated with. At launch, only the 2 systems [0:GPS, 2:GAL] are supported.

>*SatOrbit*.**readData**(*msg, i*)  
Reads the bits of a satellite orbit correction into the container.  
*msg*: The bitstring of the decoded HAS message.  
*i*: Used as a carriage to go through the message.  
Returns: the updated position of the "carriage" (i).

>*SatOrbit*.**printData**()  
Print orbit data.  

#### **Orbits**
Container for all satellite orbit corrections within a HAS message.
>**Orbits**(*satNum*)  
*satNum*: The number of satellites in all systems as obtainable from *Masks*.

>*Orbits*.**readData**(*msg, i*)  
Reads the bits of all orbit corrections into the container.  
*msg*: The bitstring of the decoded HAS message.  
*i*: Used as a carriage to go through the message.  
Returns: the updated position of the "carriage" (i).

>*Orbits*.**printData**()  
Print orbit data.  

#### **ClockFull**
Storing the information of clock corrections for all satellites available in *Masks*.
>**ClockFull**(*satNum, masks*)  
*satNum*: The number of satellites in all systems as obtainable from *Masks*.  
*masks*: *Masks* object the message is associated with.

>*ClockFull*.**readData**(*msg, i*)  
Reads the bits of all clock corrections into the container.  
*msg*: The bitstring of the decoded HAS message.  
*i*: Used as a carriage to go through the message.  
Returns: the updated position of the "carriage" (i).

>*ClockFull*.**printData**()  
Print clock data.  

#### **ClockSub**
Storing the information of a single satellites orbit correction.
>**ClockSub**(*satNums, masks*)  
*satNum*: The number of satellites in all systems as obtainable from *Masks*.  
*masks*: *Masks* object the message is associated with.

>*ClockSub*.**readData**(*msg, i*)  
Reads the bits of the available clock corrections (as indicated in the subset masks) into the container.  
*msg*: The bitstring of the decoded HAS message.  
*i*: Used as a carriage to go through the message.  
Returns: the updated position of the "carriage" (i).

>*ClockSub*.**storeIDs**(*mask*)  
Used once to store the satellite IDs associated with the available corrections in the subset.

>*ClockSub*.**printData**()  
Print clock data.  

#### **GNSSBiases**
Storing the information of both code and phase biases available for a single system in the HAS message. Please note: Biases are stored in a dict with the satellite IDs as keys. For code biases, the bias will be a single number, for phase biases a list of the following layout: [bias, discontinuity indicator]
>**GNSSBiases**(*mode, mask*)  
*mode*: The type of bias, available are *{c:code, p:phase}*  
*mask*: The mask associated with the message.

>*GNSSBiases*.**readData**(*msg, i*)  
Reads the bits of the biases of the current GNSS into the container.  
*msg*: The bitstring of the decoded HAS message.  
*i*: Used as a carriage to go through the message.  
Returns: the updated position of the "carriage" (i).

>*GNSSBiases*.**printData**()  
Print Bias data.  

#### **Biases**
Container for all *GNSSBiases* of a HAS message (the number is the same as the number of GNSSs corrections are available for).
>**Biases**(*masks, mode*)  
*mask*: The mask associated with the message.  
*mode*: The type of bias, available are *{c:code, p:phase}*

>*Biases*.**readData**(*msg, i*)  
Reads the bits of all biases of all GNSSs into the container.  
*msg*: The bitstring of the decoded HAS message.  
*i*: Used as a carriage to go through the message.  
Returns: the updated position of the "carriage" (i).

>*Biases*.**printData**()  
Print Bias data. 

### SSR_HAS
Container to store and read all information from a decoded HAS message. Also stores all received HAS message *Masks* along with their associated Mask ID and IOD sets with their associated IOD set ID.
>**SSR_HAS**(*msg, ssr, verb*)  
Constructs and fills the object with the content of the passed HAS message. Sets this instances *.valid* to *True* if the associated mask could be retrieved.  
*msg*: The decoded HAS message as a bitstring.  
*ssr*: Optional. The *SSR* object to use. If not set, creates a new one.  
*verb*: Optional. The verbose level for the process.

>*SSR_HAS*.**retrieveMasks**(*maskID*)  
Tries to access the *Masks* object associated to the Mask ID referred in the HAS header. Saves the corresponding mask in the *SSR* object.  
*maskID*: Optional. The mask ID to retrieve. Uses the one indicated in the header on default.
Returns: The availability of the *Masks* (bool).

### SSR_RTCM
Class responsible for reading a *SSR* object and from it, giving the functionality of constructing RTCM3 messages based on the availability of information.   
Please note: RTCM3 messages sometimes contain information not obtainable from HAS messages, leading to some of the information in the messages being incorrect (in the case of "drift" data and antenna yaw angle/rate) or assumed (in the case of some flags e.g. for phase bias' signal integer indicator).

>**SSR_RTCM**(*ssr*)  
*ssr*: Optional. The *SSR* instance to use.

>*SSR_RTCM*.**ssr1**(*sys, ssr, tow*)  
Constructing a SSR1 message, containing orbit corrections for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single RTCM3 message (usually 1 page).

>*SSR_RTCM*.**ssr2**(*sys, ssr, tow*)  
Constructing a SSR2 message, containing clock corrections for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single RTCM3 message (usually 1 page).

>*SSR_RTCM*.**ssr3**(*sys, ssr, tow*)  
Constructing a SSR3 message, containing code biases for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single RTCM3 message (usually 1 page).

>*SSR_RTCM*.**ssr4**(*sys, ssr, tow*)  
Constructing a SSR4 message, containing combined orbit and clock corrections for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single RTCM3 message (usually 1 page).

>*SSR_RTCM*.**ssrp**(*sys, ssr, tow*)  
Constructing a SSRp message, containing phase biases for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single RTCM3 message (usually 1 page).

>*SSR_RTCM*.**ssr5**(*sys, ssr, tow*)  
SSR5 messages contain URA correction messages. This type of correction is however not contained in HAS messages, raising an *CorrectionNotAvailable* exception.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.

>*SSR_RTCM*.**ssr6**(*sys, ssr, tow*)  
SSR5 messages contain High-Rate clock correction messages. This type of correction is however not contained in HAS messages, raising an *CorrectionNotAvailable* exception.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.

>*SSR_RTCM*.**const_common_header**(*sys, ssr, msgNum, sync, tow*)  
Constructs the common part for all RTCM3 message header.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*msgNum*: The message number of the message the header is for: {1,2,3,4,5,6,p}.  
*sync*: Synchronization flag for the header (Is another page of this message following?).  
*tow*: The time of week at the time of receival.  
Returns: The header as a bitstring.

>*SSR_RTCM*.**block**(*ssr, msgNum*)  
Based on the type of message, return the relevant blocks of the *SSR*.  
*ssr*: The *SSR* object to query.  
*msgNum*: The type of message: {1,2,3,4,5,6,p}.  
Returns: The SSR block (or list of such).

>*SSR_RTCM*.**msgNum**(*msg, sys*)  
Based on the type of message and the system, return the message number in RTCM3 format.  
*msg*: The type of message: {1,2,3,4,5,6,p}.  
*sys*: The GNSS in question: {GPS, GAL}.  
Returns: The message number (int).

>*SSR_RTCM*.**splitPages**(*msg, headerL*)  
Function to split a whole message into smaller pages if necessary.  
*msg*: The full RTCM3 message.  
*headerL*: The bitlength of a single header of this type of message.  
Returns: A list of message pages of the right size.

>*SSR_RTCM*.**frame**(*msg*)  
Frames the complete RTCM3 page (header+message) with the right introductory bits and the CRC.  
*msg*: The message to be framed with a maximum of 1023 bytes.

>*SSR_RTCM*.**calc_tow**(*ssr, tow*)  
Based on a  time of receival and a time-of-hour from the HAS header, calculates the right time-of week in seconds.  
*ssr*: The *SSR* object worked on.  
*tow*: The time of receival in seconds since the beginning of the week.  
Returns: a 20bit representation of the time of week.

>*SSR_RTCM*.**ret_udi**(*ssr_block, lowerUDI*)  
Conversion from HAS validity index to RTCM3 UDI.  
*ssr_block*: The SSR block(s) in question, containing the HAS validity index.  
*lowerUDI*: Optional. In case of non-aligning intervals, choose which RTCM UDI to choose (default: the lower).  
Returns: The UDI index in RTCM3 format (int).

### SSR_IGS
Class responsible for reading a *SSR* object and from it, giving the functionality of constructing IGS messages based on the availability of information.   
Please note: IGS messages sometimes contain information not obtainable from HAS messages, leading to some of the information in the messages being incorrect (in the case of "drift" data and antenna yaw angle/rate) or assumed (in the case of some flags e.g. for phase bias' signal integer indicator).

>*SSR_IGS*.**IGM01**(*sys, ssr, tow*)  
Constructing an IGM01 message, containing orbit corrections for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single IGS message (usually 1 page).

>*SSR_IGS*.**IGM02**(*sys, ssr, tow*)  
Constructing an IGM02 message, containing clock corrections for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single IGS message (usually 1 page).

>*SSR_IGS*.**IGM03**(*sys, ssr, tow*)  
Constructing an IGM03 message, containing combined orbit and clock corrections for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single IGS message (usually 1 page).

>*SSR_IGS*.**IGM04**(*sys, ssr, tow*)  
IGM04 messages contain High-Rate clock correction messages. This type of correction is however not contained in HAS messages, raising an *CorrectionNotAvailable* exception.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.

>*SSR_IGS*.**IGM05**(*sys, ssr, tow*)  
Constructing an IGM05 message, containing code biases for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single IGS message (usually 1 page).

>*SSR_IGS*.**IGM06**(*sys, ssr, tow*)  
Constructing an IGM06 message, containing phase biases for a single system.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.  
Returns: A list of pages of a single IGS message (usually 1 page).

>*SSR_IGS*.**IGM07**(*sys, ssr, tow*)  
IGM07 messages contain URA correction messages. This type of correction is however not contained in HAS messages, raising an *CorrectionNotAvailable* exception.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.

>*SSR_IGS*.**VTEC**(*sys, ssr, tow*)  
VTEC messages contain atmospheric correction messages. This type of correction is however not contained in HAS messages, raising an *CorrectionNotAvailable* exception.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*tow*: The time of week at the time of receival.

>*SSR_IGS*.**const_common_header**(*sys, ssr, msgNum, tow, multMess*)  
Constructs the common part for all IGS message header.  
*sys*: The GNSS in question: {GPS, GAL}.  
*ssr*: The *SSR* to get the information from.  
*msgNum*: The message number of the message the header is for: {1,2,3,4,5,6,7, VTEC}.  
*tow*: The time of week at the time of receival.
*multMess*: Synchronization flag for the header (Is another page of this message following?).  
Returns: The header as a bitstring.

>*SSR_IGS*.**splitPages**(*msg, headerL*)  
Function to split a whole message into smaller pages if necessary.  
*msg*: The full IGS message.  
*headerL*: The bitlength of a single header of this type of message.  
Returns: A list of message pages of the right size.

>*SSR_IGS*.**frame**(*msg*)  
Frames the complete IGS page (header+message) with the right introductory bits and the CRC.  
*msg*: The message to be framed with a maximum of 1023 bytes.

>*SSR_IGS*.**calc_tow**(*ssr, tow*)  
Based on a  time of receival and a time-of-hour from the HAS header, calculates the right time-of week in seconds.  
*ssr*: The *SSR* object worked on.  
*tow*: The time of receival in seconds since the beginning of the week.  
Returns: a 20bit representation of the time of week.

>*SSR_IGS*.**ret_udi**(*ssr_block, lowerUDI*)  
Conversion from HAS validity index to IGS UDI.  
*ssr_block*: The SSR block(s) in question, containing the HAS validity index.  
*lowerUDI*: Optional. In case of non-aligning intervals, choose which RTCM UDI to choose (default: the lower).  
Returns: The UDI index in IGS format (int).

### TCP_Server
Simple TCP server class, used to pass converted messages to a client listening such as PPP Wizard or RTKLIB.
>**TCP_Server**(*addr, port*)  
*addr*: Optional. The address for the server to be established. On default, *localhost* is used.  
*port*: Optional. The port to be used. On default, port 6947 is used.

>*TCP_Server*.**write**(*msg*)  
*msg*: Message to write to the server, byte-like object.

### File_Writer
Simple interface to write data to a file. Parent class of *PPP_Wiz_Writer*.
>**File_Writer**(*path*)  
*path*: Optional. The path to the file to write into. If not set, uses "ssr_messages.out"  

>*File_Writer*.**write**(*msg*)  
Writes into the open file.  
*msg*: The messages to write. Byte-like structure.  

>*File_Writer*.**close**()  
Closes the open file and finishes operation

### PPP_Wiz_Writer
Simple writer class, able to compile data into a file readable by the PPP Wizard.
>**PPP_Wiz_Writer**(*path, epch, mode*)  
*path*: Optional. The path to the file to write into. If not set, uses "ssr_messages.out"  

>*PPP_Wiz_Writer*.**write**(*msg, n, fmt, epch*)  
Writes into the open file.  
*msg*: The messages to write. Byte-like structure.  
*n*: The key of the rover the message should be accounted to by PPP Wizard.  
*fmt*: The RTKLIB format key for the format the message is encoded in.  
*epch*: Optional. The epoch value to use in the file. PPP Wizard does not require a high accuracy, so if none is set, the last known one is used.  
