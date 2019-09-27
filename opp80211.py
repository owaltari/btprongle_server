import os, time
import pickle, zlib, hashlib
import logging
from threading import Thread, Event
import Queue
from scapy.all import *

# This file is designed to be imported in btprongle_server.py, but can
# be executed by itself for developement and debugging purposes.

random.seed()
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

        
    def compose(self):

        picklewrapper = pickle.dumps(self.data)

        # add mock wep
        wepdata = "".join(['\xff\xff\xff\x00', picklewrapper, '\x00\x00\x00\x00'])
        
        if len(wepdata) > 1465:
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
    def __init__(self, s):
        Thread.__init__(self)
        self.session = s
        self.name = "WiFiListener"
        self.state = s.state
        self.downstream = s.downstream
        self.iface = s.wifi_iface_in
        
    def callback(self, pkt):
        ts = int(round(time.time() * 1000))
        # Downstream data received
        #logging.debug("Downstream data received")

        if self.session.debug:
            print "\n\n"
            logging.debug("WiFiListener caught this:")
            ls(pkt)
            print " **** "
            hexdump(pkt)
        
        try:
            if not pkt.wepdata:
                return

            msg = str(pickle.loads(pkt.wepdata))

            # CRC32 is used for weeding out duplicates. This used to be md5,
            #   but on the raspberries CRC32 is a whole lot faster.
            checksum = zlib.crc32(bytes(msg)) & 0xffffffff
            # check if this checksum is in backlog
            #logging.debug("check if this checksum is in backlog: %s", checksum)
            if checksum in self.session.backlog:
                # Do not put the frame downstream since it has been seen already
                #logging.debug("!! checksum is in backlog !!")
                pass
            else:
                logging.debug("Incoming frame payload: %s", msg)
                self.session.backlog.append(checksum)
                self.downstream.put([msg, ts])
            logging.debug("current backlog: %s", self.session.backlog)
                
        except Exception as e:
            logging.debug(e)
            pass
        
        return

    
    def run(self):
        logging.debug("sniffer started")

        sniff(filter="ether dst 11:11:11:11:11:11",
              iface=self.iface,
              prn=self.callback,
              stop_filter=lambda p: not self.state['connected'],
              store=0)
        logging.debug("stopped")

        
    def terminate(self):
        logging.debug("graceful termination of WiFiListener requested")    
        # This is a workaround to terminate sniff. We generate a dummy frame
        # that is caught by sniff leading it to trigger stop_filter.

        stopf = Frame("Stop frame")
        p = stopf.compose()
        sendp(p, iface=self.iface)
        
        

class WiFiDispatcher(Thread):
    def __init__(self, s):
        Thread.__init__(self)
        self.session = s
        self.name = "WiFiDispatcher"
        self.state = s.state
        self.upstream = s.upstream
        self.iface = s.wifi_iface_out

        
    def run(self):
        logging.debug("started")
        while self.state['connected']:
            try:
                msg, ts1 = self.upstream.get(True, 5)

            except Queue.Empty:
                pass

            else:
                f = Frame("attributes here")
                logging.debug("Outgoing frame payload: %s", msg)
                f.data = msg
                packet = f.compose()
            
                if self.session.debug:
                    packet.show()
                    hexdump(packet)
                sendp(packet, iface=self.iface)
                delta = int(round(time.time() * 1000)) - ts1
                sendp(packet, iface=self.iface)
                self.session.upstream_proc_time.append(delta)
                self.session.write_log_entry("upstream_proc_t", delta)
                logging.debug("Upstream frame processed in %d ms\n", delta)
        logging.debug("stopped")
            
            
def main():

    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s: %(message)s')

    print "This is the WiFi module for BTprongle server."
    
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

            sendp(packet, iface="mon1")
            #sendp(packet, loop=1, inter=1.0, iface=interface)
            logging.debug("frame sent")

        except KeyboardInterrupt:
            break

    
   
if __name__ == "__main__":
    main()
