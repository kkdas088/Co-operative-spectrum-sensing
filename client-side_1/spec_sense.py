#!/usr/bin/env python
#
# Copyright 2005,2007,2011 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# channel detection time is 2 seconds
# squelch threshold is to be kept at 9db
# Mininum power level to -107dBm for wireless signals
# MAC frame can be of 10 ms or  for gsm standard for 4.516ms
# Receiver Sensitivity  = -174+ 10 log(Bandwidth)+Noise Figure+ Req SNR
  

from gnuradio import gr, eng_notation
from gnuradio import blocks
from gnuradio import audio
from gnuradio import filter
from gnuradio import fft
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import math
import struct
import threading
from datetime import datetime
import logging
import time
import subprocess
import sqlite3
import os 
import datetime
from  numconn import conn
import socket
import cPickle as pickle

# logging format 
global sensing_params
sensing_params=[]
logging.basicConfig(level= logging.DEBUG,format = '%(asctime)s (%(threadName) -10s) %(message)s ')
        

class tune(gr.feval_dd):
    """
    This class allows C++ code to callback into python.
    """
    def __init__(self, tb):
        gr.feval_dd.__init__(self)
        self.tb = tb

    def eval(self, ignore):
        """
        This method is called from blocks.bin_statistics_f when it wants
        to change the center frequency.  This method tunes the front
        end to the new center frequency, and returns the new frequency
        as its result.
        """

        try:
            # We use this try block so that if something goes wrong
            # from here down, at least we'll have a prayer of knowing
            # what went wrong.  Without this, you get a very
            # mysterious:
            #
            #   terminate called after throwing an instance of
            #   'Swig::DirectorMethodException' Aborted
            #
            # message on stderr.  Not exactly helpful ;)

           
            new_freq = self.tb.set_next_freq()
            
            # wait until msgq is empty before continuing
            while(self.tb.msgq.full_p()):
                #print "msgq full, holding.."
                time.sleep(0.1)
            
            return new_freq

        except Exception, e:
            print "tune: Exception: ", e


class parse_msg(object):
    def __init__(self, msg):
        self.center_freq = msg.arg1()
        self.vlen = int(msg.arg2())
        assert(msg.length() == self.vlen * gr.sizeof_float)

        # FIXME consider using NumPy array
        t = msg.to_string()
        self.raw_data = t
        self.data = struct.unpack('%df' % (self.vlen,), t)
        

class my_top_block(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self)
       
        usage = "usage: %prog [option] BS min_freq max_freq"
       
        parser = OptionParser(option_class=eng_option, usage=usage)
        parser.add_option("-a", "--args", type="string", default="addr=192.168.30.2",
                          help="UHD device device address args [default=%default]")
        parser.add_option("", "--spec", type="string", default="A:0",
	                  help="Subdevice of UHD device where appropriate")
        parser.add_option("-A", "--antenna", type="string", default="RX2",
                          help="select Rx Antenna where appropriate")
        parser.add_option("-s", "--samp-rate", type="eng_float", default=5e6,
                          help="set sample rate [default=%default]")
        parser.add_option("-g", "--gain", type="eng_float", default=None,
                          help="set gain in dB (default is midpoint)")
        parser.add_option("", "--tune-delay", type="eng_float",
                          default=0.25, metavar="SECS",
                          help="time to delay (in seconds) after changing frequency [default=%default]")
        parser.add_option("", "--dwell-delay", type="eng_float",
                          default=0.25, metavar="SECS",
                          help="time to dwell (in seconds) at a given frequency [default=%default]")
        parser.add_option("-b", "--channel-bandwidth", type="eng_float",
                          default=200e3, metavar="Hz",
                          help="channel bandwidth of fft bins in Hz [default=%default]")
        parser.add_option("-l", "--lo-offset", type="eng_float",
                          default=0, metavar="Hz",
                          help="lo_offset in Hz [default=%default]")
        parser.add_option("-q", "--squelch-threshold", type="eng_float",
                          default=35, metavar="dB",
                          help="squelch threshold in dB [default=%default]")
        parser.add_option("-F", "--fft-size", type="int", default=None,
                          help="specify number of FFT bins [default=samp_rate/channel_bw]")
        parser.add_option("", "--real-time", action="store_true", default=False,
                          help="Attempt to enable real-time scheduling")

        parser.add_option("-t", "--socket", type="int", default=None,
                          help="socket for read and write operation")

        (options, args) = parser.parse_args()
        if len(args) != 2:
            parser.print_help()
            logging.debug("exiting")
            sys.exit(1)

        self.channel_bandwidth = options.channel_bandwidth

        self.min_freq = eng_notation.str_to_num(args[0])
        self.max_freq = eng_notation.str_to_num(args[1])

        self.sd = socket.fromfd(options.socket,socket.AF_INET, socket.SOCK_STREAM)


        
 

        if self.min_freq > self.max_freq:
            # swap them
            self.min_freq, self.max_freq = self.max_freq, self.min_freq

        if not options.real_time:
            realtime = False
        else:
            # Attempt to enable realtime scheduling
            r = gr.enable_realtime_scheduling()
            if r == gr.RT_OK:
                realtime = True
            else:
                realtime = False
                print "Note: failed to enable realtime scheduling"

        # build graph
        d = uhd.find_devices(uhd.device_addr(options.args))
     
        self.address = options.args
        
        self.u = uhd.usrp_source(device_addr=options.args,
                                 stream_args=uhd.stream_args('fc32'))

        # Set the subdevice spec
        if(options.spec):
            self.u.set_subdev_spec(options.spec, 0)

        # Set the antenna
        if(options.antenna):
            self.u.set_antenna(options.antenna, 0)
        
        self.u.set_samp_rate(options.samp_rate)
        self.usrp_rate = usrp_rate = self.u.get_samp_rate()
        print 'options samp rate',self.usrp_rate
        
        self.lo_offset = options.lo_offset

        if options.fft_size is None:
            self.fft_size = int(self.usrp_rate/self.channel_bandwidth)
        else:
            self.fft_size = options.fft_size
        
        self.squelch_threshold = options.squelch_threshold
        
        s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_size)
        

        mywindow = filter.window.blackmanharris(self.fft_size)
        #print mywindow
        ffter = fft.fft_vcc(self.fft_size, True, mywindow, True)
        #print ffter
        power = 0
        for tap in mywindow:
            power += tap*tap

        c2mag = blocks.complex_to_mag_squared(self.fft_size)

        # FIXME the log10 primitive is dog slow
        #log = blocks.nlog10_ff(10, self.fft_size,
        #                       -20*math.log10(self.fft_size)-10*math.log10(power/self.fft_size))

        # Set the freq_step to 75% of the actual data throughput.
        # This allows us to discard the bins on both ends of the spectrum.

        self.freq_step = self.nearest_freq((0.75 * self.usrp_rate), self.channel_bandwidth)
        print "freq step" ,self.freq_step
        self.min_center_freq = self.min_freq + (self.freq_step/2) 
        print " min center freq" ,self.min_center_freq
        nsteps = math.ceil((self.max_freq - self.min_freq) / self.freq_step)
        self.nsteps = nsteps
        print "n steps", nsteps
        self.max_center_freq = self.min_center_freq + (nsteps * self.freq_step)

        self.next_freq = self.min_center_freq

        tune_delay  = max(0, int(round(options.tune_delay * usrp_rate / self.fft_size)))  # in fft_frames
        print "tune delay in frames " , tune_delay
        dwell_delay = max(1, int(round(options.dwell_delay * usrp_rate / self.fft_size))) # in fft_frames

        self.msgq = gr.msg_queue(1)
        print"message queue", self.msgq
        self._tune_callback = tune(self)        # hang on to this to keep it from being GC'd
        stats = blocks.bin_statistics_f(self.fft_size, self.msgq,
                                        self._tune_callback, tune_delay,
                                        dwell_delay)

        # FIXME leave out the log10 until we speed it up
	#self.connect(self.u, s2v, ffter, c2mag, log, stats)
	self.connect(self.u, s2v, ffter, c2mag, stats)

        if options.gain is None:
            # if no gain was specified, use the mid-point in dB
            g = self.u.get_gain_range()
            options.gain = float(g.start()+g.stop())/2.0

        self.set_gain(options.gain)
        print "gain =", options.gain

    def set_next_freq(self):
        target_freq = self.next_freq
        self.next_freq = self.next_freq + self.freq_step
        if self.next_freq >= self.max_center_freq:
            self.next_freq = self.min_center_freq

        if not self.set_freq(target_freq):
            print "Failed to set frequency to", target_freq
            sys.exit(1)

        return target_freq


    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        Args:
            target_freq: frequency in Hz
        @rypte: bool
        """
        
        r = self.u.set_center_freq(uhd.tune_request(target_freq, rf_freq=(target_freq + self.lo_offset),rf_freq_policy=uhd.tune_request.POLICY_MANUAL))
        if r:
            return True

        return False

    def set_gain(self, gain):
        self.u.set_gain(gain)
    
    def nearest_freq(self, freq, channel_bandwidth):
        freq = round(freq / channel_bandwidth, 0) * channel_bandwidth
        return freq

def main_loop(tb):
    global sensing_params
    isolationlevels= 'IMMEDIATE'
    logging.debug("entered Main looop")
    db_filename ='spec.db'
    schema_filename = 'spectable.sql'
   
    def bin_freq(i_bin, center_freq):
        #hz_per_bin = tb.usrp_rate / tb.fft_size
        freq = center_freq - (tb.usrp_rate / 2) + (tb.channel_bandwidth * i_bin)
        #print "freq original:",freq
        #freq = nearest_freq(freq, tb.channel_bandwidth)
        #print "freq rounded:",freq
        return freq
    
    bin_start = int(tb.fft_size * ((1 - 0.75) / 2))
    bin_stop = int(tb.fft_size - bin_start)
    #noise_floor_dbm = -174+10*math.log10(tb.usrp_rate)+5
    noise_floor_dbm = -174+10*math.log10(tb.channel_bandwidth)+5
    #print "noise floor is %d" %noise_floor_dbm
    db_is_new = not os.path.exists(db_filename)
    
    with sqlite3.connect(db_filename,isolation_level = isolationlevels) as conn:
		
        if db_is_new:
            print 'creating schema for sensing'
    
            with open(schema_filename,'rt') as f:
                schema = f.read()
        
            conn.executescript(schema)
            
         
        conn.row_factory = sqlite3.Row
        cursor= conn.cursor()
        cursor.execute("select count(stfreq) from spec1")
        
       
        
        
        for row in cursor.fetchmany(1):
            if row[0]>0:
                print"updating"
            else:
                print"inserting"
                       
        nsteps=tb.nsteps
        
        while (nsteps>0):
            # Get the next message sent from the C++ code (blocking call).
            # It contains the center frequency and the mag squared of the fft
            m = parse_msg(tb.msgq.delete_head())

            # m.center_freq is the center frequency at the time of capture
            # m.data are the mag_squared of the fft output
            # m.raw_data is a string that contains the binary floats.
            # You could write this as binary to a file.
            
            queryinsert="""insert into spec1(stfreq,enfreq,ctfreq,pwdbm,addr,time) values(?,?,?,?,?,?)"""
            queryupdate ="""update spec1 set pwdbm=?,time=? where stfreq=? and addr=?"""
  
            print "center frequency" ,m.center_freq
            for i_bin in range(bin_start, bin_stop):
                        
                center_freq = m.center_freq
                freq = bin_freq(i_bin, center_freq)
                power_dbm = 10*math.log10(m.data[i_bin]/tb.usrp_rate) 
                stfreq=freq
                enfreq=freq+tb.channel_bandwidth
                seltxt='No'
                ctfreq= (stfreq+enfreq)/2
                #power_dbm = 10*math.log10(m.data[i_bin]/(tb.channel_bandwidth*tb.fft_size))
                #power_dbm = 10*math.log10(m.data[i_bin]/(0.001*tb.channel_bandwidth*tb.fft_size))
                '''print "Noise_floor = ", noise_floor_dbm
                print "m.data[i_bin] = ", m.data[i_bin]
                print "usrp_rate - ",tb.usrp_rate'''
                #power_dbm = -10*math.log10(m.data[i_bin]/0.001*tb.usrp_rate)
                #power_dbm_W_USRP = 10*math.log10((m.data[i_bin]*tb.channel_bandwidth)/(0.001*tb.usrp_rate))
                #print "power_dbm = ", power_dbm
                pwdbm = power_dbm
                a = power_dbm - noise_floor_dbm
               # print "Power - Noise = ", a
               
                
               
                                                           
                if (row[0]>0):
                    right_now = datetime.datetime.now()    
                    #conn.execute(queryupdate,(pwdbm,right_now,stfreq,tb.address))
                    sensing_params.append(pwdbm);sensing_params.append(right_now);sensing_params.append(stfreq);sensing_params.append(tb.address);sparams = pickle.dumps(sensing_params)
                    tb.sd.send("c1"+"old"+sparams)
                else:
                    right_now = datetime.datetime.now()    
                    #conn.execute(queryinsert,(stfreq,enfreq,ctfreq,pwdbm,tb.address,right_now))
                    sensing_params.append(pwdbm);sensing_params.append(right_now);sensing_params.append(stfreq);sensing_params.append(tb.address);sensing_params.append(enfreq);sensing_params.append(ctfreq);sparams = pickle.dumps(sensing_params) 
                    tb.sd.send("c1"+"new"+sparams)
            
               
            sensing_params=[]
                    
                 
            nsteps -=1
        
        
            
                                                        
class Main_Data(object):

    def Inf_run(self):
        tb = my_top_block()
        tb.start()
        while True:
 
            main_loop(tb)
            
if __name__ == '__main__':
    print " The spectrum Detection  will be running for 2ms as per IEEE 802.22 standard and then data (MAC Frame)  will be sent for 10ms  in the band found as per the detection"
    
    try:
        Main_Data().Inf_run()
          
    except KeyboardInterrupt:
        #command ="rm spec.db"
        logging.debug("after interrupt")
        #subprocess.call(command,shell=True)

        
        
        
    
    

    
