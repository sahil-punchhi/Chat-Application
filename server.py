# Python 3
# Usage: python3 server.py server_port block_duration timeout
# COMP 9331: Computer Networks and Applications, Term 3 - 2019
# Instant Messaging Application
# Server code

# Developed by: Sahil Punchhi, z5204256
# version 1.0, 20th November, 2019

import sys
import time
import socket
import threading
import selectors
from collections import defaultdict
import math
import datetime


buf_size = 1024
update_interval = 1

# time period which blocks user after 3 failed login attempts
block_time = int(sys.argv[2])

# time period after which a user gets logged out because of no activity
# (i.e. no input commands from the user, receipt of a message does not count)
timeout = int(sys.argv[3])

# file which stores login names and passwords
file_name = "credentials.txt"


# function to accept the client, checks login details and starts the client threads
def accept_client():
    global credentials_dict
    global connection_list_dict
    global name_list
    global login_blocked_users
    global last_command_time_dict
    global address_dict

    while True:
        # accept
        cli_sock, cli_add = ser_sock.accept()

        # checks username
        try:

            name = cli_sock.recv(buf_size).decode().strip()

        except:
            cli_sock.send("Invalid username.".encode())

        while True:
            if name in name_list:
                cli_sock.send("Username already in use.".encode())
                break

            if name in credentials_dict:
                pass
            else:
                cli_sock.send("Invalid username.".encode())
                break

            # checks password
            cli_sock.send("Enter your password: ".encode())
            password = cli_sock.recv(buf_size).decode().strip()
            if (name in login_blocked_users) and (time.time() - login_blocked_users[name] <= block_time):
                cli_sock.send(
                    "Your account is blocked due to multiple login failures. Please try again later.".encode())
                break
            elif (name in login_blocked_users) and (time.time() - login_blocked_users[name] > block_time):
                del login_blocked_users[name]
            if credentials_dict[name] == password:
                pass
            else:
                response = "Invalid password. Please try again.\n" + "Enter your password: "
                cli_sock.send(response.encode())
                password = cli_sock.recv(buf_size).decode().strip()
                if credentials_dict[name] == password:
                    pass
                else:
                    response = "Invalid password. Please try again.\n" + "Enter your password: "
                    cli_sock.send(response.encode())
                    password = cli_sock.recv(buf_size).decode().strip()
                    if credentials_dict[name] == password:
                        pass
                    else:
                        cli_sock.send(
                            "Invalid password. Your account has been temporarily blocked. Please try again later.".encode())
                        login_blocked_users[name] = time.time()
                        break

            # various client details stored in lists and dictionaries (defined in main)
            login_time_dict[name] = time.time()
            last_command_time_dict[cli_sock] = time.time()
            connection_list.append(cli_sock)
            name_list.append(name)
            connection_list_dict[cli_sock] = name
            address_dict[name] = cli_add

            # confirmation notification
            cli_sock.send("Welcome to the greatest messaging app ever!".encode())

            # deliver all the stored/offline messages for the user
            if name in stored_messages_dict:
                stored_messages_on_server = stored_messages_dict.pop(name)
                if len(stored_messages_on_server) > 0:
                    offline_messages = "\nHere are your offline messages: \n"
                    for offline_message in stored_messages_on_server:
                        offline_messages = offline_messages + offline_message + '\n'
                    offline_messages = offline_messages.strip()
                    cli_sock.send(offline_messages.encode())

            # login notification sent to all users
            status = 'LOGIN' + ' ' + name + " has logged in."
            broadcast_notifications(cli_sock, status)

            # client thread for commands by the user
            thread_client = threading.Thread(target=user_command, args=[cli_sock])
            thread_client.start()

            # client thread to check activity of the user
            thread_client_logout = threading.Thread(target=check_logout, args=[cli_sock])
            thread_client_logout.start()

            break


# function which logs out client because of no activity
def check_logout(cli_sock):

    while True:

        time.sleep(update_interval)

        try:
            if time.time() - last_command_time_dict[cli_sock] > timeout:
                status = 'LOGOUT' + ' ' + connection_list_dict[cli_sock] + " has logged out."
                broadcast_notifications(cli_sock, status)
                cli_sock.close()

                # update logout time in login time dict since user was online upto that time
                login_time_dict[connection_list_dict[cli_sock]] = time.time()
                connection_list.remove(cli_sock)
                name_list.remove(connection_list_dict[cli_sock])
                del connection_list_dict[cli_sock]
                del last_command_time_dict[cli_sock]

                break
        except:
            break


# function which returns the key for a particular value in a dictionary
def get_key(dictionary, val):
    for key, value in dictionary.items():
        if val == value:
            return key


# function for various commands received from the user
def user_command(cli_sock):
    while True:
        try:
            # server receives data from client side
            data = cli_sock.recv(buf_size).decode()
            data_recv_time = time.time()
            last_command_time_dict[cli_sock] = data_recv_time
            data = data.strip()
            length = len(data.split())
            word1 = data.split(' ', 1)[0]

            # checks for different commands below:

            # if command is message
            if word1 == "message":
                if length >= 2:
                    from_word_2 = data.split(' ', 1)[1]
                    # word2 here is the user to whom message should be sent
                    word2 = from_word_2.split(' ', 1)[0]
                    # user should be in credentials dictionary
                    if word2 in credentials_dict:
                        # if user is the sender itself
                        if word2 == connection_list_dict[cli_sock]:
                            cli_sock.send("You cannot message yourself.".encode())
                        else:
                            if length >= 3:
                                message = from_word_2.split(' ', 1)[1]
                                # if user is online but sender has blocked the user
                                if word2 in blocked_user_dict[connection_list_dict[cli_sock]]:
                                    cli_sock.send("You have blocked the user. "
                                                  "You need to unblock the user to send your message.".encode())
                                # if user is online and has not blocked the sender
                                elif (word2 in name_list) and (
                                        connection_list_dict[cli_sock] not in blocked_user_dict[word2]):
                                    data = connection_list_dict[cli_sock] + '> ' + message
                                    user_socket = get_key(connection_list_dict, word2)
                                    user_socket.send(data.encode())
                                # if user is online but has blocked the sender
                                elif (word2 in name_list) and (
                                        connection_list_dict[cli_sock] in blocked_user_dict[word2]):
                                    cli_sock.send(
                                        "Your message could not be delivered as the recipient has blocked you.".encode())
                                # if user is offline, message is stored and delivered later when the user comes online
                                elif (word2 not in name_list) and (
                                        connection_list_dict[cli_sock] not in blocked_user_dict[word2]):
                                    offline_message = connection_list_dict[cli_sock] + '> ' + message
                                    stored_messages_dict[word2].append(offline_message)
                            else:
                                cli_sock.send("Incorrect command. Please mention message to the user.".encode())
                    else:
                        cli_sock.send("User does not exist".encode())
                else:
                    cli_sock.send("Incorrect command. Please mention user and message.".encode())

            # if command is broadcast
            elif word1 == "broadcast":
                if length >= 2:
                    broadcast_message = data.split(' ', 1)[1]
                    broadcast_user(cli_sock, broadcast_message)
                else:
                    cli_sock.send("Incorrect command. Please mention broadcast message.".encode())

            # if command is whoelse
            elif word1 == "whoelse":
                if length >= 2:
                    cli_sock.send("Incorrect command.".encode())
                else:
                    online_users = ''
                    # checks all online users in dictionary and adds them to a string
                    for key, value in connection_list_dict.items():
                        if value != connection_list_dict[cli_sock]:
                            online_users = online_users + value + '\n'
                    online_users = online_users.strip()
                    cli_sock.send(online_users.encode())

            # if command is whoelsesince
            elif word1 == "whoelsesince":
                if length == 2:
                    try:
                        past_time = int(data.split(' ', 1)[1])
                        online_users_since = ''
                        # checks for users in login time dictionary
                        for key, value in login_time_dict.items():
                            if (key != connection_list_dict[cli_sock]) and (
                                    ((data_recv_time - value) <= past_time) | (key in name_list)):
                                online_users_since = online_users_since + key + '\n'
                        online_users_since = online_users_since.strip()
                        cli_sock.send(online_users_since.encode())
                    except:
                        cli_sock.send("Incorrect command.".encode())
                else:
                    cli_sock.send("Incorrect command.".encode())

            # if command is logout
            elif word1 == "logout":
                if length >= 2:
                    cli_sock.send("Incorrect command.".encode())
                else:
                    status = 'LOGOUT' + ' ' + connection_list_dict[cli_sock] + " has logged out."
                    broadcast_notifications(cli_sock, status)
                    # cli_sock.send("You have been successfully logged out.".encode())
                    cli_sock.close()
                    # update logout time in login time dict since user was online upto that time
                    login_time_dict[connection_list_dict[cli_sock]] = time.time()
                    connection_list.remove(cli_sock)
                    name_list.remove(connection_list_dict[cli_sock])
                    del connection_list_dict[cli_sock]
                    break

            # if command is block
            elif word1 == "block":
                if length > 2:
                    cli_sock.send("Incorrect command.".encode())
                elif length == 1:
                    cli_sock.send("Specify the user you want to block.".encode())
                else:
                    blocked_user = data.split(' ', 1)[1]
                    if blocked_user == connection_list_dict[cli_sock]:
                        cli_sock.send("You cannot block yourself.".encode())
                    elif blocked_user not in credentials_dict:
                        cli_sock.send("The user you want to block does not exist.".encode())
                    else:
                        # add to blocked user dictionary
                        blocked_user_dict[connection_list_dict[cli_sock]].add(blocked_user)
                        info = "You have blocked " + blocked_user + "."
                        cli_sock.send(info.encode())

            # if command is unblock
            elif word1 == "unblock":
                if length > 2:
                    cli_sock.send("Incorrect command.".encode())
                elif length == 1:
                    cli_sock.send("Specify the user you want to unblock.".encode())
                else:
                    unblock_user = data.split(' ', 1)[1]
                    if (unblock_user in credentials_dict) and unblock_user != connection_list_dict[cli_sock]:
                        for key in blocked_user_dict.keys():
                            if key == connection_list_dict[cli_sock]:
                                if unblock_user in blocked_user_dict[key]:
                                    # remove user from blocked dictionary
                                    blocked_user_dict[key].remove(unblock_user)
                                    info = unblock_user + " is unblocked."
                                    cli_sock.send(info.encode())
                                else:
                                    info = unblock_user + " was not blocked."
                                    cli_sock.send(info.encode())
                    elif unblock_user == connection_list_dict[cli_sock]:
                        cli_sock.send("You cannot unblock yourself.".encode())
                    else:
                        cli_sock.send("The user you want to unblock does not exist.".encode())

            # peer to peer messaging - start private chat
            elif word1 == "startprivate":
                if length > 2:
                    cli_sock.send("Incorrect command.".encode())
                elif length == 1:
                    cli_sock.send("Specify the user you want to start a private chat with.".encode())
                else:
                    private_chat_user = data.split(' ', 1)[1]
                    if private_chat_user == connection_list_dict[cli_sock]:
                        cli_sock.send("You cannot start a private chat with yourself.".encode())
                    elif private_chat_user not in credentials_dict:
                        cli_sock.send("The user does not exist.".encode())
                    elif (private_chat_user in name_list) and (
                            connection_list_dict[cli_sock] in blocked_user_dict[private_chat_user]):
                        cli_sock.send("You cannot start a private chat as the user has blocked you.".encode())
                    elif (private_chat_user in credentials_dict) and (private_chat_user not in name_list):
                        cli_sock.send("The user is offline.".encode())
                    elif (private_chat_user in name_list) and (connection_list_dict[cli_sock] not in blocked_user_dict[
                        private_chat_user]):
                        # send client address details for user to make a TCP connection
                        details = "IP " + str(address_dict[private_chat_user][0]) + ' ' + str(
                            address_dict[private_chat_user][1]) + ' ' + private_chat_user
                        cli_sock.send(details.encode())


            else:
                # for all other cases, command is not valid
                cli_sock.send("Incorrect command.".encode())

        except:
            break


# message broadcast function
def broadcast_user(cs_sock, msg):
    for client in connection_list:
        # message is not broadcast if user has blocked the sender
        if (client != cs_sock) and (
                connection_list_dict[client] not in blocked_user_dict[connection_list_dict[cs_sock]]) \
                and (connection_list_dict[cs_sock] not in blocked_user_dict[connection_list_dict[client]]):
            data = connection_list_dict[cs_sock] + '> ' + msg
            client.send(data.encode())
    count = 0
    for client in connection_list:
        if (client != cs_sock) and (connection_list_dict[cs_sock] in blocked_user_dict[connection_list_dict[client]]):
            count += 1
    if count > 0:
        cs_sock.send("Your message could not be delivered to some recipients.".encode())


# notifications broadcast function
def broadcast_notifications(cs_sock, msg):
    for client in connection_list:
        # broadcast notifications are not sent if user has blocked you
        if (client != cs_sock) and (
                connection_list_dict[client] not in blocked_user_dict[connection_list_dict[cs_sock]]) \
                and (connection_list_dict[cs_sock] not in blocked_user_dict[connection_list_dict[client]]):
            client.send(msg.encode())


if __name__ == "__main__":

    start_time = time.time()
    # list of sockets which are currently active
    connection_list = []
    # list of names which are currently online
    name_list = []

    # Create empty dictionaries:
    # dictionary for users blocked from logging in, key is username, value is blocked time
    login_blocked_users = dict()
    # dictionary for credentials, key is username, value is password
    credentials_dict = dict()
    # dictionary for connection list, key is socket, value is name
    connection_list_dict = dict()
    # dictionary for login time, key is name, value is login time and is updated to logout time if user logs out
    login_time_dict = dict()
    # dictionary for blocked users, key is name of user A, value is a set of users blocked by A
    blocked_user_dict = defaultdict(set)
    # dictionary for stored messages, key is name of the user who has received all the messages, value is a list of
    # all offline messages
    stored_messages_dict = defaultdict(list)
    # dictionary which stores timestamp of last command by the client socket, key is client socket and value is last
    # timestamp this is used for automatic logout in a separate thread
    last_command_time_dict = dict()
    # dictionary which stores IP address and port number for each client, key is username and value is a tuple
    # consisting of IP address and port number
    address_dict = dict()

    # takes all elements (numbers) from the text file into a list
    with open(file_name) as inputfile:
        for line in inputfile:
            line = line.strip()
            words = line.split(" ")
            credentials_dict[words[0]] = words[1]

    # TCP server socket
    ser_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ser_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # bind
    HOST = 'localhost'
    PORT = int(sys.argv[1])
    ser_sock.bind((HOST, PORT))

    # listen
    ser_sock.listen(10)
    # a confirmation message that chat server has started
    print('Chat server started on port : ' + str(PORT))

    # thread
    thread_ac = threading.Thread(target=accept_client)
    thread_ac.start()
