import socket
import time
import json
import struct
import numpy as np
import pygame

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
    "2": (5, 0),
    "3": (0, 3),
    "4":(5,3)
    # Add more anchors as needed
}

# Pygame setup
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("UWB Positioning System")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)

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

def draw_grid():
    screen.fill(WHITE)
    for anchor_id, (ax_pos, ay_pos) in anchor_positions.items():
        px_pos, py_pos = int(ax_pos * 100 + 50), int(600 - (ay_pos * 100 + 50))
        pygame.draw.circle(screen, RED, (px_pos, py_pos), 5)
        font = pygame.font.Font(None, 36)
        text = font.render(f"A{anchor_id}", True, BLACK)
        screen.blit(text, (px_pos - 15, py_pos - 25))

try:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt
        
        data, addr = listen_sock.recvfrom(1024)  # Buffer size is 1024 bytes
        msg = json.loads(data.decode('utf-8').replace("'", "\""))

        anchors = msg["anchors"]
        tagid = msg["tagid"]
        x, y = calculate_position(msg, anchor_positions)
        print(f"Position: X={roundDec(x)}, Y={roundDec(y)}")

        draw_grid()
        tag_px, tag_py = int(x * 100 + 50), int(600 - (y * 100 + 50))
        pygame.draw.circle(screen, BLUE, (tag_px, tag_py), 5)
        font = pygame.font.Font(None, 36)
        text = font.render("Tag", True, BLACK)
        screen.blit(text, (tag_px + 10, tag_py - 15))

        pygame.display.flip()
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nServer stopped")
finally:
    listen_sock.close()
    send_sock.close()
    pygame.quit()
