import os, time
import pickle
from threading import Thread, Event

import Queue
#from Queue import Queue
from scapy.all import *

# This file is designed to be imported in btprongle_server.py, but can
# be executed by itself for developement and debugging purposes.

test_q = Queue.Queue()
stop_e = Event()

# globals
interface = "mon0" # FIXTHIS: This comes from the main program as an attribute
seq = 1

class Frame():
    def __init__(self, attr): # attr not used for anything at the moment
        global seq
        self.attr = attr

        self._type = 2 # data
        self._subtype = 0
        self._FCfield = 0b01000000 # protected, ad-hoc

        self._SC = seq << 4
        seq += 1
        
        self.sa = "11:11:11:11:11:11" # sender
        self.da = "11:11:11:11:11:11" # destination
        self.ra = "11:11:11:11:11:11" # receiver
        self.null_addr = "00:00:00:00:00:00"

        self.payload = ""
                
        #print "opp80211"
        

    def compose(self):

        # add mock wep
        data = "".join(['\xff\xff\xff\x00', self.payload, '\x00\x00\x00\x00'])
        
        packet = RadioTap()/Dot11(type=self._type, subtype=self._subtype,
                                  FCfield=self._FCfield, SC=self._SC,
                                  addr1=self.sa,
                                  addr2=self.da,
                                  addr3=self.ra,
                                  addr4=self.null_addr) / Raw(load=data)
        return packet

    
class WiFiListener(Thread):
    def __init__(self, q, interface, stop_e):
        Thread.__init__(self)
        self.downstream_q = q
        self.iface = interface
        self.stop = stop_e
        
    def callback(self, pkt):
        #print pkt.summary()
        pkt.show()
        hexdump(pkt)
        try:
            msg = pkt.wepdata[:-4]
            #TODO: sanity check input and possibly unpickle
            self.downstream_q.put(pickle.loads(msg))
        except Exception:
            pass
        
        return
        
    def run(self):
        sniff(filter="ether host 11:11:11:11:11:11",
              iface=self.iface,
              prn=self.callback,
              #lfilter=lambda x: x.type==0 and x.subtype==4,
              stop_filter=lambda p: self.stop.isSet(),
              store=0)
        print "Sniffer stopped."
        


class WiFiDispatcher(Thread):
    def __init__(self, q, interface):
        Thread.__init__(self)
        self.iface = interface
        self.upstream_q = q
        self.stop = False
        
    def run(self):
        while True:
            msg = self.upstream_q.get()
             
            f = Frame("attributes here")
            f.payload = pickle.dumps(msg)
            packet = f.compose()
            
            packet.show()
            hexdump(packet)
            sendp(packet, iface=interface)
            
            
        
"""        
class Dot11EltRates(Packet):
    name = "802.11 Rates Information Element"
    # Our Test STA supports the rates 6, 9, 12, 18, 24, 36, 48 and 54 Mbps
    supported_rates = [0x0c, 0x12, 0x18, 0x24, 0x30, 0x48, 0x60, 0x6c]
    fields_desc = [ByteField("ID", 1), ByteField("len", len(supported_rates))]
    for index, rate in enumerate(supported_rates):
        fields_desc.append(ByteField("supported_rate{0}".format(index + 1), rate))
"""


def main():
    print "This is the WiFi module for BTprongle server."

    sniffer = WiFiListener(test_q, interface, stop_e)

    sniffer.start()

    while True:
        try:
            cmd = raw_input("> ")
        except KeyboardInterrupt:
            stop_e.set()
            break

    sniffer.join()
    


    #f = Frame("attributes here")
    #packet = f.compose()
    #packet.show()
    #sendp(packet, loop=1, inter=1.0, iface=interface)

    
   
if __name__ == "__main__":
    main()
