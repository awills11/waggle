#!/usr/bin/env python
import socket, os, os.path, time, PacketHandler
from multiprocessing import Process, Queue
#from internal_communicator import server, client_push, client_pull
    
class internal_communicator(object):
    """ This class acts as the channel of communication to and from the GN and the NC. The internal_msg_handler pulls messages from the data cache, parses the header, and sends the message to the appropriate location. 
    It also recieves messages from the GNs and pushes them into the data cache.""" 
    #TODO write logic for putting messages back in DC if GN disconnects before message is sent
    
    def __init__(self):
        pass
    
    DC_push = Queue() #stores messages to be pushed to the DC
    incoming_request = Queue() #stores the unique ID of GNs currently connected
    incoming_msg = Queue() #stores incoming msgs #TODO will likely need to make a separate queue for each GN
    
class client_push(Process):
    """ A client process that connects to the data cache and pushes outgoing messages. """
    
    def run(self):
        comm = internal_communicator()
        while True:
            try:
                if not comm.DC_push.empty(): #if the queue is not empty, connect to DC and send msg
                    if os.path.exists('/tmp/Data_Cache_push_server'):
                        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        client_sock.connect('/tmp/Data_Cache_push_server')
                        print "Ready"
                        data = comm.DC_push.get() #theoretically pushes messages from the GN into a queue
                        print "sending: " , data
                        client_sock.sendall()
                        client_sock.close() #closes socket after each message is sent #TODO is there a better way to do this?
                    else: 
                        print 'Unable to connect to DC...'
                else: 
                    print 'sleeping'
                    time.sleep(1) #else, wait until messages are in queue
            except KeyboardInterrupt, k:
                    print "Shutting down."
                    break

class client_pull(Process):
    """ A client process that connects to the data cache and pulls incoming messages out. Sends a request in the format 'i,dev' and recieves the message"""
    
    def run(self):
        comm = internal_communicator()
        print "Connecting to data cache... client_pull"
        if os.path.exists('/tmp/Data_Cache_pull_server'):
            client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_sock.connect('/tmp/Data_Cache_pull_server')
            print "Ready"
            while True:
                while incoming_request.empty(): #sleeps until a GN initiates a pull request
                    time.sleep(1)
                try: 
                    dev = comm.incoming_request.get() #gets the dev ID that is initiating the pull request
                    dev += 'i,' + str(dev) #puts the request in the correct format for the DC
                        print "sending: " , dev
                        client_sock.send(dev)
                        msg = client_sock.recv(4028) #arbitrary, can go in config file
                        if not data:
                            comm.incoming.put(msg) #will be False if no messages are available in the DC for the GN
                        else: 
                            print 'Client_pull error...'
                        
                except KeyboardInterrupt, k:
                    print "Shutting down."
                    break
            client_sock.close()
        else:
            print "Couldn't Connect!"
        print "Done."
        
class push_server(Process):
    """ Server process that listens for connections from GNs. Gets messages from the guest nodes, parses head to get device ID (can also use device IP), and msg_p, 
    adds it to the message, along with indicator flag specifying that it is an outgoing message, stores it in DC_push queue... for now."""
    
    def run(self):
        print 'server process started'
        comm = internal_communicator()
        HOST = '0.0.0.0'
        PORT = 9090
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST,PORT))
        server.listen(5) #supports up to 5 threads, one for each GN
        
        while True:
            conn, addr = server.accept()
            print "Connected to ", addr
            while True:
                try:
                    data = conn.recv(4028) 
                    if not data:
                        header = PacketHandler.unpack_header(data)
                        if header['r_uniqid'] == 'cloud': #TODO replace with the actual unique ID for the cloud
                            dev, msg, order = header['flags'] #unpacks the tuple containing the flags
                            #adds each onto the msg string #TODO will this work with pickled things?
                            data += (str(order) + '|')
                            data += (str(msg) + ',')
                            data += (str(dev) +',')
                            data += 'o,' #indicates that it is an outgoing message
                            internal_communicator.DC_push.put(data)
                        elif header['r_uniqid'] == 'NC': #TODO replace with NC ID
                            pass #TODO messages just gets unpacked and handled by NC
                        else: 
                            print "Unknown recipient"
                    else:
                       pass
                except KeyboardInterrupt, k:
                    print "Shutting down."
                    break
            server.close()
            
class pull_server(Process):
    """ Server process that listens for connections from GNs. Gets messages from the Data Cache and sends them to connected GNs. """
    
    def run(self):
        print 'server process started'
        comm = internal_communicator()
        HOST = '0.0.0.0'
        PORT = 9090
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST,PORT))
        server.listen(5) #supports up to 5 threads, one for each GN
        
        while True:
            conn, addr = server.accept()
            print "Connected to ", addr
            while True:
                try:
                    data = conn.recv(40) #Guest Nodes connect and send their uniq_ID
                    if not data:
                        incoming_requests.put(data) #Unique ID goes into incoming requests queue. These get pulled out by the pull_client as pull requests
                        msg = False #if the DC takes longer than 15 seconds to put something in the queue, there is a connection problem. 
                        for i in range(15): #allows 15 seconds to get message from DC
                            if incoming.empty(): #TODO each GN should have a queue
                                time.sleep(1) #sleeps for a second then tries again
                            else:
                                msg = incoming.get()#if there are no messages for this GN, this returns False
                                break
                    conn.sendto(msg, addr) #sends the msg to the GN #TODO this may break
                    conn.close() #closes connection to GN? 
                    break #TODO does this break the while or the try?
                    else:
                       pass
                except KeyboardInterrupt, k:
                    print "Shutting down."
                    break
            server.close()
    

if __name__ == "__main__":
    try:
        #starts the pull server
        pull_serv = pull_server()
        pull_serv.start()
        
        #starts the push server 
        push_serv = push_server()
        push_serv.start()
        
        #starts the push client
        push_client = client_push()
        push_client.start()
        
        #starts the pull client
        pull_client = client_pull()
        pull_client.start()
        while True:
            pass
        
    except KeyboardInterrupt, k:
        pull_serv.terminate()
        push_serv.terminate()
        push_client.terminate()
        pull_client.terminate()
        print 'Done.'
    
                