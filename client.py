# Python 3
# Usage: python3 client.py server_IP server_port
# COMP 9331: Computer Networks and Applications, Term 3 - 2019
# Instant Messaging Application
# Client code

# Developed by: Sahil Punchhi, z5204256
# version 1.0, 20th November, 2019

import sys
import socket
import selectors
import types
import threading

# using selectors for selecting and registering sockets
sel = selectors.DefaultSelector()

HOST = sys.argv[1]
PORT = int(sys.argv[2])

# file which stores login names and passwords
file_name = "credentials.txt"


def new_client_sock(ip, port):

    # create a new TCP socket and bind it with existing client ip and client port to listen to other sockets
    new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    new_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    new_sock.bind((ip, port))
    new_sock.listen(10)

    try:
        while True:

            # accept requests when other clients try to connect
            client_sock, address = new_sock.accept()

            # receive data from the client who has just connected
            data = client_sock.recv(1024).decode()
            data = data.strip()

            # extract user and name from the client
            user = data.split(" ", 1)[0]
            name = data.split(" ", 2)[1]
            msg = data.split(" ", 2)[2]
            print(name, msg, sep=" ")

            # add client socket to the name of the client in the dictionary
            my_dict[name] = client_sock

            # send a connection confirmation response to the client
            response = "You have successfully established a private connection with " + user + "."
            client_sock.send(response.encode())

            # register client socket
            sel.register(client_sock, selectors.EVENT_READ, data=None)

    except KeyboardInterrupt:
        new_sock.close()
    finally:
        new_sock.close()


if __name__ == "__main__":

    # dictionary for credentials, key is username, value is password
    credentials_dict = dict()
    # dictionary for sending messages, key is username, value is socket
    my_dict = dict()
    # log stores names of all the users who have logged out after the client connected with server
    # if user comes online again, it is removed from the set
    log = set()

    # takes all elements (numbers) from the text file into a list
    with open(file_name) as inputfile:
        for line in inputfile:
            line = line.strip()
            words = line.split(" ")
            credentials_dict[words[0]] = words[1]

    # create a TCP client socket and connect with server
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client.connect((HOST, PORT))

    uname = input('Enter your username: \n')
    info = uname
    client.send(info.encode())

    # registering client socket and standard input socket
    sel.register(sys.stdin, selectors.EVENT_READ, data=None)
    sel.register(client, selectors.EVENT_READ, data=None)

    client_ip = client.getsockname()[0]
    client_port = client.getsockname()[1]

    recv_thread = threading.Thread(name="new_client_sock", target=new_client_sock, args=(client_ip, client_port))
    recv_thread.daemon = True
    recv_thread.start()

    try:
        while True:
            events = sel.select()
            for key, mask in events:
                sock = key.fileobj

                # interaction of client with the server
                if sock == client:
                    try:
                        data = sock.recv(1024).decode()
                        data = data.strip()
                        word = data.split(" ", 1)[0]

                        if word == "LOGIN":
                            login_user = data.split(' ', 2)[1]
                            if login_user in log:
                                log.remove(login_user)
                            # log.add(login_user)
                            status = data.split(" ", 1)[1]
                            print(status)

                        elif word == "LOGOUT":
                            logout_user = data.split(' ', 2)[1]
                            log.add(logout_user)
                            status = data.split(" ", 1)[1]
                            print(status)

                        elif word == "IP":
                            # get IP address and port number used by other client
                            IP_address = data.split(' ', 2)[1]
                            port_number = int(data.split(' ', 3)[2])
                            user = data.split(' ', 3)[3]

                            # create a new TCP socket to connect with other client
                            my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            my_socket.connect((IP_address, port_number))
                            sel.register(my_socket, selectors.EVENT_READ, data=None)

                            msg_to_be_sent = user + ' ' + uname + " has now a private connection with you."
                            my_socket.send(msg_to_be_sent.encode())
                            # dictionary for sending:
                            my_dict[user] = my_socket

                        else:
                            # in all other cases print all the data received from the server
                            print(data)

                    except:
                        print("Error")


                # interaction with standard input socket
                elif sock == sys.stdin:
                    try:
                        msg = input()
                        msg = msg.strip()
                        length = len(msg.split())
                        word_start = msg.split(' ', 1)[0]

                        if word_start == 'private':
                            if length >= 2:

                                user = msg.split(' ', 2)[1]

                                if user == uname:
                                    print("You cannot start a private chat with yourself.")

                                elif (user in my_dict) and (user not in log):
                                    if length >= 3:
                                        actual_message = msg.split(' ', 2)[2]
                                        msg_del = uname + '(private)' + '>' + ' ' + msg.split(' ', 2)[2]
                                        my_dict[user].send(msg_del.encode())
                                    else:
                                        print("Mention message to be sent to the user.")

                                elif (user in my_dict) and (user in log):
                                    # if user has logged out and went offline after the start of private chat
                                    # my_dict.remove(user)
                                    del my_dict[user]
                                    print("User has went offline.")

                                elif user in credentials_dict:
                                    print("You have not established a private connection with ", user, ".", sep='')

                                else:
                                    print("User does not exist.")

                            else:
                                print("Mention name of the user.")

                        elif word_start == "stopprivate":
                            if length == 2:

                                user = msg.split(' ', 1)[1]

                                if user == uname:
                                    print("You cannot stop a private chat with yourself.")
                                elif (user in my_dict):
                                    update = "STOP" + ' ' + uname
                                    my_dict[user].send(update.encode())
                                    del my_dict[user]
                                    print("You have stopped a private connection with ", user, ".", sep='')
                                else:
                                    print("You do not have an active private connection with ", user, ".", sep='')

                                if (uname in my_dict):
                                    del my_dict[uname]

                            elif length == 1:
                                print("Mention name of the user.")

                            else:
                                print("Incorrect command.")

                        else:
                            client.send(msg.encode())
                    except:
                        print("Incorrect command.")

                # interaction with all other client sockets
                else:
                    try:
                        data = sock.recv(1024).decode()
                        data = data.strip()
                        first_word = data.split(" ", 1)[0]
                        if first_word == "STOP":
                            user = data.split(" ", 2)[1]
                            if user in my_dict:
                                # delete user's socket from the dictionary
                                del my_dict[user]
                                print(user, " has stopped the private connection with you.", sep='')
                        else:
                            print(data)
                    except:
                        print("Error")

    except:
         print("Error")