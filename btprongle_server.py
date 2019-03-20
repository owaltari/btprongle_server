import os, time, select, ast
import opp80211
import logging
from threading import Thread #, Event
import Queue
from bluetooth import *

uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

class Session():
    def __init__(self):
        self.state = {'running': True,
                      'connected': False}

        self.wifi_iface_in = "mon0"
        self.wifi_iface_out = "mon1"

        self.upstream = Queue.Queue()
        self.downstream = Queue.Queue()

        self.upstream_proc_time = []
        self.downstream_proc_time = []
                
        self.serv_sock = None
        self.client_sock = None
        self.client_info = None

        
class BluetoothListener(Thread):
    def __init__(self, s):
        Thread.__init__(self)
        self.name = "BluetoothListener"
        self.state = s.state
        self.socket = s.client_sock
        self.upstream = s.upstream

        # The normal flow of information here is upstream.
        #  We need downstream here only for local echo replies (Android <-> Prongle latency)
        self.downstream = s.downstream
        
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
                    logging.debug("IOError while reading Bluetooth socket (Android app was closed?)")
                    self.state['connected'] = False
                    pass

                else: 
                    ts = int(round(time.time() * 1000))
                    logging.debug("Upstream data received")
                    
                    frame = ast.literal_eval(data)
                    if frame[0] == 201:
                        # If message ID == 201: This is a echo request to the prongle.
                        # Put the message downstream
                        logging.debug("Local echo request received: %s", frame[0])
                        self.downstream.put([data, ts])
                    else:
                        self.upstream.put([data, ts])

        if self.state['connected']:
            self.state['connected'] = False
        
        logging.debug("stopped")


class BluetoothDispatcher(Thread):
    def __init__(self, s):
        Thread.__init__(self)
        self.session = s
        self.name = "BluetoothDispatcher"
        self.state = s.state
        self.downstream = s.downstream
        self.socket = s.client_sock


    def run(self):
        logging.debug("started")

        while self.state['connected']:
            #msg = self.downstream_q.get()

            try:
                msg, ts1 = self.downstream.get(True, 1)
                logging.debug("found msg in downstream queue")
            except Queue.Empty:
                # Handle empty queue here
                pass
            
            else:
                self.socket.send(msg)
                delta = int(round(time.time() * 1000)) - ts1
                self.session.downstream_proc_time.append(delta)
                logging.debug("Downstream frame processed in %d ms", delta)
                self.downstream.task_done()
                
                
        logging.debug("stopped")
            
            
                    
def main():

    #state = {'running': True,
    #         'connected': False}

    session = Session()

    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s: %(message)s')
    
    while session.state['running']:          
        # Main loop for the program. One iteration per session. Start with
        #   setting up bluetooth listening for an incoming bind request.
        session.server_sock = BluetoothSocket(RFCOMM)
        session.server_sock.bind(("", PORT_ANY))
        session.server_sock.listen(1)
        port = session.server_sock.getsockname()[1]

        advertise_service(session.server_sock, "BTProngle",
                          service_id = uuid,
                          service_classes = [ uuid, SERIAL_PORT_CLASS ],
                          profiles = [ SERIAL_PORT_PROFILE ])
      
        logging.debug(" *** Waiting for connection on RFCOMM channel %d ***" % port)

        try:
            session.client_sock, session.client_info = session.server_sock.accept()
        except KeyboardInterrupt:
            break

        session.state['connected'] = True

        logging.debug("Accepted connection from %s", session.client_info[0])

        # Upstream threads
        wifi_out = opp80211.WiFiDispatcher(session)
        bluetooth_in = BluetoothListener(session)
        
        # Downstream threads
        wifi_in = opp80211.WiFiListener(session)
        bluetooth_out = BluetoothDispatcher(session)
        
        # upstream
        wifi_out.start()
        bluetooth_in.start()

        # downstream
        wifi_in.start()
        bluetooth_out.start()
        
        try:
            # This is where main thread sits during a session
            while session.state['connected']:
                time.sleep(1)
                
        except IOError:
            logging.debug("IOError caught")
            break
            
        except KeyboardInterrupt:
            logging.debug("KeyboardInterrupt")
            wifi_in.terminate()
            session.state['connected'] = False
            session.state['running'] = False
            break

        if session.state['connected']:
            session.state['connected'] = False
            
        session.server_sock.close()
        logging.debug("server_sock closed. Bringing threads down.")
        
        # Upstream
        wifi_out.join()
        bluetooth_in.join()

        # Downstream
        wifi_in.terminate()
        wifi_in.join() ## This is a tricky one because of scapys sniff stop_filter
        bluetooth_out.join()

        # Clear queues
        session.upstream.queue.clear()
        session.downstream.queue.clear()
        
        
    logging.debug("Bye.")
    
if __name__ == "__main__":
    main()
