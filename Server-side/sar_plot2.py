#!/usr/bin/env python

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sqlite3
import os 
import time


class MainData(object):

    def __init__(self):
        self.db_filename ='sense2.db'
        self.plt = self.setup_backend();
        self.fig = self.plt.figure(figsize=(10,5))
        win = self.fig.canvas.manager.window
        no_issue_for_db= self.checkfordb()
        while no_issue_for_db:
            win.after(1, self.animate())
            self.plt.ion()
            self.plt.show()
            while True:
                win.after(1, self.animate())


    def checkfordb(self):
         db_is_new = not os.path.exists(self.db_filename)
         while  db_is_new:
             time.sleep(0.0001)

         else:
             time.sleep(2)
             with sqlite3.connect(self.db_filename) as conn:
                   conn.row_factory = sqlite3.Row
                   cursor= conn.cursor()
                   while 1:
                       cursor.execute("select count(stfreq) from sense2")
                       for row in cursor.fetchmany(1):
                           if row[0]>35:
                               print"eligible for Visualization";return True
                           else:
                               time.sleep(1)
                    
             
             
         
            
        
    def setup_backend(self,backend='TkAgg'):
        import sys
        del sys.modules['matplotlib.backends']
        del sys.modules['matplotlib.pyplot']
        import matplotlib as mpl
        mpl.use(backend)  # do this before importing pyplot
        import matplotlib.pyplot as plt
        return plt

    
    def animate(self):

        global counter
        if counter == 0:
            with sqlite3.connect(self.db_filename) as conn:
                conn.row_factory = sqlite3.Row
                cursor= conn.cursor()
                cursor.execute("select * from sense2")
                datas= cursor.fetchall()
                self.ctfreq=[]
                self.pwdbm=[]
                for row in datas:
                
                    self.ctfreq.append(row['stfreq']/1e6)
                    self.pwdbm.append(130+row['pwr'])
            
            self.bar_width =0.1
            self.opacity=0.4
            self.error_config = {'ecolor': '1'}
            self.plt.xlim(590,600)
            self.plt.ylim(-130,-90)
            self.rects1 = self.plt.bar(self.ctfreq, self.pwdbm, self.bar_width,bottom=-130,
                     alpha=self.opacity,
                     color='r',
                     
                     label='For USRP 192.168.30.2')
       
            #self.plt.gca().invert_yaxis()  
            self.plt.legend()
            counter +=1
            self.fig.canvas.draw()
            
        else:
            
           
            with sqlite3.connect(self.db_filename) as conn:
                conn.row_factory = sqlite3.Row
                cursor= conn.cursor()
                cursor.execute("select * from sense2")
                datas= cursor.fetchall()
                del self.pwdbm[:]
                del self.ctfreq[:]               
                self.pwdbm=[]
                self.ctfreq=[]
                
                for row in datas:
                
                    self.ctfreq.append(row['stfreq']/1e6)
                    self.pwdbm.append(130+row['pwr'])
                 
            self.plt.clf()
            self.plt.xlabel('Frequency in MHz')
            self.plt.ylabel('Power in dBm')
            self.plt.xlim(590,600)
            self.plt.ylim(-130,-90)
            self.rects1 = self.plt.bar(self.ctfreq, self.pwdbm, self.bar_width,bottom=-130,
                     alpha=self.opacity,
                     color='r',
                     
                     label='For USRP 192.168.20.2')
       
            #self.plt.gca().invert_yaxis()  
            self.plt.legend()
            
            self.fig.canvas.draw()     
                

            
if __name__ == '__main__': 
    try:
        global counter
        counter=0
        k=  MainData()
     
           
    except KeyboardInterrupt:
    
        pass
