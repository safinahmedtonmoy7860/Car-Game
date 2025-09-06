from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import math
import random
import time

# Game state
game_start_time = 0
day_mode = 1  # 1=day, 2=evening, 3=night
headlights_on = False
car_x, car_z = 0.0, 0.0
car_angle = 0.0
current_speed = 0.0
max_speed = 8.0  # Reduced maximum speed

acceleration = 0.3  # Reduced acceleration
deceleration = 0.5  # Reduced deceleration
brake_deceleration = 0.8  # Reduced brake deceleration
car_width = 1.5 * 0.81
car_length = 3.0 * 0.81
car_height = 1.2 * 0.81
steering_speed = 3  # Reduced steering speed
wheel_rotation_angle = 0.0
first_person_view = False
game_active = True
score = 0
time_of_day = 6 * 60  # Start at 6:00 AM (minutes)
obstacles = []
next_obstacle_time = 0
game_over_time = 0

# NEW: Jump mechanics
car_jump_height = 0.0
car_jump_velocity = 0.0
is_jumping = False
jump_power = 5.0  # Further reduced for lower jump
gravity = 0.8  # Increased gravity for faster descent

# Camera state
camera_angle_horizontal = 0.0
camera_angle_vertical = 20.0
camera_distance = 7.0
car_height_offset = 3.0
camera_rotation_speed = 3.9
camera_vertical_speed = 2.0
min_vertical_angle = 0.0
max_vertical_angle = 85.0

# Road and scene size
road_width = 10
scene_start = -5
scene_end = 30000
building_spacing = 30
tree_spacing = 25

# Global storage for building and tree heights
building_heights = {}
tree_heights = {}

# Keyboard state
keys = {
    b'w': False,
    b's': False,
    b'a': False,
    b'd': False,
    b' ': False,
    b'r': False,
    b'l': False,
    b'1': False,
    b'2': False,
    b'3': False,
    b'g': False,
    b'h': False,
    b'j': False,  # NEW: Jump key
    'left': False,
    'right': False,
    'up': False,
    'down': False,
    b'q': False,
    b'e': False
}

class Obstacle:
    def __init__(self, z_pos):
        self.type = random.choice(['round', 'cube'])  # Only round and cube obstacles
        self.z = z_pos
        self.x = random.uniform(-road_width/2 + 1, road_width/2 - 1)
        if self.type == 'round':
            self.color = (0.2, 0.8, 0.2)  # Green for round (good)
        else:
            self.color = (0.8, 0.2, 0.2)  # Red for cube (bad)
        self.scored = False
        self.hit = False  # NEW: Track if obstacle was hit

def init():
    glClearColor(0.5, 0.8, 1.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, 800 / 600, 0.1, 100000.0)
    glMatrixMode(GL_MODELVIEW)

def reset_game():
    global car_x, car_z, car_angle, current_speed, camera_angle_horizontal, camera_angle_vertical, headlights_on, first_person_view, game_active, score, obstacles
    global game_start_time, obstacles, next_obstacle_time, car_jump_height, car_jump_velocity, is_jumping
    game_start_time = time.time()
    obstacles = []
    next_obstacle_time = 0
    car_x, car_z = 0.0, 0.0
    car_angle = 0.0
    current_speed = 0.0
    camera_angle_horizontal = 0.0
    camera_angle_vertical = 20.0
    headlights_on = False
    first_person_view = False
    game_active = True
    score = 0
    obstacles = []
    # NEW: Reset jump mechanics
    car_jump_height = 0.0
    car_jump_velocity = 0.0
    is_jumping = False

def check_collision(obstacle):
    # NEW: Enhanced collision detection with jump consideration
    car_radius = max(car_width, car_length)/2 * 0.8
    obs_radius = 1.0
    
    # Check if car is high enough to jump over obstacle
    if is_jumping and car_jump_height > 0.5:  # Lower jump height to clear obstacles
        return False
    
    dx = car_x - obstacle.x
    dz = car_z - obstacle.z
    return math.sqrt(dx**2 + dz**2) < car_radius + obs_radius

def draw_obstacle(obstacle):
    glPushMatrix()
    glTranslatef(obstacle.x, 0, obstacle.z)
    glColor3f(*obstacle.color)
    
    if obstacle.type == 'round':
        # Round obstacle (good - gives points and speed boost)
        glutSolidSphere(0.8, 16, 16)
    elif obstacle.type == 'cube':
        # Cube obstacle (bad - takes points and reduces speed)
        glutSolidCube(1.2)
    
    glPopMatrix()

def draw_ground():
    if day_mode == 1:
        glColor3f(0.3, 0.8, 0.3)
    elif day_mode == 2:
        glColor3f(0.2, 0.5, 0.2)
    else:
        glColor3f(0.05, 0.15, 0.05)
    
    glBegin(GL_QUADS)
    glVertex3f(-50, 0, scene_start)
    glVertex3f(-50, 0, scene_end)
    glVertex3f(50, 0, scene_end)
    glVertex3f(50, 0, scene_start)
    glEnd()

    if day_mode == 1:
        glColor3f(0.2, 0.2, 0.2)
    elif day_mode == 2:
        glColor3f(0.15, 0.15, 0.15)
    else:
        glColor3f(0.08, 0.08, 0.08)
    
    glBegin(GL_QUADS)
    glVertex3f(-road_width / 2, 0.02, scene_start)
    glVertex3f(-road_width / 2, 0.02, scene_end)
    glVertex3f(road_width / 2, 0.02, scene_end)
    glVertex3f(road_width / 2, 0.02, scene_start)
    glEnd()

    lane_width = 0.2
    lane_length = 2.0
    gap_length = 4.0
    z = scene_start
    
    if day_mode == 1:
        glColor3f(1.0, 1.0, 1.0)
    elif day_mode == 2:
        glColor3f(0.8, 0.8, 0.8)
    else:
        glColor3f(0.4, 0.4, 0.4)
    
    while z < scene_end:
        glBegin(GL_QUADS)
        glVertex3f(-lane_width/2, 0.03, z)
        glVertex3f(-lane_width/2, 0.03, z + lane_length)
        glVertex3f(lane_width/2, 0.03, z + lane_length)
        glVertex3f(lane_width/2, 0.03, z)
        glEnd()
        z += lane_length + gap_length

def draw_building(x, z, scale_x, scale_y, scale_z, color):
    glPushMatrix()
    glTranslatef(x, scale_y / 2, z)
    if day_mode == 2:
        color = (color[0]*0.6, color[1]*0.6, color[2]*0.6)
    elif day_mode == 3:
        color = (color[0]*0.3, color[1]*0.3, color[2]*0.3)
    glColor3f(*color)
    glScalef(scale_x, scale_y, scale_z)
    glutSolidCube(1)
    glPopMatrix()

def draw_tree(x, z, trunk_height, leaf_radius):
    glPushMatrix()
    glTranslatef(x, trunk_height / 2, z)
    if day_mode == 1:
        glColor3f(0.5, 0.35, 0.05)
    elif day_mode == 2:
        glColor3f(0.35, 0.25, 0.04)
    else:
        glColor3f(0.2, 0.15, 0.03)
    
    glPushMatrix()
    glScalef(0.3, trunk_height, 0.3)
    glutSolidCube(1)
    glPopMatrix()
    
    if day_mode == 1:
        glColor3f(0.1, 0.6, 0.1)
    elif day_mode == 2:
        glColor3f(0.07, 0.42, 0.07)
    else:
        glColor3f(0.04, 0.24, 0.04)
    
    glTranslatef(0, trunk_height, 0)
    glutSolidSphere(leaf_radius, 10, 10)
    glPopMatrix()

def draw_scenery():
    global building_heights, tree_heights
    
    # Limit buildings to prevent OpenGL errors
    max_buildings = 30
    building_count = 0
    
    for i in range(scene_start, scene_end + building_spacing, building_spacing):
        if building_count >= max_buildings:
            break
        z = i
        if z not in building_heights:
            building_heights[z] = random.uniform(3, 10)
        height = building_heights[z]
        draw_building(-road_width / 2 - 5, z, 3, height, 3, (0.7, 0.7, 0.7))
        building_count += 1

    building_count = 0
    for i in range(scene_start + building_spacing // 2, scene_end + building_spacing, building_spacing):
        if building_count >= max_buildings:
            break
        z = i
        if z not in building_heights:
            building_heights[z] = random.uniform(4, 12)
        height = building_heights[z]
        draw_building(road_width / 2 + 5, z, 2, height, 2, (0.6, 0.6, 0.6))
        building_count += 1

    # Limit trees to prevent OpenGL errors
    max_trees = 20
    tree_count = 0
    
    for i in range(scene_start, scene_end + tree_spacing, tree_spacing):
        if tree_count >= max_trees:
            break
        z = i
        if z not in tree_heights:
            tree_heights[z] = (random.uniform(2, 5), random.uniform(0.8, 1.5))
        trunk_height, leaf_radius = tree_heights[z]
        draw_tree(-road_width / 2 - 10, z, trunk_height, leaf_radius)
        draw_tree(road_width / 2 + 10, z, trunk_height, leaf_radius)
        tree_count += 1

def draw_car():
    glPushMatrix()
    # NEW: Apply jump height to car position
    glTranslatef(car_x, car_height / 2 + car_jump_height, car_z)
    glRotatef(car_angle, 0, 1, 0)
    
    draw_enhanced_car_body()  # NEW: Enhanced car design
    draw_windows()
    draw_wheels()
    draw_lights()
    
    glPopMatrix()

def draw_enhanced_car_body():
    # NEW: Trapezium-shaped car design
    glColor3f(0.2, 0.8, 0.2)  # Bright green color
    
    # Create trapezium shape using custom vertices
    glBegin(GL_QUADS)
    
    # Front face (narrower)
    glVertex3f(-car_width/3, -car_height/2, car_length/2)
    glVertex3f(-car_width/3, car_height/2, car_length/2)
    glVertex3f(car_width/3, car_height/2, car_length/2)
    glVertex3f(car_width/3, -car_height/2, car_length/2)
    
    # Back face (wider)
    glVertex3f(-car_width/2, -car_height/2, -car_length/2)
    glVertex3f(-car_width/2, car_height/2, -car_length/2)
    glVertex3f(car_width/2, car_height/2, -car_length/2)
    glVertex3f(car_width/2, -car_height/2, -car_length/2)
    
    # Left side (trapezium)
    glVertex3f(-car_width/3, -car_height/2, car_length/2)
    glVertex3f(-car_width/3, car_height/2, car_length/2)
    glVertex3f(-car_width/2, car_height/2, -car_length/2)
    glVertex3f(-car_width/2, -car_height/2, -car_length/2)
    
    # Right side (trapezium)
    glVertex3f(car_width/3, -car_height/2, car_length/2)
    glVertex3f(car_width/3, car_height/2, car_length/2)
    glVertex3f(car_width/2, car_height/2, -car_length/2)
    glVertex3f(car_width/2, -car_height/2, -car_length/2)
    
    # Top face (trapezium)
    glVertex3f(-car_width/3, car_height/2, car_length/2)
    glVertex3f(-car_width/2, car_height/2, -car_length/2)
    glVertex3f(car_width/2, car_height/2, -car_length/2)
    glVertex3f(car_width/3, car_height/2, car_length/2)
    
    # Bottom face (trapezium)
    glVertex3f(-car_width/3, -car_height/2, car_length/2)
    glVertex3f(-car_width/2, -car_height/2, -car_length/2)
    glVertex3f(car_width/2, -car_height/2, -car_length/2)
    glVertex3f(car_width/3, -car_height/2, car_length/2)
    
    glEnd()
    
    # Add some details
    glColor3f(0.1, 0.1, 0.1)  # Black details
    # Front bumper
    glPushMatrix()
    glTranslatef(0, -car_height/2 - 0.1, car_length/2 + 0.1)
    glScalef(car_width/2, 0.1, 0.2)
    glutSolidCube(1)
    glPopMatrix()
    
    # Rear bumper
    glPushMatrix()
    glTranslatef(0, -car_height/2 - 0.1, -car_length/2 - 0.1)
    glScalef(car_width/2, 0.1, 0.2)
    glutSolidCube(1)
    glPopMatrix()

def draw_windows():
    if day_mode == 1:
        window_color = (0.8, 0.8, 1.0, 0.7)
    elif day_mode == 2:
        window_color = (0.7, 0.7, 0.9, 0.7)
    else:
        window_color = (0.6, 0.6, 0.8, 0.7)
    
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    glColor4f(*window_color)
    glBegin(GL_QUADS)
    glVertex3f(-car_width/2 * 0.9, -car_height/2 * 0.5, car_length/2)
    glVertex3f(-car_width/2 * 0.9, car_height/2 * 0.7, car_length/2)
    glVertex3f(car_width/2 * 0.9, car_height/2 * 0.7, car_length/2)
    glVertex3f(car_width/2 * 0.9, -car_height/2 * 0.5, car_length/2)
    glEnd()
    
    glColor4f(*window_color)
    glBegin(GL_QUADS)
    glVertex3f(-car_width/2 * 0.9, -car_height/2 * 0.5, -car_length/2)
    glVertex3f(-car_width/2 * 0.9, car_height/2 * 0.7, -car_length/2)
    glVertex3f(car_width/2 * 0.9, car_height/2 * 0.7, -car_length/2)
    glVertex3f(car_width/2 * 0.9, -car_height/2 * 0.5, -car_length/2)
    glEnd()
    
    glColor4f(*window_color)
    glBegin(GL_QUADS)
    glVertex3f(-car_width/2, -car_height/2 * 0.5, -car_length/2 * 0.9)
    glVertex3f(-car_width/2, car_height/2 * 0.7, -car_length/2 * 0.9)
    glVertex3f(-car_width/2, car_height/2 * 0.7, car_length/2 * 0.9)
    glVertex3f(-car_width/2, -car_height/2 * 0.5, car_length/2 * 0.9)
    glEnd()
    
    glColor4f(*window_color)
    glBegin(GL_QUADS)
    glVertex3f(car_width/2, -car_height/2 * 0.5, -car_length/2 * 0.9)
    glVertex3f(car_width/2, car_height/2 * 0.7, -car_length/2 * 0.9)
    glVertex3f(car_width/2, car_height/2 * 0.7, car_length/2 * 0.9)
    glVertex3f(car_width/2, -car_height/2 * 0.5, car_length/2 * 0.9)
    glEnd()
    
    glDisable(GL_BLEND)

def draw_wheels():
    global wheel_rotation_angle
    wheel_radius = 0.315 * 0.9
    wheel_width = 0.2 * 0.9
    wheel_offset_x = 0.8 * 0.81
    wheel_offset_z = 0.8 * 0.81

    wheel_rotation_angle += current_speed * 0.5
    if wheel_rotation_angle > 360:
        wheel_rotation_angle -= 360
    elif wheel_rotation_angle < -360:
        wheel_rotation_angle += 360

    positions = [
        (wheel_offset_x, wheel_offset_z),
        (wheel_offset_x, -wheel_offset_z),
        (-wheel_offset_x, wheel_offset_z),
        (-wheel_offset_x, -wheel_offset_z),
    ]

    for x, z in positions:
        glPushMatrix()
        glTranslatef(x, -0.5 + wheel_radius, z)
        glRotatef(90, 0, 1, 0)
        glRotatef(wheel_rotation_angle, 0, 0, 1)
        
        glColor3f(0, 0, 0)
        glutSolidCylinder(wheel_radius, wheel_width, 32, 10)
        
        glColor3f(0.7, 0.7, 0.7)
        glutSolidTorus(0.05, wheel_radius - 0.05, 10, 32)
        glPopMatrix()

def draw_lights():
    light_size = 0.15
    light_height = -0.2
    
    if headlights_on:
        if day_mode == 3:
            glColor3f(1.0, 1.0, 0.9)
        else:
            glColor3f(1.0, 1.0, 0.7)
        
        if day_mode == 3:
            glPushMatrix()
            glTranslatef(0, light_height, car_length/2 * 0.9)
            
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            glColor4f(1.0, 1.0, 0.8, 0.3)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(-car_width/2 * 0.9, 0, 0)
            glVertex3f(-car_width/2 * 0.9 - 1.2, 0, 10)
            glVertex3f(-car_width/2 * 0.9 + 1.2, 0, 10)
            glEnd()
            
            glColor4f(1.0, 1.0, 0.8, 0.3)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(car_width/2 * 0.9, 0, 0)
            glVertex3f(car_width/2 * 0.9 - 1.2, 0, 10)
            glVertex3f(car_width/2 * 0.9 + 1.2, 0, 10)
            glEnd()
            
            glDisable(GL_BLEND)
            glPopMatrix()
    else:
        glColor3f(0.6, 0.6, 0.4)
    
    glPushMatrix()
    glTranslatef(-car_width/2 * 0.9, light_height, car_length/2 * 0.9)
    glutSolidSphere(light_size, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(car_width/2 * 0.9, light_height, car_length/2 * 0.9)
    glutSolidSphere(light_size, 10, 10)
    glPopMatrix()
    
    if current_speed < 0 or keys[b' ']:
        glColor3f(1.0, 0.0, 0.0)
    else:
        glColor3f(0.5, 0.0, 0.0)
    
    glPushMatrix()
    glTranslatef(-car_width/2 * 0.9, light_height, -car_length/2 * 0.9)
    glutSolidSphere(light_size, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(car_width/2 * 0.9, light_height, -car_length/2 * 0.9)
    glutSolidSphere(light_size, 10, 10)
    glPopMatrix()

def draw_minimap():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, 100, 0, 100, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)

    center_x = 84
    center_y = 84
    radius = 10 * 0.9

    glColor3f(1, 1, 1)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(center_x, center_y)
    for i in range(361):
        angle = i * 2 * math.pi / 360
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        glVertex2f(x, y)
    glEnd()

    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(center_x - 4, center_y - radius + 2)
    glVertex2f(center_x - 4, center_y + radius - 2)
    glVertex2f(center_x + 4, center_y + radius - 2)
    glVertex2f(center_x + 4, center_y - radius + 2)
    glEnd()

    mapped_x = center_x
    mapped_z = center_y + ((car_z - scene_start) / (scene_end - scene_start)) * (2 * radius - 4) - (radius - 2)
    glColor3f(0.0, 0.8, 0.0)  # NEW: Green car on minimap
    glPointSize(6)
    glBegin(GL_POINTS)
    glVertex2f(mapped_x, mapped_z)
    glEnd()

    glEnable(GL_DEPTH_TEST)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_speedometer():
    speed_kmh = abs(current_speed) * 3.6
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 700)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glDisable(GL_DEPTH_TEST)
    
    glRasterPos2f(15, 680)
    score_text = f"Score: {score}"
    glColor3f(1, 1, 1)
    for character in score_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(character))

    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(10, 660)
    glVertex2f(150, 660)
    glVertex2f(150, 680)
    glVertex2f(10, 680)
    glEnd()
    
    glColor3f(1, 1, 1)
    glRasterPos2f(15, 665)
    speed_text = f"Speed: {speed_kmh:.1f} km/h"
    for character in speed_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(character))
    
    glRasterPos2f(15, 645)
    light_text = "Headlights: ON" if headlights_on else "Headlights: OFF"
    glColor3f(1.0, 1.0, 0.0) if headlights_on else glColor3f(0.7, 0.7, 0.7)
    for character in light_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(character))
    
    glRasterPos2f(15, 625)
    mode_text = ["Day Mode", "Evening Mode", "Night Mode"][day_mode-1]
    glColor3f(1.0, 1.0, 1.0)
    for character in mode_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(character))
    
    glRasterPos2f(15, 605)
    view_text = "View: First-Person" if first_person_view else "View: Third-Person"
    glColor3f(0.8, 0.8, 1.0)
    for character in view_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(character))
    
    # NEW: Jump status display
    glRasterPos2f(15, 585)
    jump_text = "JUMPING!" if is_jumping else "Press J to Jump"
    glColor3f(1.0, 0.5, 0.0) if is_jumping else glColor3f(0.7, 0.7, 0.7)
    for character in jump_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(character))
    
    glEnable(GL_DEPTH_TEST)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def display():
    global time_of_day, headlights_on, day_mode
    
    if game_active:
        time_of_day += 0.5
        if time_of_day >= 24*60:
            time_of_day -= 24*60

    if 5*60 <= time_of_day < 6*60:
        r = 0.7 + 0.3*(time_of_day-300)/60
        g = 0.5 + 0.3*(time_of_day-300)/60
        b = 0.3 + 0.5*(time_of_day-300)/60
        day_mode = 1
    elif 6*60 <= time_of_day < 18*60:
        r, g, b = 0.5, 0.8, 1.0
        day_mode = 1
    elif 18*60 <= time_of_day < 19*60:
        t = (time_of_day-1080)/60
        r = 0.5 - 0.3*t
        g = 0.8 - 0.4*t
        b = 1.0 - 0.7*t
        day_mode = 2
    elif 19*60 <= time_of_day < 21*60:
        r, g, b = 0.02, 0.02, 0.08
        day_mode = 3
    else:
        r, g, b = 0.01, 0.01, 0.04
        day_mode = 3

    headlights_on = (time_of_day >= 18*60) or (time_of_day < 5*60)

    glClearColor(r, g, b, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    if first_person_view:
        eye_x = car_x + 0.3 * math.sin(math.radians(car_angle))
        eye_y = car_height * 0.7 + car_jump_height  # NEW: Include jump height
        eye_z = car_z + 0.3 * math.cos(math.radians(car_angle))
        look_x = car_x + math.sin(math.radians(car_angle))
        look_y = eye_y - 0.1
        look_z = car_z + math.cos(math.radians(car_angle))
        gluLookAt(eye_x, eye_y, eye_z, look_x, look_y, look_z, 0, 1, 0)
        
        glPushMatrix()
        glTranslatef(car_x, car_height/2 + car_jump_height, car_z)  # NEW: Include jump height
        glRotatef(car_angle, 0, 1, 0)
        
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex3f(-car_width/2 * 0.8, -car_height/4, -car_length/2 * 0.9)
        glVertex3f(-car_width/2 * 0.8, car_height/4, -car_length/2 * 0.9)
        glVertex3f(car_width/2 * 0.8, car_height/4, -car_length/2 * 0.9)
        glVertex3f(car_width/2 * 0.8, -car_height/4, -car_length/2 * 0.9)
        glEnd()
        
        glColor3f(0.4, 0.4, 0.4)
        glPushMatrix()
        glTranslatef(0, car_height/4, -car_length/2 * 0.8)
        glutSolidTorus(0.05, 0.15, 10, 20)
        glPopMatrix()
        
        glPopMatrix()
    else:
        eye_x = car_x - camera_distance * math.sin(math.radians(car_angle + camera_angle_horizontal)) * math.cos(
            math.radians(camera_angle_vertical))
        eye_y = car_height_offset + camera_distance * math.sin(math.radians(camera_angle_vertical))
        eye_z = car_z - camera_distance * math.cos(math.radians(car_angle + camera_angle_horizontal)) * math.cos(
            math.radians(camera_angle_vertical))
        gluLookAt(eye_x, eye_y, eye_z, car_x, car_height / 2 + car_jump_height, car_z, 0, 1, 0)  # NEW: Include jump height

    draw_ground()
    draw_scenery()
    if not first_person_view:
        draw_car()
    for obstacle in obstacles:
        draw_obstacle(obstacle)
    draw_minimap()
    draw_speedometer()

    if not game_active:
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, 800, 0, 600)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glColor3f(1, 0, 0)
        glRasterPos2f(350, 300)
        game_over_text = "GAME OVER! Final Score: " + str(score)
        for character in game_over_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(character))
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    glutSwapBuffers()

def update(value):
    global car_x, car_z, car_angle, camera_angle_horizontal, camera_angle_vertical, current_speed, headlights_on, first_person_view, game_active, next_obstacle_time, score, game_over_time
    global next_obstacle_time, car_jump_height, car_jump_velocity, is_jumping
    
    if game_active:
        # Start spawning obstacles 10 seconds after game start
        if time.time() > game_start_time + 10:  # 10 second delay
            if time.time() > next_obstacle_time:
                obstacles.append(Obstacle(car_z + 100))
                next_obstacle_time = time.time() + random.uniform(1.5, 4.0)

    # NEW: Jump mechanics
    if keys[b'j'] and not is_jumping:
        is_jumping = True
        car_jump_velocity = jump_power
        keys[b'j'] = False
    
    if is_jumping:
        car_jump_height += car_jump_velocity * 0.1
        car_jump_velocity -= gravity
        if car_jump_height <= 0:
            car_jump_height = 0
            car_jump_velocity = 0
            is_jumping = False

    if keys[b'g']:
        first_person_view = True
        keys[b'g'] = False
    if keys[b'h']:
        first_person_view = False
        keys[b'h'] = False

    if keys[b'l']:
        # Only allow toggle during daylight hours (5AM-6PM)
        if not (18*60 <= time_of_day < 5*60):
            headlights_on = not headlights_on
        keys[b'l'] = False

    if 18*60 <= time_of_day < 5*60:
        headlights_on = True

    if keys[b'r']:
        reset_game()
        keys[b'r'] = False

    if keys['left'] or keys[b'q']:
        camera_angle_horizontal += camera_rotation_speed
    if keys['right'] or keys[b'e']:
        camera_angle_horizontal -= camera_rotation_speed

    if keys['up']:
        camera_angle_vertical += camera_vertical_speed
    if keys['down']:
        camera_angle_vertical -= camera_vertical_speed

    camera_angle_vertical = max(min_vertical_angle, min(max_vertical_angle, camera_angle_vertical))

    if keys[b'a']:
        car_angle += steering_speed * 0.1
    elif keys[b'd']:
        car_angle -= steering_speed * 0.1

    if keys[b'w']:
        current_speed = min(current_speed + acceleration, max_speed)

    if keys[b' ']:
        if current_speed > 0:
            current_speed = max(current_speed - brake_deceleration, 0)
        elif current_speed < 0:
            current_speed = min(current_speed + brake_deceleration, 0)

    if not (keys[b'w'] or keys[b's'] or keys[b' ']):
        if current_speed > 0:
            current_speed = max(current_speed - 0.5, 0)
        elif current_speed < 0:
            current_speed = min(current_speed + 0.5, 0)

    dx = current_speed * math.sin(math.radians(car_angle))
    dz = current_speed * math.cos(math.radians(car_angle))

    new_car_x = car_x + dx * 0.1
    new_car_z = car_z + dz * 0.1

    if new_car_x < road_width / 2 - car_width / 2 and new_car_x > -road_width / 2 + car_width / 2:
        car_x = new_car_x
    elif new_car_x >= road_width / 2 - car_width / 2:
        car_x = road_width / 2 - car_width / 2
    elif new_car_x <= -road_width / 2 + car_width / 2:
        car_x = -road_width / 2 + car_width / 2

    car_z = new_car_z

    if game_active:
        if time.time() > next_obstacle_time and time_of_day > 15*60:
            obstacles.append(Obstacle(car_z + 100))
            next_obstacle_time = time.time() + random.uniform(1.5, 4.0)
        
        for obs in obstacles[:]:
            obs.z -= current_speed * 0.1
            
            if check_collision(obs) and not obs.hit:
                obs.hit = True
                if obs.type == 'round':
                    # Round obstacle: +10 points and speed boost
                    score += 10
                    current_speed = min(current_speed + 2.0, max_speed)  # Speed boost
                    print(f"Hit GREEN round obstacle! +10 points, speed boost! Score: {score}")
                elif obs.type == 'cube':
                    # Cube obstacle: -5 points and speed decrease
                    score -= 5
                    current_speed = max(current_speed - 1.5, 0)  # Speed decrease
                    print(f"Hit RED cube obstacle! -5 points, speed decrease! Score: {score}")
            
            if obs.z < car_z - 20 and not obs.scored:
                if not obs.hit:  # Only score if not hit (avoided obstacle)
                    if obs.type == 'round':
                        score += 5  # Bonus for avoiding good obstacle
                    elif obs.type == 'cube':
                        score += 3  # Bonus for avoiding bad obstacle
                obs.scored = True
                obstacles.remove(obs)

    if not game_active:
        if time.time() > game_over_time + 5:
            reset_game()
        else:
            glutPostRedisplay()
            glutTimerFunc(16, update, 0)
            return

    glutPostRedisplay()
    glutTimerFunc(16, update, 0)

def key_down(key, x, y):
    if key in keys:
        keys[key] = True

def key_up(key, x, y):
    if key in keys:
        keys[key] = False

def special_down(key, x, y):
    if key == GLUT_KEY_UP:
        keys['up'] = True
    elif key == GLUT_KEY_DOWN:
        keys['down'] = True
    elif key == GLUT_KEY_LEFT:
        keys['left'] = True
    elif key == GLUT_KEY_RIGHT:
        keys['right'] = True

def special_up(key, x, y):
    if key == GLUT_KEY_UP:
        keys['up'] = False
    elif key == GLUT_KEY_DOWN:
        keys['down'] = False
    elif key == GLUT_KEY_LEFT:
        keys['left'] = False
    elif key == GLUT_KEY_RIGHT:
        keys['right'] = False

def main():
    print("🚗 Enhanced Car Game with Jump Feature!")
    print("=" * 50)
    print("Controls:")
    print("  W - Accelerate")
    print("  A/D - Steer left/right")
    print("  Space - Brake")
    print("  J - JUMP (NEW!)")
    print("  G/H - Toggle first/third person view")
    print("  L - Toggle headlights")
    print("  R - Reset game")
    print("  Arrow Keys - Camera control")
    print("=" * 50)
    print("NEW FEATURES:")
    print("  • Jump over obstacles with J key (low height)")
    print("  • GREEN round obstacles = +10 points + speed boost")
    print("  • RED cube obstacles = -5 points + speed decrease")
    print("  • Trapezium-shaped car design in bright green")
    print("  • Strategic gameplay: collect green, avoid red!")
    print("=" * 50)
    
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 700)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Enhanced 3D Car Game with Jump Feature")
    init()
    glutDisplayFunc(display)
    glutKeyboardFunc(key_down)
    glutKeyboardUpFunc(key_up)
    glutSpecialFunc(special_down)
    glutSpecialUpFunc(special_up)
    glutTimerFunc(16, update, 0)
    glutMainLoop()

if __name__ == "__main__":
    main()
