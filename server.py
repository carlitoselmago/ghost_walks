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
import sys
from scipy.optimize import minimize
import csv
import os
import itertools

# Configuration
LISTEN_IP = "0.0.0.0"  # Listen on all available network interfaces
LISTEN_PORT = 8888     # Must match the port used by the ESP32

SEND_IP = "192.168.4.255"  # Replace with the actual IP address of your ESP32
SEND_PORT = 8888

anchor_positions = {
    "1": (0, 0),
    "2": (5.6, 0.6),
    "3": (-1, 6),
    "4": (7, 5.5)
    # Add more anchors as needed
}

blocksize=0.2 # grid step in meters
presencemult=0.01 #values from each position will be multiplied by this value

# Argument parser setup
parser = argparse.ArgumentParser(description="UWB Positioning System")
parser.add_argument('-gui', action='store_true', help='Enable GUI using Pygame')
parser.add_argument('-store', action='store_true', help='Store range data as csv')
parser.add_argument('-load', action='store_true', help='Load range data as csv')
args = parser.parse_args()

offlinedatafile="offlinetest_data.csv"

def get_fixed_scale_factors(anchor_positions, display_height, rmse_bar_width, padding=50):
    min_x = min(anchor_positions.values(), key=lambda pos: pos[0])[0]
    min_y = min(anchor_positions.values(), key=lambda pos: pos[1])[1]
    max_x = max(anchor_positions.values(), key=lambda pos: pos[0])[0]
    max_y = max(anchor_positions.values(), key=lambda pos: pos[1])[1]

    scale_y = (display_height - 2 * padding) / (max_y - min_y)
    display_width = int((max_x - min_x) * scale_y + 2 * padding)

    return scale_y, display_width, min_x, min_y

if args.gui:
    import pygame
    pygame.init()
    display_height = 600
    rmse_bar_width = 100  # Width reserved for RMSE bar
    scale, display_width, min_x, min_y = get_fixed_scale_factors(anchor_positions, display_height, rmse_bar_width)
    screen = pygame.display.set_mode((display_width + rmse_bar_width, display_height))
    pygame.display.set_caption("UWB Positioning System")

DB = db(presencemult,blocksize)

x = 0
y = 0
rmse = 0

ranges = []
maxdistance = 20  # distance which if greater will be rejected
max_error = 3  # if rmse is greater than this, the values won't be accepted

for r, i in enumerate(anchor_positions):
    ranges.append(0.0)

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
GREY = (192, 192, 192)

def euclidean_distance(p1, p2):
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# Define the function to calculate the position
def calculate_position(distances, anchor_positions):
    # Extract anchor positions into a list
    anchors = [anchor_positions[str(i+1)] for i in range(len(distances))]
    
    # Initial guess for the tag position (could be improved)
    initial_guess = (0, 0)
    
    # Define the error function
    def error_function(tag_position):
        return sum((euclidean_distance(tag_position, anchor) - dist)**2 for anchor, dist in zip(anchors, distances))
    
    # Use minimize function to find the best position
    result = minimize(error_function, initial_guess, method='L-BFGS-B')
    
    # Extract the optimal position
    optimal_position = result.x
    
    # Calculate the error percentage
    total_error = error_function(optimal_position)
    error_percentage = (total_error / sum(distances)) * 100
    
    return optimal_position, error_percentage

def generateHeatMapMatrix(self, sizeX, sizeY):
    """
    Generate a heatmap matrix with normalized values.

    :param sizeX: Number of columns in the heatmap.
    :param sizeY: Number of rows in the heatmap.
    :return: A 2D numpy array representing the heatmap.
    """
    # Determine the boundaries based on anchor points
    min_x = min(anchor_positions.values(), key=lambda pos: pos[0])[0]
    min_y = min(anchor_positions.values(), key=lambda pos: pos[1])[1]
    max_x = max(anchor_positions.values(), key=lambda pos: pos[0])[0]
    max_y = max(anchor_positions.values(), key=lambda pos: pos[1])[1]
    
    # Calculate the step size in meters for each cell in the heatmap
    step_x = (max_x - min_x) / (sizeX - 1) if sizeX > 1 else 0
    step_y = (max_y - min_y) / (sizeY - 1) if sizeY > 1 else 0

    heatmap = np.zeros((sizeY, sizeX))

    for i in range(sizeY):
        for j in range(sizeX):
            x = min_x + j * step_x
            y = min_y + i * step_y
            heatmap[i, j] = self.getPresenceValue(x, y)

    return heatmap

def draw_rmse_bar(screen, rmse, rmse_bar_width):
    bar_height = int((rmse / 5.0) * (display_height - 100))  # Scale RMSE to bar height (max 500 pixels)
    bar_width = rmse_bar_width - 20
    bar_x = display_width - rmse_bar_width + 80  # Position on the right
    bar_y = 50 + ((display_height - 100) - bar_height)  # Position the bar from the top

    # Draw the bar background
    pygame.draw.rect(screen, WHITE, (bar_x, 50, bar_width, display_height - 100))

    # Draw the RMSE bar
    pygame.draw.rect(screen, BLUE, (bar_x, bar_y, bar_width, bar_height))

    # Draw the RMSE text
    font = pygame.font.Font(None, 36)
    text = font.render(f"RMSE: {rmse:.2f}", True, BLACK)
    screen.blit(text, (bar_x - 60, 10))

def draw_grid(active_anchors, scale, min_x, min_y):
    for anchor_id, (ax_pos, ay_pos) in anchor_positions.items():
        px_pos = int((ax_pos - min_x) * scale + 50)
        py_pos = int(display_height - ((ay_pos - min_y) * scale + 50))
        color = RED if anchor_id in active_anchors else GREY
        pygame.draw.circle(screen, color, (px_pos, py_pos), 5)
        font = pygame.font.Font(None, 36)
        text = font.render(f"A{anchor_id}", True, BLACK)
        screen.blit(text, (px_pos - 15, py_pos - 25))

    # Draw the RMSE bar
    draw_rmse_bar(screen, rmse, rmse_bar_width)

def draw_heatmap(matrix, size, scale, min_x, min_y):
    step_x = (display_width - rmse_bar_width) / size
    step_y = display_height / size
    for i in range(size):
        for j in range(size):
            try:
               
                value = float(matrix[i][j])  # Ensure the value is a float
                # Calculate the color based on the value
                red = int(value * 255)
                green = int((1 - value) * 255)
                color = (red, green, 0)
                px_pos = int((i * step_x) + 50)
                py_pos = int(display_height - ((j * step_y) + 50))
                pygame.draw.rect(screen, color, (px_pos, py_pos, step_x, step_y))
            except:
                pass

def osc_handler(addr, *msg):
    global ranges, x, y, rmse, max_error
    # messages by index anchor ranges
    
    if args.store:
        #### CSV for testing remove in live

        # Define the CSV file path
        csv_file = offlinedatafile
        
        # Check if the CSV file exists, and create it with headers if it doesn't
        if not os.path.isfile(csv_file):
            with open(csv_file, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Address'] + [f'Message_{i}' for i in range(len(msg))])
        
        # Append the new msg data to the CSV file
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([addr] + list(msg))

        #### END CSV

    for i, r in enumerate(anchor_positions):
        newv = msg[i]
        if newv > 0 and newv < maxdistance:
            ranges[i] = newv

    position, error_percentage = calculate_position(ranges[0:len(anchor_positions)], anchor_positions)
    rmse = error_percentage / 10
    print(position, rmse)
    if rmse < max_error:
        x = position[0]
        y = position[1]
        print("msg[0],x,y", msg[0], x, y)
        DB.insertPos(msg[0], x, y)

def load_csv():
    # Define the CSV file path
    csv_file = offlinedatafile
    
    # Check if the CSV file exists
    if not os.path.isfile(csv_file):
        print(f"File {csv_file} does not exist.")
        return

    # Read the contents of the CSV file
    with open(csv_file, mode='r') as file:
        reader = csv.reader(file)
        rows = list(reader)
        
        # Remove header if present
        if rows and rows[0][0] == 'Address':
            rows = rows[1:]
        
        # Loop through the rows indefinitely
        for row in itertools.cycle(rows):
            time.sleep(0.1)
            # Assuming the first column is the address and the rest are the messages
            addr = row[0]
            msg = [float(value) for value in row[1:]]
            osc_handler(addr, *msg)

if args.load: #if loading stored csv data
    server_thread = threading.Thread(target=load_csv)
    server_thread.start()
else:
    disp = dispatcher.Dispatcher()
    disp.map("/tag1", osc_handler)

    server = osc_server.ThreadingOSCUDPServer((LISTEN_IP, LISTEN_PORT), disp)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

if args.gui:
    heatmap_cell_size = 50  # Adjust this value to change the density of the heatmap
    sizeX = (display_width - rmse_bar_width) // heatmap_cell_size
    sizeY = display_height // heatmap_cell_size
    heatmap_matrix = DB.generateHeatMapMatrix(anchor_positions,sizeY, sizeX)

try:
    while True:
        if args.gui:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt

            screen.fill(WHITE)  # Fill the screen with white before drawing

            draw_heatmap(heatmap_matrix, sizeX, scale, min_x, min_y)  # Draw the heatmap first

            active_anchors = anchor_positions.keys()
            draw_grid(active_anchors, scale, min_x, min_y)  # Draw the grid and anchors

            tag_px = int((x - min_x) * scale + 50)
            tag_py = int(display_height - ((y - min_y) * scale + 50))
            pygame.draw.circle(screen, BLUE, (tag_px, tag_py), 5)

            font = pygame.font.Font(None, 36)
            text = font.render("Tag", True, BLACK)
            screen.blit(text, (tag_px + 10, tag_py - 15))

            pygame.display.flip()

            # You might add a small sleep here to prevent maxing out CPU usage
            time.sleep(0.01)

except KeyboardInterrupt:
    print("\nServer stopped")
finally:
    server.shutdown()
    server.server_close()
    if args.gui:
        pygame.quit()
