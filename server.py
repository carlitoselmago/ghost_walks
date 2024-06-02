
import socket
import time
import json
from dbclient import db
import struct
import numpy as np

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

anchor_positions = {
    "1": (0, 0),
    "2": (3, 0),
    "3": (0, 3),
}

def calculate_position(data, anchor_positions):
    # Parse JSON data
    
    distances = data['anchors']
    
    # Prepare matrices for multilateration
    A = []
    B = []
    
    anchors = list(distances.keys())
    
    for i in range(1, len(anchors)):
        anchor1_id = anchors[0]
        anchor2_id = anchors[i]
        
        x1, y1 = anchor_positions[anchor1_id]
        x2, y2 = anchor_positions[anchor2_id]
        
        d1 = distances[anchor1_id]
        d2 = distances[anchor2_id]
        
        A.append([2 * (x2 - x1), 2 * (y2 - y1)])
        B.append([d1**2 - d2**2 - x1**2 + x2**2 - y1**2 + y2**2])
    
    # Convert lists to numpy arrays
    A = np.array(A)
    B = np.array(B)
    
    # Solve the linear equation system A * [x, y] = B
    pos = np.linalg.lstsq(A, B, rcond=None)[0]
    
    return pos[0][0], pos[1][0]

def roundDec(value,dec=2):
    return str(round(value, dec))

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
        print(data)
        #print(f"Received message from {addr}: {data.decode('utf-8')}")
        msg=json.loads(data.decode('utf-8').replace("\'", "\""))
        #print(msg)

        anchors=msg["anchors"]

        tagid=msg["tagid"]
        x, y = calculate_position(msg, anchor_positions)
        print(f"Position: X={roundDec(x)}, Y={roundDec(y)}")
        """
        #x=0.1
        #y=0.1
        DB.insertPos(tagid,x,y)

        norm=DB.getNormValue(x,y)
        
        """
        norm=0.5
        response_message = norm
        #send_message_to_esp32(response_message,addr[0])

        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nServer stopped")
finally:
    listen_sock.close()
    send_sock.close()


