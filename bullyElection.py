import random
from socket  import *
from constCS import * #-
from multiprocessing import Process
from threading import Thread
from typing import Dict, List
import time

class Node:
    def __init__(self, id_letter, id, listening_port):
        """The constructor for the Node class.
        Inputs:
            id_letter: The letter of the node's ID.
            id: The number of the node's ID. USed for election, which means that the node with the highest number wins. Note that two nodes might have the same id, in this case the ID_letter will be used.
            """
        self.id_letter = id_letter
        self.id = id
        self.coordinator = False
        self.listening_port = listening_port
        self.threads_counter = 0

    def init_server_listener(self):
        """Initializes the server listener for the node. This function is called as a process."""
        s = socket(AF_INET, SOCK_STREAM)
        s.bind((HOST, self.listening_port))  # AB: Bind the socket to specific IP address and port.
        s.listen(MAX_NUM_CLIENT_CONNECTIONS_TO_SERVER)  # AB: maximum number of connection to be accepted by siumltaneously by the server.
        while True:                # forever
            print("Node {} is listening on port: {} ...".format(self.id_letter, self.listening_port))
            (conn, addr) = s.accept()  # returns new socket and addr. of the client
            print("Node {} has accepted connection from {}:{}".format(self.id_letter, addr[0], addr[1]))
            thread_id = "{}:{}".format(self.id_letter, self.threads_counter)
            handle_server_request_thread = Thread(target=self.server_request_handler, args=(thread_id, addr, conn))
            handle_server_request_thread.start()
            self.threads_counter += 1
            # handle_server_request_thread.join()

    def server_request_handler(self, thread_id, addr, conn):
        data = conn.recv(1024)  # receive data from client
        msg = data.decode()  # process the incoming data into a response
        msg_content = msg.split(":")[0]
        if msg_content == "COORDINATOR":
            print("Node {} have received the coordinator message: {}".format(self.id_letter, msg))
            self.coordinator = False
            return
        electing_node_id_letter = msg.split(":")[1]
        electing_node_id = int(msg.split(":")[2])
        print("Node {} has received a message from node {}: {}".format(self.id_letter, electing_node_id_letter, msg))
        if electing_node_id < self.id or (electing_node_id == self.id and ord(electing_node_id_letter) < ord(self.id_letter)):
            print("Node {} sends OK message to node {}.".format(self.id_letter, electing_node_id))
            conn.send("OK".encode())
            self.start_election()

    def start_election(self):
        """Send messages to all other nodes as it does not know which node has a higher ID."""
        handles = []
        print("Node {} starts the election.".format(self.id_letter))
        self.does_node_with_higher_id_exist = False
        for node in nodes_list:
            node: Node = node
            if node.id_letter != self.id_letter and node.id >= self.id:
                handle_client_request_thread = Thread(target=self.send_election_message, args=("", node))
                handle_client_request_thread.start()
                handles.append(handle_client_request_thread)
                # self.__send_election_message(node)

        for handle in handles: # Make sure that all threads are finished before continuing.
            handle.join()
        
        if not self.does_node_with_higher_id_exist:
            print("Node {} is the coordinator.".format(self.id_letter))
            self.coordinator = True
            for node in nodes_list:
                node: Node = node
                if node.id_letter != self.id_letter:
                    self.send_coordinator_message(node)

    def send_coordinator_message(self, node):
        """Send to the node that I am the new coordinator."""
        node: Node = node
        print("Node {} sends coordinator message to node {}.".format(self.id_letter, node.id_letter))
        s = socket(AF_INET, SOCK_STREAM)
        s.connect((HOST, node.listening_port))
        msg = "COORDINATOR:{}:{}".format(self.id_letter, self.id) # Send a message to the node to notify it that I am the new coordinator.
        s.send(msg.encode())
        s.close()

    def send_election_message(self, _, node):
        """Send election message to a specific node and blocks till it gets a response or a timeout occurs.
        Outputs:
         - This function changes the value of the attribute `does_node_with_higher_id_exist` to True if the node with higher ID exists.
         """
        node: Node = node
        print("Node {} sends election message to node {}.".format(self.id_letter, node.id_letter))
        s = socket(AF_INET, SOCK_STREAM)
        s.connect((HOST, node.listening_port))
        msg = "ELECTION:{}:{}".format(self.id_letter, self.id) # Send an election message with the ID of the node for comparison.
        s.send(msg.encode())
        s.settimeout(CLIENT_THREAD_SLEEP_TIMEOUT_SECOND) # Set timeout for the receive function.
        try:
            data = s.recv(1024)
            data = data.decode()
            print("Node {} has received a message from node {}: {}".format(self.id_letter, node.id_letter, data))
            if data == "OK":
                self.does_node_with_higher_id_exist = True
        except timeout:
            print("Node {} has not received a message from node {}.".format(self.id_letter, node.id_letter))
        # if data:
        #     data = data.decode()
        #     print("Node {} has received a message from node {}: {}".format(self.id_letter, node.id_letter, data))
        #     if data == "OK":
        #         self.does_node_with_higher_id_exist = True
        # else:
        #     print("Node {} has not received a message from node {}.".format(self.id_letter, node.id_letter))
        s.close()


if __name__ == "__main__":
    n = int(input("Enter the number of nodes: ")) if not debug else N
    k = int(input("Enter k: ")) if not debug else K

    # Create the nodes
    nodes_list: List[Node] = []
    for i in range(n):
        node = Node(chr(ord('A') + i), random.randint(1, k), PORT_START + i)
        nodes_list.append(node)
        client_handler = Process(target=node.init_server_listener)
        client_handler.start()
        print("Create Node {} that has ID {} and the election ID is: {}".format(i, node.id_letter, node.id))
    time.sleep(1) # Wait for the servers to start listening.
    # Start the election by choosing a random node.
    random_node_id = random.randint(0, n - 1)
    random_node = nodes_list[random_node_id]
    random_node.start_election()
