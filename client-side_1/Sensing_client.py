#!/usr/bin/python
import numpy as np
import time
import socket 
import sys
import threading
import select
import string
import subprocess
import os
import cPickle as pickle
import pprint

class open_port(object):
    
    def __init__(self):
        print "port opening intiated\n"
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.setblocking(1)
        self.server_address = ('130.233.158.159',16000)
        #self.server_address = ('localhost',16000)
        print  'connecting to %s port %s\n' % self.server_address
        self.sock.connect(self.server_address)
        self.data="";self.paramslist=[]
        
 
    def prompt(self):
        sys.stdout.write('<You> ')
        sys.stdout.flush()


    def intiate_sensing(self):
        print "intiating client  module"
        params = pickle.loads(self.paramslist.pop());print "After de serialization, USRP address", params.addr
        subprocess.call(" python spec_sense.py  %r  %r --args %s --samp-rate %d --gain %d --socket %d"%(params.minfreq,params.maxfreq,params.addr,params.samprate,params.gain,self.sock.fileno()), shell=True)
        print "\n ***********************Sensing performed according to data but transmission not done %s******************************\n"%(self.data)
        return


def main():

    op= open_port()
    sys.stdout.write('\n<You> ')
    print "Sending ready for sensing to the server\n"
    op.sock.send("Boot Ready")
  
    try:
        while 1:
            socket_list = [sys.stdin, op.sock]
         
            # Get the list sockets which are readable

            read_sockets, write_sockets, error_sockets = select.select(socket_list , [], [])
        
            for sock in read_sockets:
                #incoming message from remote server
                if sock == op.sock:
                    op.data = sock.recv(4096)
                    if not op.data :
                        print '\nDisconnected from chat server'
                        sys.exit()
                    else :
                        #print data
                        sys.stdout.write('\n<Them> ')
                        if 'sense' in op.data:
                            sys.stdout.write('sense\n')
                            op.intiate_sensing()
                        
                        else:
                            sys.stdout.write('Other than sensing\n');op.paramslist.append(op.data)
                        sys.stdout.write('\n')    
                        op.prompt()
             
                #user entered a message
                else :
                    msg = sys.stdin.readline()
                    op.sock.send(msg)
                    op.prompt()

    finally:
        op.sock.close()
    

if __name__ =="__main__":
    print "  Open for instructions from server\n"
    main()
