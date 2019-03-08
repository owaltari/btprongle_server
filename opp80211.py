import os, time
import pickle
import logging
from threading import Thread, Event
import Queue
from scapy.all import *

# This file is designed to be imported in btprongle_server.py, but can
# be executed by itself for developement and debugging purposes.

test_q = Queue.Queue()
random.seed()

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

        self.data = None
        
        #print "opp80211"
        

    def compose(self):

        picklewrapper = pickle.dumps(self.data)

        # add mock wep
        wepdata = "".join(['\xff\xff\xff\x00', picklewrapper, '\x00\x00\x00\x00'])
        
        if len(wepdata) < 1465:
            logging.debug("Payload too long for one frame! FIXTHIS")
            pass # Check if frame is too long
        
        packet = RadioTap()/Dot11(type=self._type, subtype=self._subtype,
                                  FCfield=self._FCfield, SC=self._SC,
                                  addr1=self.sa,
                                  addr2=self.da,
                                  addr3=self.ra,
                                  addr4=self.null_addr) / Raw(load=wepdata)
        return packet

    
class WiFiListener(Thread):
    def __init__(self, s, q, interface):
        Thread.__init__(self)
        self.name = "WiFiListener"
        self.state = s
        self.downstream_q = q
        self.iface = interface
        
    def callback(self, pkt):
        #print pkt.summary()
        logging.debug("WiFiListener caught this:")
        pkt.show()
        hexdump(pkt)

        try:
            if not pkt.wepdata:
                return

            msg = str(pickle.loads(pkt.wepdata))
            #TODO: sanity check and add logic
            self.downstream_q.put(msg)
            logging.debug("msg (%s) was put into downstream queue", msg)

        except Exception as e:
            logging.debug(e)
            pass
        
        return

    
    def run(self):
        logging.debug("started")

        sniff(filter="ether host 11:11:11:11:11:11",
              iface=self.iface,
              prn=self.callback,
              #lfilter=lambda x: x.type==0 and x.subtype==4,
              stop_filter=lambda p: not self.state['connected'],
              #stop_filter=lambda p: self.stop.isSet(),
              store=0)
        logging.debug("stopped")

        
    def terminate(self):
        logging.debug("graceful termination of WiFiListener requested")    
        # This is a workaround to terminate sniff. We generate a dummy frame
        # that is caught by sniff leading it to trigger stop_filter.

        stopf = Frame("Stop frame")
        p = stopf.compose()
        sendp(p, iface=interface)
        
        

class WiFiDispatcher(Thread):
    def __init__(self, s, q, interface):
        Thread.__init__(self)
        self.name = "WiFiDispatcher"
        self.state = s
        self.upstream_q = q
        self.iface = interface

        
    def run(self):
        logging.debug("started")
        while self.state['connected']:
            try:
                msg = self.upstream_q.get(True, 5)

            except Queue.Empty:
                pass

            else:
                f = Frame("attributes here")

                f.data = msg
                packet = f.compose()
            
                packet.show()
                hexdump(packet)
                sendp(packet, iface=interface)

                
        logging.debug("stopped")
            
            
        
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

    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s: %(message)s')

    print "This is the WiFi module for BTprongle server."
    
    #sniffer = WiFiListener(test_q, interface, stop_e)
    #sniffer.start()

    while True:

        try:
            msg = raw_input("> ")
            # TODO: implement attribute control. As of now, all input goes as
            #       payload in a frame with default parameters.

            f = Frame("attributes go here")
            f.payload = pickle.dumps(msg)
            packet = f.compose()
            
            packet.show()
            hexdump(packet)

            sendp(packet, iface=interface)
            #sendp(packet, loop=1, inter=1.0, iface=interface)
            logging.debug("frame sent")

        except KeyboardInterrupt:
            break

    
   
if __name__ == "__main__":
    main()
