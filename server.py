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

anchor_positions = {
    "1": (0, 0),
    "2": (5.6, 0.6),
    "3": (-1, 6),
    "4": (7, 5.5)
    # Add more anchors as needed
}

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

def draw_heatmap(matrix, size, scale, min_x, min_y):
    margin = DB.marginpos * 800
    step = int(800 / size)
    for i in range(size):
        if i<10:
            for j in range(size):
                if j<10:
                    value = matrix[i][j]
                    color_intensity = int(value * 255)
                    color = (color_intensity, 0, 255 - color_intensity)
                    px_pos = int((i * step) + 50)
                    py_pos = int(600 - ((j * step) + 50))
                    pygame.draw.rect(screen, color, (px_pos, py_pos, step, step))

x = 0
y = 0
rmse = 0

def osc_handler(addr, *msg):
    global ranges, x, y, rmse, max_error
    # messages by index anchor ranges
    
    #### CSV for testing remove in live

    # Define the CSV file path
    csv_file = 'data.csv'
    
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
    print(position, error_percentage)
    rmse = error_percentage / 10
    if rmse < max_error:
        x = position[0]
        y = position[1]

disp = dispatcher.Dispatcher()
disp.map("/tag1", osc_handler)

server = osc_server.ThreadingOSCUDPServer((LISTEN_IP, LISTEN_PORT), disp)
server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()

scale, min_x, min_y = get_fixed_scale_factors(anchor_positions)
heatmap_matrix = DB.generateHeatMapMatrix(10)

try:
    while True:
        if args.gui:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt

            screen.fill(WHITE)  # Fill the screen with white before drawing

            draw_heatmap(heatmap_matrix, 10, scale, min_x, min_y)  # Draw the heatmap first

            active_anchors = anchor_positions.keys()
            draw_grid(active_anchors, scale, min_x, min_y)  # Draw the grid and anchors

            tag_px = int((x - min_x) * scale + 50)
            tag_py = int(600 - ((y - min_y) * scale + 50))
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
