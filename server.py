import socket
import time
import json
import struct
import numpy as np
import argparse
from dbclient import db
from pythonosc import dispatcher
from pythonosc import osc_server
import threading

# Configuration
LISTEN_IP = "0.0.0.0"  # Listen on all available network interfaces
LISTEN_PORT = 8888     # Must match the port used by the ESP32

SEND_IP = "192.168.4.255"  # Replace with the actual IP address of your ESP32
SEND_PORT = 8888

# Argument parser setup
parser = argparse.ArgumentParser(description="UWB Positioning System")
parser.add_argument('-gui', action='store_true', help='Enable GUI using Pygame')
args = parser.parse_args()

if args.gui:
    import pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("UWB Positioning System")

DB = db()

"""
# Create UDP sockets
listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listen_sock.bind((LISTEN_UDP_IP, LISTEN_UDP_PORT))
listen_sock.setblocking(False)  # Set to non-blocking mode

send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
"""

anchor_positions = {
    "1": (0, 0),
    "2": (4.6, 0.6),
    "3": (-1, 6),
    "4": (6, 5.5)
    #"3": (5, 3),
    # Add more anchors as needed
}

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
GREY = (192, 192, 192)

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

"""
def send_message_to_esp32(message, address):
    try:
        message_bytes = struct.pack('f', message) if isinstance(message, float) else str(message).encode('utf-8')
        send_sock.sendto(message_bytes, (address, SEND_UDP_PORT))
        #print(f"Sent message: {message} to {address}:{SEND_UDP_PORT}")
    except PermissionError as e:
        print(f"PermissionError: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
"""
def get_fixed_scale_factors(anchor_positions, canvas_size=(800, 600), padding=50):
    min_x = min(anchor_positions.values(), key=lambda pos: pos[0])[0]
    min_y = min(anchor_positions.values(), key=lambda pos: pos[1])[1]
    max_x = max(anchor_positions.values(), key=lambda pos: pos[0])[0]
    max_y = max(anchor_positions.values(), key=lambda pos: pos[1])[1]

    scale_x = (canvas_size[0] - 2 * padding) / (max_x - min_x)
    scale_y = (canvas_size[1] - 2 * padding) / (max_y - min_y)
    
    return min(scale_x, scale_y), min_x, min_y

def draw_rmse_bar(screen, rmse):
    bar_height = int((rmse / 5.0) * 500)  # Scale RMSE to bar height (max 500 pixels)
    bar_width = 30
    bar_x = 750  # Position on the right
    bar_y = 50 + (500 - bar_height)  # Position the bar from the top

    # Draw the bar background
    pygame.draw.rect(screen, WHITE, (bar_x, 50, bar_width, 500))

    # Draw the RMSE bar
    pygame.draw.rect(screen, BLUE, (bar_x, bar_y, bar_width, bar_height))

    # Draw the RMSE text
    font = pygame.font.Font(None, 36)
    text = font.render(f"RMSE: {rmse:.2f}", True, BLACK)
    screen.blit(text, (bar_x - 100, 10))


def draw_grid(active_anchors, scale, min_x, min_y):
    screen.fill(WHITE)
    for anchor_id, (ax_pos, ay_pos) in anchor_positions.items():
        px_pos = int((ax_pos - min_x) * scale + 50)
        py_pos = int(600 - ((ay_pos - min_y) * scale + 50))
        color = RED if anchor_id in active_anchors else GREY
        pygame.draw.circle(screen, color, (px_pos, py_pos), 5)
        font = pygame.font.Font(None, 36)
        text = font.render(f"A{anchor_id}", True, BLACK)
        screen.blit(text, (px_pos - 15, py_pos - 25))

    # Draw the RMSE bar
    draw_rmse_bar(screen, rmse)

def draw_heatmap(heatmap_data, scale, min_x, min_y):
    max_visits = max(heatmap_data.values(), default=1)
    for (x, y), visits in heatmap_data.items():
        intensity = int((visits / max_visits) * 255)
        color = (255, 255 - intensity, 255 - intensity)
        px_pos = int((x - min_x) * scale + 50)
        py_pos = int(600 - ((y - min_y) * scale + 50))
        pygame.draw.circle(screen, color, (px_pos, py_pos), 10)

x=0
y=0
rmse=0

def osc_handler(addr, *msg):
    global x, y,rmse
    #messages by index: x,y,error
    
    #msg = json.loads(args[0])
    #print(msg)

    tagid =addr# msg["tagid"]
    x = msg[0]#msg["x"]
    y = msg[1]#msg["y"]
    rmse=msg[2]
    print(f"Position: X={x:.2f}, Y={y:.2f} , E:{rmse:.2f}")

    if x != 0 and y != 0:
        #DB.insertPos(tagid, x, y)
        coord = (round(x, 1), round(y, 1))

    
    

disp = dispatcher.Dispatcher()
disp.map("/tag1", osc_handler)

server = osc_server.ThreadingOSCUDPServer((LISTEN_IP, LISTEN_PORT), disp)
server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()

scale, min_x, min_y = get_fixed_scale_factors(anchor_positions)

try:
    while True:
        if args.gui:
            #pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
            
            #norm = DB.getNormValue(x, y)
            #response_message = norm
            #send_message_to_esp32(response_message, addr[0])

    
            active_anchors = anchor_positions.keys()
            draw_grid(active_anchors, scale, min_x, min_y)

            tag_px = int((x - min_x) * scale + 50)
            tag_py = int(600 - ((y - min_y) * scale + 50))
            pygame.draw.circle(screen, BLUE, (tag_px, tag_py), 5)

            font = pygame.font.Font(None, 36)
            text = font.render("Tag", True, BLACK)
            screen.blit(text, (tag_px + 10, tag_py - 15))

            pygame.display.flip()

            # You might add a small sleep here to prevent maxing out CPU usage
            #time.sleep(0.01)

except KeyboardInterrupt:
    print("\nServer stopped")
finally:
    server.shutdown()
    server.server_close()
    if args.gui:
        pygame.quit()


"""

try:
    #heatmap_data = {}
    scale, min_x, min_y = get_fixed_scale_factors(anchor_positions)

    while True:
        if args.gui:
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
        
        try:
            while True:
                data, addr = listen_sock.recvfrom(1024)  # Buffer size is 1024 bytes
                msg = json.loads(data.decode('utf-8').replace("'", "\""))

                print(msg)
                #sys.exit()

                #anchors = msg["anchors"]
                tagid = msg["tagid"]
                
                #try:
                #    x, y = calculate_position(msg, anchor_positions)
                #except Exception as e:
                #    print("couldn't calculate position:", e)
                #    x = -1.0
                #    y = -1.0
                
                x=msg["x"]
                y=msg["y"]
                #if x > 0 and y > 0:
                print(f"Position: X={x:.2f}, Y={y:.2f}")
                
                # Save to db and update heatmap data
                
                if x != 0 and y != 0:
                    DB.insertPos(tagid, x, y)
                    coord = (round(x, 1), round(y, 1))  # rounding to the nearest 0.1 for heatmap purposes
                    #heatmap_data[coord] = heatmap_data.get(coord, 0) + 1

                norm = DB.getNormValue(x, y)
                response_message = norm
                #print("response msg", response_message) 
                send_message_to_esp32(response_message, addr[0])

                if args.gui:
                    active_anchors = anchor_positions.keys()#anchors.keys()
                    draw_grid(active_anchors, scale, min_x, min_y)
                    #draw_heatmap(heatmap_data, scale, min_x, min_y)

                    tag_px = int((x - min_x) * scale + 50)
                    tag_py = int(600 - ((y - min_y) * scale + 50))
                    pygame.draw.circle(screen, BLUE, (tag_px, tag_py), 5)

                    font = pygame.font.Font(None, 36)
                    text = font.render("Tag", True, BLACK)
                    screen.blit(text, (tag_px + 10, tag_py - 15))

                    pygame.display.flip()
                
        except BlockingIOError:
            pass  # No data available, continue loop
        
        #time.sleep(0.01)  # Slightly delay the loop to avoid 100% CPU usage

except KeyboardInterrupt:
    print("\nServer stopped")
finally:
    listen_sock.close()
    send_sock.close()
    if args.gui:
        pygame.quit()

"""