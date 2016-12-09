#!/usr/bin/env python

from gnuradio import gr, digital  
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser
from numconn import *

import os, sys
import random, time, struct
import socket # for networking
import threading # to handle events
import subprocess # to execute commands as if in the terminal
import sqlite3 #database
import random
import inspect 
import traceback
import socket
import select
import Queue
import cPickle as pickle

global numconn,e,BUFF
numconn = conn() 
e=threading.Event() 
BUFF=4096

class server_open_port(object):
    
    def __init__(self):
        print "port opening intiated"
        self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)  
        #self.server.setblocking(0)  
        self.server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        self.server_address = ('130.233.158.159',16000)
        print ' Port opened up on %s port %s' %self.server_address
        self.server.bind(self.server_address)
        self.server.listen(10)



    def response(self,key):
        return 'Server response: ' + 'Wait'

    def handler(self,clientsock,addr):
        while 1:
            data = clientsock.recv(BUFF)
            if not data: break
            print repr(addr) + ' recv:' + repr(data)
            print 'Number of actual connections',numconn.aconn
            checker = bool(numconn.aconn is not numconn.conn);print checker
            while numconn.aconn!=numconn.conn:
                time.sleep(0.1)   
            else:
                para_string=pickle.dumps(numconn)
                clientsock.send('sense'+','+para_string)
                print repr(addr) + ' sent:' + repr('sense + params')
               
            if "close" == data.rstrip(): break # type 'close' on client console to close connection from the server side

        clientsock.close();numconn.aconn-=1
        print addr, "- closed connection" #log on console

def main():
    global tnum,numconn,aconn
    parser = OptionParser(option_class=eng_option, conflict_handler="resolve")
    parser.add_option("-n", "--conn", type="int", default=2,
                      help="set number of connections [default=%default]")

    parser.add_option("-x", "--minfreq", type="int", default=590e6,
                      help="set number of connections [default=%default]")

    parser.add_option("-y", "--maxfreq", type="int", default=600e6,
                      help="set number of connections [default=%default]")

    parser.add_option("-s", "--samprate", type="eng_float", default=5e6,
                          help="set sample rate [default=%default]")

    parser.add_option("-g", "--gain", type="eng_float", default=19,
                          help="set gain in dB (default is midpoint)")


    parser.add_option("-b", "--channelbandwidth", type="eng_float",
                          default=200e3, metavar="Hz",
                          help="channel bandwidth of fft bins in Hz [default=%default]")

    (options,args) = parser.parse_args()

    numconn.conn = options.conn;numconn.minfreq=options.minfreq;numconn.maxfreq=options.maxfreq;numconn.samprate=options.samprate;numconn.gain=options.gain 
    numconn.chbw=options.channelbandwidth
 

    op = server_open_port()
   
    while 1:
        print 'waiting for connection...'
        clientsock, addr = op.server.accept()
        print '...connected from:', addr;numconn.aconn+=1;print 'actual connections',numconn.aconn
        t=threading.Thread(target=op.handler,args=(clientsock,addr))
        t.setDaemon(True)
        t.start()

if __name__=='__main__':
    main()
