#!/usr/bin/env python

from gnuradio import gr, digital  
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser
from numconn import conn
from sensingparams import sparams

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
import pprint
import datetime
import json

global numconn,BUFF,usrp_address,conn,isolationlevels,db_filename,schema_filename,addr,times,fobj
numconn = conn() ;times=0
BUFF=4096;usrp_address=['addr=192.168.30.2', 'addr=192.168.20.2']
isolationlevels= 'IMMEDIATE'; db_filename ='sense.db';schema_filename = 'sensetable.sql'

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


    def setupdb(self):
        global conn,isolationlevels,db_filename,schema_filename
        
        db_is_new = not os.path.exists(db_filename)
    
        with sqlite3.connect(db_filename,isolation_level = isolationlevels) as conn:
		
            if db_is_new:
                print 'creating schema for sensing'
    
                with open(schema_filename,'rt') as f:
                    schema = f.read()
        
                conn.executescript(schema)

            else:
                print'Not reqd'

    def updatedb(self,data,clientsock):
        global conn,isolationlevels,db_filename,schema_filename,addr
        with sqlite3.connect(db_filename,isolation_level = isolationlevels) as conn:
            queryinsert ="""insert into sense(usrp,stfreq,tloc,tserv,pwr) values(?,?,?,?,?)"""
            queryupdate ="""update sense set tloc=?,tserv=?,pwr=? where stfreq=? and usrp=?"""
            
            segmnt= data.pop()
            
            if segmnt=='c1new':

                params = data
                params.pop();params.pop();Address= params.pop();stfreq= params.pop();timelocal= params.pop();power_dbm= params.pop();time_server = datetime.datetime.now() 
                conn.execute(queryinsert,(Address,stfreq,timelocal,time_server,power_dbm))
                print 'Sensing data for client 1 start freq %d inserted\n'%(stfreq)
                
                
            elif segmnt=='c1old':
               
               
                params = data;time_server = datetime.datetime.now() 
                Address= params.pop();stfreq= params.pop();timelocal= params.pop();power_dbm= params.pop();               
                conn.execute(queryupdate,(timelocal,time_server,power_dbm,stfreq,Address))
                print 'Sensing data for client 1 start freq %d updated\n'%(stfreq)


            elif segmnt=='c2new':
                params = data
                params.pop();params.pop();Address= params.pop();stfreq= params.pop();timelocal= params.pop();power_dbm= params.pop();time_server = datetime.datetime.now() 
                conn.execute(queryinsert,(Address,stfreq,timelocal,time_server,power_dbm))
                print 'Sensing data for client 2 start freq %d inserted\n'%(stfreq)  
      
            elif segmnt=='c2old':
                params = data;time_server = datetime.datetime.now()  
                Address= params.pop();stfreq= params.pop();timelocal= params.pop();power_dbm= params.pop()
                conn.execute(queryupdate,(timelocal,time_server,power_dbm,stfreq,Address))
                print 'Sensing data for client 2 start freq %d updated\n'%(stfreq)

           
                 
            else:
                print repr(addr) + ' recv:'+ repr(data[:5])

     

    def response(self,key):
        return 'Server response: ' + 'Wait'

    def handler(self,clientsock,addr):
        global numconn,usrp_address, conn,isolationlevels,db_filename,schema_filename,times,fobj
        
   
        while 1:
            data = clientsock.recv(BUFF)
            if not data: break
            if data[:4]=="Boot":
                print repr(addr) + ' recv:' + repr(data)
                print 'Number of actual connections',numconn.aconn;
                numconn.addr=usrp_address[numconn.aconn-1]
                para_string=pickle.dumps(numconn);clientsock.send(para_string);print repr(addr) + ' sent:' + repr('params')
                checker = bool(numconn.aconn is not numconn.conn);print checker
                while numconn.aconn!=numconn.conn:
                    time.sleep(0.00001)   
                else:
                    clientsock.send('sense')
                    print repr(addr) + ' sent:' + repr('sense')
                    
            
               
                if "close" == data.rstrip(): break # type 'close' on client console to close connection from the server side


            elif data[:4]=="Data":
                actual_data=data[4:];times+=1
                if times==1:
                    fobj = open("somedata", 'wb')
                #print 'Actual data length',len(actual_data)
                fobj.write(actual_data)
                #print 'Creating data file part-%d'%times


            elif data[:4]=="Done":
                print 'File creation complete'
                fobj.close();times=0
                try:
                    f = open('somedata', 'rb');data=pickle.load(f)
                    self.updatedb(data,clientsock)
                except:
                    print '**************************************Not able to insert record**********************************************************************************'


            else:
                print 'Irrelevant\n'
                
                
                
        clientsock.close();numconn.aconn-=1
        print addr, "- closed connection" #log on console

def main():
    global tnum,numconn,aconn,addr,fobj
   
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
 

    op = server_open_port();op.setupdb()
   
    while 1:
        print 'waiting for connection...'
        clientsock, addr = op.server.accept()
        print '...connected from:', addr;numconn.aconn+=1;print 'actual connections',numconn.aconn
        t=threading.Thread(target=op.handler,args=(clientsock,addr))
        t.setDaemon(True)
        t.start()

if __name__=='__main__':
    main()

