
import socket
import time
import json
from dbclient import db
import struct

# Configuration
LISTEN_UDP_IP = "0.0.0.0"  # Listen on all available network interfaces
LISTEN_UDP_PORT = 8888     # Must match the port used by the ESP32

SEND_UDP_IP = "192.168.1.255"  # Replace with the actual IP address of your ESP32
SEND_UDP_PORT = 8888

# Create UDP sockets
listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listen_sock.bind((LISTEN_UDP_IP, LISTEN_UDP_PORT))

send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

DB=db()

def send_message_to_esp32(message,address):
    try:
        message_bytes = struct.pack('f', message) if isinstance(message, float) else str(message).encode('utf-8')
        send_sock.sendto(message_bytes, (address, SEND_UDP_PORT))
        print(f"Sent message: {message} to {address}:{SEND_UDP_PORT}")
    except PermissionError as e:
        print(f"PermissionError: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


try:
    while True:
        data, addr = listen_sock.recvfrom(1024)  # Buffer size is 1024 bytes
        #print(f"Received message from {addr}: {data.decode('utf-8')}")
        msg=json.loads(data.decode('utf-8').replace("\'", "\""))
        #print(msg)
        x=msg["x"]
        y=msg["y"]
        tagid=msg["tagid"]

        #x=0.1
        #y=0.1
        DB.insertPos(tagid,x,y)

        norm=DB.getNormValue(x,y)

        response_message = norm
        send_message_to_esp32(response_message,addr[0])

        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nServer stopped")
finally:
    listen_sock.close()
    send_sock.close()

