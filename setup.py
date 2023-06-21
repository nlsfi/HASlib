from setuptools import find_packages, setup

setup(
    name='galileo_has_decoder',
    packages=find_packages(include=['galileo_has_decoder']),
    package_data={'galileo_has_decoder': ['resources/*.txt']},
    version='1.0.2',
    description='A library to decode Galileo HAS messages and convert the data into IGS or RTCM3 messages. Supported input types are: SBF & BINEX via files, TCP clients and Serial ports. The output can be written to a TCP server or a file according to user requirements',
    author='Oliver Horst / FGI',
    license_files = ('Licence.txt','Notice.txt'),
    install_requires=['numpy', 'reedsolo', 'galois', 'serial'],
)
