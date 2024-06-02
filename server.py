import socket
import time
import json
import struct
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Configuration
LISTEN_UDP_IP = "0.0.0.0"  # Listen on all available network interfaces
LISTEN_UDP_PORT = 8888     # Must match the port used by the ESP32

SEND_UDP_IP = "192.168.1.255"  # Replace with the actual IP address of your ESP32
SEND_UDP_PORT = 8888

# Create UDP sockets
listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listen_sock.bind((LISTEN_UDP_IP, LISTEN_UDP_PORT))

send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

anchor_positions = {
    "1": (0, 0),
    "2": (2.5, 0),
    "3": (0, 2),
    # Add more anchors as needed
}

def calculate_position(data, anchor_positions):
    distances = data['anchors']
    
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
    
    A = np.array(A)
    B = np.array(B)
    
    pos = np.linalg.lstsq(A, B, rcond=None)[0]
    
    return pos[0][0], pos[1][0]

def update(frame):
    try:
        data, addr = listen_sock.recvfrom(1024)  # Buffer size is 1024 bytes
        msg = json.loads(data.decode('utf-8').replace("'", "\""))

        x, y = calculate_position(msg, anchor_positions)
        
        ax.clear()
        
        # Plot anchors
        for anchor_id, (ax_pos, ay_pos) in anchor_positions.items():
            ax.plot(ax_pos, ay_pos, 'ro')
            ax.text(ax_pos, ay_pos, f"Anchor {anchor_id}", fontsize=12, ha='right')
        
        # Plot tag
        ax.plot(x, y, 'bo')
        ax.text(x, y, 'Tag', fontsize=12, ha='left')
        
        # Set plot limits
        ax.set_xlim(-1, 10)
        ax.set_ylim(-1, 10)
        ax.set_title(f"Position: X={x:.2f}, Y={y:.2f}")

    except Exception as e:
        print(f"An error occurred: {e}")

# Set up plot
fig, ax = plt.subplots()

# Create animation
ani = FuncAnimation(fig, update, interval=200)

plt.show()

# Close sockets on exit
def close_sockets():
    listen_sock.close()
    send_sock.close()

try:
    while True:
        time.sleep(0.01)  # Keep the script running
except KeyboardInterrupt:
    print("\nServer stopped")
finally:
    close_sockets()
