import os, time, select
import opp80211
import logging
from threading import Thread #, Event
import Queue
from bluetooth import *


wifi_iface = "mon0"
server_sock = BluetoothSocket(RFCOMM)
server_sock.bind(("", PORT_ANY))
server_sock.listen(1)

#connection = Event()
#stop_e = Event()

upstream = Queue.Queue()
downstream = Queue.Queue()

port = server_sock.getsockname()[1]

uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

advertise_service(server_sock, "BTProngle",
                  service_id = uuid,
                  service_classes = [ uuid, SERIAL_PORT_CLASS ],
                  profiles = [ SERIAL_PORT_PROFILE ], 
                  #protocols = [ OBEX_UUID ] 
)


class BluetoothListener(Thread):
    def __init__(self, s, q, sock):
        Thread.__init__(self)
        self.name = "BluetoothListener"
        self.state = s
        self.socket = sock
        self.upstream_q = q

        self.socket.setblocking(0)

    
    def run(self): 

        logging.debug("started")
        
        while self.state['connected']:
            #logging.debug("recv select loop")
            ready = select.select([self.socket], [], [], 5)

            if ready[0]:
                try:
                    data = self.socket.recv(1024)
                    if len(data) == 0:
                        logging.debug("Empty socket read (EOF)")
                        break

                except IOError:
                    # FIXTHIS: Rotating the BTProngle app between landscape and
                    #          portrait triggers an IOError on rfcomm read.
                    #          Not sure how to fix. Might even be intentional.
                    logging.debug("IOError while reading Bluetooth socket")
                    self.state['connected'] = False
                    pass

                else: 
                    logging.debug("Upstream data received")
                    self.upstream_q.put(data)

        if self.state['connected']:
            self.state['connected'] = False
        
        logging.debug("stopped")


class BluetoothDispatcher(Thread):
    def __init__(self, s, q, sock):
        Thread.__init__(self)
        self.name = "BluetoothDispatcher"
        self.state = s
        self.downstream_q = q
        self.socket = sock


    def run(self):
        logging.debug("started")

        while self.state['connected']:
            #msg = self.downstream_q.get()

            try:
                msg = self.downstream_q.get(True, 1)
                logging.debug("found msg in downstream queue")
            except Queue.Empty:
                # Handle empty queue here
                pass
            
            else:
                self.socket.send(msg)
                print "downstream queue: "+msg
                self.downstream_q.task_done()

                
        logging.debug("stopped")
            
            
                    
def main():

    state = {'running': True,
             'connected': False}
    
    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s: %(message)s')
    
    while state['running']:          

        logging.debug("Waiting for connection on RFCOMM channel %d" % port)
    
        try:
            client_sock, client_info = server_sock.accept()
        except KeyboardInterrupt:
            break
            
        state['connected'] = True

        logging.debug("Accepted connection from %s", client_info[0])

        # Upstream threads
        wifi_out = opp80211.WiFiDispatcher(state, upstream, wifi_iface)
        bluetooth_in = BluetoothListener(state, upstream, client_sock)
        
        # Downstream threads
        wifi_in = opp80211.WiFiListener(state, downstream, wifi_iface)
        bluetooth_out = BluetoothDispatcher(state, downstream, client_sock)

        
        # upstream
        wifi_out.start()
        bluetooth_in.start()

        # downstream
        wifi_in.start()
        bluetooth_out.start()
        
        
        while state['connected']:
        #while connection.isSet():

            # print list(msgq.queue)
            try:
                msg = raw_input("> ")
                client_sock.send(msg)
            except IOError:
                logging.debug("IOError caught")
                break
            
            except KeyboardInterrupt:
                logging.debug("KeyboardInterrupt")
                state['connected'] = False
                state['running'] = False
                #client_sock.close()
                #stop_e.set()
                break



        if state['connected']:
            state['connected'] = False
            
        #if connection.isSet():
        #    connection.clear()
        
        server_sock.close()
                            
        # Upstream
        wifi_out.join()
        bluetooth_in.join()

        # Downstream
        wifi_in.terminate()
        wifi_in.join() ## This is a tricky one because of scapys sniff stop_filter
        bluetooth_out.join()
        
        
    logging.debug("Bye.")
    
if __name__ == "__main__":
    main()
