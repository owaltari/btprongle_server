import os, time
import opp80211
from threading import Thread, Event
from Queue import Queue
from bluetooth import *


wifi_iface = "mon0"
server_sock = BluetoothSocket(RFCOMM)
server_sock.bind(("", PORT_ANY))
server_sock.listen(1)

connection = Event()
stop_e = Event()

upstream = Queue()
downstream = Queue()

port = server_sock.getsockname()[1]

uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

advertise_service(server_sock, "BTProngle",
                  service_id = uuid,
                  service_classes = [ uuid, SERIAL_PORT_CLASS ],
                  profiles = [ SERIAL_PORT_PROFILE ], 
                  #protocols = [ OBEX_UUID ] 
)


class BluetoothListener(Thread):
    def __init__(self, q, sock):
        Thread.__init__(self)
        self.socket = sock
        self.upstream_q = q

        
    def run(self): 

        while connection.isSet():
            try:
                
	        data = self.socket.recv(1024)
                if len(data) == 0:
                    print "len(data) == 0 ; break"
                    # TODO: appropriate thread cleanup
                    break

                # This is where WiFiDispatch should be called
                print "received [%s]" % data
                self.upstream_q.put(data)
                
            except IOError:
                print "except"
	        break # or pass? Find out why and how often IOError occurs
    
            except KeyboardInterrupt:
            	print "disconnected"
                self.socket.close()
                break
            
        if connection.isSet():
            connection.clear()

class BluetoothDispatcher(Thread):
    def __init__(self, q, sock):
        Thread.__init__(self)
        self.socket = sock
        self.downstream_q = q

    def run(self):
        while True:
            msg = self.downstream_q.get()
            self.socket.send(msg)
            print "downstream queue: "+msg
            self.downstream_q.task_done()
            
            
            
"""            
class TextInput(Thread):
    def __init__(self, s):
        Thread.__init__(self)
        self.sock = s

        
    def run(self):
        while connection.locked():
            try:
                msg = raw_input("> ")
                self.sock.send(msg)
            except IOError:
                break
            
            except KeyboardInterrupt:
            	print "disconnected"
                self.sock.close()
	        #server_sock.close()
	        print "all done"
                break
        connection.release()
"""
        
def main():

    global connection

    
    
    while True:          
        print "Waiting for connection on RFCOMM channel %d" % port
    
        client_sock, client_info = server_sock.accept()
        connection.set()
        print "Accepted connection from ", client_info

        wifi_out = opp80211.WiFiDispatcher(upstream, wifi_iface)
        bluetooth_in = BluetoothListener(upstream, client_sock)
        
        wifi_in = opp80211.WiFiListener(downstream, wifi_iface, stop_e)
        bluetooth_out = BluetoothDispatcher(downstream, client_sock)

        
        # upstream
        wifi_out.start()
        bluetooth_in.start()

        # downstream
        wifi_in.start()
        bluetooth_out.start()
        
        
        while connection.isSet():

            
            # print list(msgq.queue)
            try:
                msg = raw_input("> ")
                client_sock.send(msg)
            except IOError:
                break
            
            except KeyboardInterrupt:
            	print "disconnected"
                client_sock.close()
                stop_e.set()
	        #server_sock.close()
                break
        if connection.isSet():
            connection.clear()
        
        #sniffer.terminate()
        bluetooth_in.join()
        #thread_out.join()
        
    #listener()

    
if __name__ == "__main__":
    main()
