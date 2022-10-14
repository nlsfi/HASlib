#!/usr/bin/env python

'''
Simple TCP server class

VER   DATE        AUTHOR
1.0   09/12/2021  Oliver Horst / FGI
'''

import socket

class TCP_Server:
    server_address = 'localhost'
    port = 6947
    server = None
    alive = False
    def __init__(self, addr=None, port=None, init=True):
        if addr != None:
            self.server_address = addr
        if port != None:
            self.port = port
        if init:
            self.initServer()

    def initServer(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.server_address, self.port))
        self.server.listen(5)
        print("Waiting for connection on " + str(self.server_address) + ":" + str(self.port))
        (self.client, self.address) = self.server.accept()
        print("Connection established")
        self.alive = True

    def close(self):
        self.server.close()
        self.alive = False

    def write(self, msg):
        try:
            self.client.send(msg)
        except BrokenPipeError:
            self.initServer()
            self.client.send(msg)

    def read(self, n, timeout=0):
        try:
            if timeout != 0:
                self.client.settimeout(timeout)
            data = self.client.recv(n)
        except BrokenPipeError:
            self.initServer()
            data = self.client.recv(n)
        except socket.timeout:
            return -1
        return data
