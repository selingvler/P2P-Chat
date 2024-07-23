import base64
import json
import logging
import math
import socket
import threading
import time
from datetime import datetime

import pyDes

dictionary = {}

logging.basicConfig(filename='logging.log', level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
broadcast_address = "172.20.10.15"

def Service_Announcer():

    username = input(f"Enter your username: ")

    username_data = {"username": username}
    username_message = json.dumps(username_data).encode()

    udpclient_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udpclient_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        try:
            udpclient_socket.sendto(username_message,
                                    (broadcast_address, 6000))
            #print(f"Sent broadcast announcement: {username_data}")
            time.sleep(8)  # Announce every 8 seconds
        except Exception as e:
            print(f"Error sending broadcast message: {e}")
            break

def Peer_Discovery():
    udpserver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udpserver_socket.bind((broadcast_address, 6000))

    while True:
        try:
            data, address = udpserver_socket.recvfrom(1024)
            unformatted_timestamp = time.time()
            timestamp = datetime.fromtimestamp(unformatted_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            received_data = json.loads(data.decode())
            # print(f"Received announcement from {address[0]}: {received_data}")
            if dictionary.__contains__(address[0]):
                if dictionary[address[0]][1] == received_data:
                    dictionary[address[0]][1] = timestamp

            else:
                dictionary[address[0]] = [received_data, timestamp]
                print(f"{received_data['username']} is online")

        except:
            pass
            break

def Chat_Initiator():
    p = 23
    g = 5

    port = 6001

    while True:
        selection = input(
            f"Would you like to view online users, initiate chat, or view chat history(Enter Users, Chat or History): ")

        if selection != "quit":
            if selection == "Users":
                current_unformatted_timestamp = time.time()

                active = []

                for key, value in dictionary.items():
                    timestamp_datetime = datetime.strptime(value[1], '%Y-%m-%d %H:%M:%S')
                    timestamp_float = time.mktime(timestamp_datetime.timetuple())

                    time_difference = current_unformatted_timestamp - timestamp_float

                    if time_difference <= 900:
                        if time_difference < 10:
                            active.append(f"{str(dictionary[key][0]['username'])}" + " Online")
                        else:
                            active.append(f"{str(dictionary[key][0]['username'])}" + " Away")

                print(active)

            elif selection == "Chat":
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    user_selection = input(f"Who do you want to chat with: ")
                    for key, value in dictionary.items():
                        if 'username' in value[0] and user_selection == value[0]['username']:
                            ip_address = key
                            break

                    resolved_ip_address = socket.gethostbyname(ip_address)


                    sock.connect((resolved_ip_address, port))


                    type = input(f"Select type of chat you want to view(Secure or Unsecure): ")

                    if type == "Secure":
                        b = int(input("Enter a number: "))

                        a = int(input("Enter another number: "))
                        A = math.pow(g, a) % p

                        key = math.pow(A, b) % p

                        sending_dict = {"b": b, "A": A}
                        sending_json = json.dumps(sending_dict).encode()
                        sock.send(sending_json)


                        message = input("Enter your message: ")
                        encrypted_message = pyDes.triple_des(str(key).ljust(24)).encrypt(message, padmode=2)
                        encoded_encrypted_message = base64.b64encode(encrypted_message).decode()
                        encrypted_dict = {"encrypted_message": encoded_encrypted_message}
                        encrypted_json = json.dumps(encrypted_dict)
                        sock.send(encrypted_json.encode())
                        print("Message sent")

                        logging.info(f"{user_selection} {message} RECEIVED")

                    elif type == "Unsecure":

                        message = input("Enter your message: ")

                        message_dict = {"unencrypted_message": message}
                        message_json = json.dumps(message_dict)
                        sock.send(message_json.encode())
                        print("Message sent")

                        logging.info(f"{user_selection} {message} RECEIVED")



                except socket.error as e:
                    print("Error: Connection with the server could not be established:", e)
                finally:
                    sock.close()

            elif selection == "History":
                with open('logging.log', 'r') as f:
                    for line in f:
                        print(line, end='')
        else:
            break

def Chat_Responder():
    p = 23
    g = 5

    port = 6001

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', port))

    sock.listen(1)

    try:
        while True:
            conn, addr = sock.accept()

            message_json = conn.recv(1024).decode()
            message_dict = json.loads(message_json)
            #print(message_dict)

            if len(message_dict) == 2:


                b = int(message_dict["b"])

                A = int(message_dict["A"])

                key = math.pow(A, b) % p


                message_json = conn.recv(1024).decode()
                message_dict = json.loads(message_json)
                if 'encrypted_message' in message_dict:

                    encoded_encrypted_message = message_dict.get("encrypted_message")
                    encrypted_textMessage = base64.b64decode(encoded_encrypted_message)
                    message = pyDes.triple_des(str(key).ljust(24)).decrypt(encrypted_textMessage, padmode=2)

                    if addr[0] in dictionary:
                        user_selection = dictionary[addr[0]][0]
                        logging.info(f"{user_selection} {message} SENT")

                    print(f"{user_selection}" + message.decode("utf-8"))

            elif 'encrypted_message' in message_dict:

                encoded_encrypted_message = message_dict.get("encrypted_message")
                encrypted_textMessage = base64.b64decode(encoded_encrypted_message)
                message = pyDes.triple_des(str(key).ljust(24)).decrypt(encrypted_textMessage, padmode=2)

                if addr[0] in dictionary:
                    user_selection = dictionary[addr[0]][0]
                    logging.info(f"{user_selection} {message} SENT")

                print(f"{user_selection}" + message.decode("utf-8"))

            elif 'unencrypted_message' in message_dict:
                message = message_dict["unencrypted_message"]

                if addr[0] in dictionary:
                    user_selection = dictionary[addr[0]][0]
                    logging.info(f"{user_selection} {message} SENT")

                print(f"{user_selection} :" + message)


    except socket.timeout:
        print("Connection timed out")
    finally:
        conn.close()


announcer = threading.Thread(target=Service_Announcer)
discovery = threading.Thread(target=Peer_Discovery)
initiator = threading.Thread(target=Chat_Initiator)
responder = threading.Thread(target=Chat_Responder)

announcer.start()
discovery.start()
initiator.start()
responder.start()
