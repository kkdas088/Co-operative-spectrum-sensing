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
import threading 
import socket
import select
import Queue

global numconn,e
numconn = conn()
e=threading.Event()   

class server_open_port(object):
    
    def __init__(self):
        print "port opening intiated"
        self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)  
        self.server.setblocking(0)  
        self.server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        #self.server_address = ('130.233.158.159',16000)
        self.server_address = ('localhost',16000)
        print ' Port opened up on %s port %s' %self.server_address
        self.server.bind(self.server_address)
        self.server.listen(10)



    def chk_conn(self):
        while numconn.aconn!=numconn.conn:
            print "False"
        else:
            e.set()
            print "True"
           



def main():

   
    parser = OptionParser(option_class=eng_option, conflict_handler="resolve")
    parser.add_option("-n", "--conn", type="int", default=2,
                      help="set number of connections [default=%default]")

    (options,args) = parser.parse_args()

    numconn.conn = options.conn 
    numconn.aconn = +1
    
   
    inputs = []
    outputs =[]
    
   
    message_queues = {}

    op = server_open_port();inputs.append(op.server)
    while True:
        # Wait for at least one of the sockets to be ready for processing
        #print >>sys.stderr, 'Basestation control module is open and ready to recieve and transmit messages'
        readable, writeable, exceptional = select.select(inputs,outputs,inputs)
     
        for s in readable:
            if s is op.server:
                # A "readable" socket is ready to accept a connection
                connection, client_address = s.accept()
                print >>sys.stderr, 'connection from', client_address
                connection.setblocking(0)
                inputs.append(connection)
                # Give the connection a queue for data we want to send
                message_queues[connection] = Queue.Queue()
                numconn.aconn=+1

            
            else:
                data = s.recv(1024)
                if data:
                    # A readable client socket has data
                    #print >>sys.stderr, 'received "%s" from %s' % (data, s.getpeername())
                    message_queues[s].put(data)
                    # Add output channel for response
                    if s not in outputs:
                        outputs.append(s)

                else:
                    # Interpret empty result as closed connection
                    print >>sys.stderr, 'closing', client_address
                    # Stop listening for input on the connection
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    s.close()
                    # Remove message queue
                    del message_queues[s]



        for s in writeable:
            try:
                e.wait(0.001)
                
                next_msg = message_queues[s].get_nowait()
            except Queue.Empty:
                # No messages waiting so stop checking for writability.
                print >>sys.stderr, ' ', s.getpeername(), 'queue empty'
                outputs.remove(s)
            else:
                print "length of next_message",len(next_msg)
                first_msg= "The server would reply shortly\n"
                s.send(first_msg)
                #next_msg=op.intiate_instructions(next_msg)
                
                
                else:
                    next_msg= "sense"
                    print "next_msg",next_msg
                    print >>sys.stderr, 'sending "%s" to %s' % (next_msg, s.getpeername())
                    s.send(next_msg)
                    e.clear()
 
  
        # Handle "exceptional conditions"
        for s in exceptional:
            print >>sys.stderr, 'exception condition on', s.getpeername()
            # Stop listening for input on the connection
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()
            # Remove message queue
            del message_queues[s]
    print "Basic boot up done"

if __name__ == '__main__':   
        
    print " The intial  parameters which are to be set on Base stations are given below "
    print "        ----------------------------------------------------------------------  "
    
    main()
