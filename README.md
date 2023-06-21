# HASlib

The Galileo HAS Decoder library is a repository for Python 3, capable of decoding raw Galileo C/Nav pages received by an E6 capable signal receiver. Messages can both be read live via a serial port or TCP or pre-recorded from a file.  
Messages are collected and, as possible, decoded into Galileo High Accuracy Service (HAS) messages, containing Precise Point Positioning (PPP) corrections for navigation messages from both the GPS and the Galileo constellations.  
Additionally, messages can be converted into RTCM3 SSR or IGS SSR messages. Converted messages can be directly passed on via a TCP server or locally saved as a file. For the latter, a possible output mode is a special PPP Wizard-conform format, which can directly be processed by the processing module of it. 

# Version 1.0.2 UPDATE
Bugfix: The sign convention differences between HAS and the supported output formats (i.e., RTCM-SSR and IGS-SSR) are now properly taken into account. The documentation has been updated to specify that the SSR classes store the information in the HAS sign convention, and any conversions are on the responsibility of the output class.

# Version 1.0.1 UPDATE!
Several additions and bugfixes submitted 23.02.2023, including bugfix for handling redundant HAS pages and enabling HAS operational mode. Please update your local repository to the newest version. 

## Requirements
The Python version used for the library is v3.9.6.  
Please see [Notice.txt](Notice.txt) for required dependencies.

## Installation
Download or clone the repository and use the following commands to install the library as Python wheel. 

    cd HASlib-main
    python setup.py bdist_wheel
    pip install dist/galileo_has_decoder-1.0.2-py3-none-any.whl
  

## Usage
The Galileo HAS Decoder can easily be used as a library to include it (or parts of it) in code. However, if only a low level of adaptation is required, one can also use the _HAS\_Converter.py_ file for a simple command-line usage.

### Library
The basic usage of the library is relatively straightforward. Most of the use cases will only make use of the central `galileo_has_decoder.conv.HAS_Converter` class. With it, it is possible to read data, convert decoded HAS messages and output these in one of the two options mentioned earlier.  
After installation, you are able to import and use it as follows:

```
>> import galileo_has_decoder.conv as gal_conv
>> converter = gal_conv.HAS_Converter(source="data.sbf", target="log.out", out_format=2)
>> converter.convertX(3000)
```
This code reads pre-recorded data from the file *data.sbf* and saves converted HAS messages to the log-file *log.out*. HAS messages encountered are converted into the RTCM3 SSR format (mode *2*). Using the `.convertX(3000)` function, 3000 messages from the file indicated are read and encountering HAS messages are converted & output as indicated on initialization.  
Parameters for the `HAS_Converter` are as follows:  
* `source`: The source. Can be a filename/path or portname.  
* `target`: The output target. Can be a filename/path or an IP address for a TCP server.  
* `out_format`: The format of the output. Options are [1:IGS, 2:RTCM3]  
* `modeIn`: Optional. Determining the mode of input. If not set, looks for file endings.  Options are [1:SBF File, 2:BINEX File, 3:SBF Serial, 4:BINEX Serial, 5:SBF TCP, 6:BINEX TCP]  
* `modeOut`: Optional. Determining the mode of output. If not set, decides based on all-numeric IP addresses (excl. dots)/localhost or not. Options are: [1:TCP, 2:File, 3:PPPWiz File, 4:PPPWiz Stream]  
* `x`: Optional parameter. Used to indicate a maximum number of navigation messages to read. This includes all GNSS messages and is not limited to Galileo HAS messages.  
* `port`: Optional parameter for TCP output. If not set, uses port 6947  
* `baudrate`: Optional parameter for serial input. If not set, uses 115200  
* `skip`: Optional for file input. Used to skip an initial portion of the file.  
* `mute`: Optional. Pass _True_ or _1_ to suppress verbose-independent messages.

While most parameters are optional and may be skipped, it is generally encouraged to set all parameters to avoid confusing or unwanted behaviour.

When an instance of `HAS_Converter` is created, it is possible to use the two functions `.convertAll()` or `.convertX(x)` to read all messages available from the source or just a specific amount of messages.  
Please note that these messages do not all have to be C/Nav messages or even valid ones, thus it may happen that a set of messages does not contain many, or even any, valid HAS messages. After each function call, a summary of the process is printed to the console. For more information on intermediate steps, you may use the `verbose` parameter on either of the `.convert` functions.

### CLI Usage
For a simple interfacing via the command line, the _HAS\_Converter.py_ file can be used. Most parameters can be set with this, which takes care of the aforementioned steps. The command is used as shown below:  
```
> python3 HAS_Converter.py -s data.sbf -f RTCM -t log.out -x 3000  
```
This command sets up a decoder with exactly the same settings as shown in the previous library case. The correct usage is shown below, together with the available options.
```
>> python3 HAS_Converter.py -s SOURCE -t TARGET -f OUTFORMAT [...options...]
```
* -s arg    : Source stream to decode messages from  
* -t arg : Target stream to decode messages to  
* -f opt : Format to convert HAS messages to. Options are [1:IGS, 2:RTCM3]  
* -i opt : Input mode, specifying the type of input stream. Options are : [1:SBF File, 2:BINEX File, 3:SBF Serial, 4:BINEX Serial, 5:SBF TCP, 6:BINEX TCP]  
* -o opt : Output mode, specifying the type of output stream. Options are: [1:TCP, 2:File, 3:PPPWiz File, 4:PPPWiz Stream]  
* -p arg : Optional for TCP output. If not set, uses port 6947  
* -b arg : Optional for serial input, specifying the baudrate of the stream. If not set, uses 115200  
* -v arg : Optional, specifying the verbose level for the process  
* -m     : Optional, used to mute verbose-independent messages  
* -h     : Displaying this help message    
* --skip arg      : Optional, used to skip some initial portion of a read file.  
* --mute          : Optional, used to mute verbose-independent messages  

### Advanced Usage
Most parts of the library can also be used independently for special use cases. For further information on classes and functions please refer to the documentation.

## Tests

Tests-folder includes Zip-file comprising of two SBF-files recorded in FGI offices in Otaniemi, Espoo, Finland. Unzip the files and test decoding, for example, via the HAS_converter.py:
```
> python3 HAS_Converter.py -s ./Tests/galileo_ssr000.sbf -f RTCM -t log.out -x 3000  
```
Specifications for the test recordings can be found in [ReadMe.md](Tests/ReadMe.md)

## License

Please see [Licence.txt](Licence.txt).
This software can decode the HAS SiS ICD. If the HAS SiS ICD is used, the terms and conditions set in the HAS SiS ICD apply. Please see the [ICD](https://www.gsc-europa.eu/sites/default/files/sites/all/files/Galileo_HAS_SIS_ICD_v1.0.pdf) for further details.

## Acknowledgement

This work was conducted under the project Precise and Authentic User Location Analysis (PAULA), funded by the European Commission DG-DEFIS under contract DEFIS/2020/OP/0002.

We wish to acknowledge JRC for their significant help for addressing and fixing HASlib software issues and furthermore, testing the library!

## Further information

This library is further documented in a [paper](galileo_has.pdf) published in proceedings of the [ION-GNSS+ 2022 conference](https://www.ion.org/gnss/abstracts.cfm?paperID=11477) as well as in a [Master's thesis]( https://aaltodoc.aalto.fi/handle/123456789/112893).
If you wish to refer to this work in your publication, please cite the ION-GNSS paper.

## Disclaimer

HASlib has not been developed or tested operationally. HASlib users use it at their own risk, without any guarantee or liability from the code authors or the Galileo HAS signal provider.
