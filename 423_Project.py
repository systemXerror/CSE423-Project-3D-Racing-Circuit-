from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import time
import random

# Game states
GAME_STATE_START = 0
GAME_STATE_RACING = 1
GAME_STATE_FINISHED = 2

# Camera modes
CAMERA_FIRST_PERSON = 0  # True first person (no car visible)
CAMERA_THIRD_PERSON = 1   # Behind car view

# Game variables
game_state = GAME_STATE_START
camera_mode = CAMERA_THIRD_PERSON  # Start with third person
camera_pos = (0, 50, 100)
fovY = 60
GRID_LENGTH = 2000

# Key states for continuous movement
keys_pressed = {
    b'w': False,
    b's': False,
    b'a': False,
    b'd': False
}

# Car physics variables
car_pos = [800, 0, 5]  # Start on track at finish line, lower to ground
car_rotation = 0  # Face straight along track (0 degrees)
car_speed = 0  # Current speed
car_max_speed = 500  # Max speed (km/h scaled for game)
car_acceleration = 2
car_deceleration = 3
car_turn_speed = 2
car_friction = 0.98
car_reverse_max = -100

# Track and checkpoint system
current_checkpoint = 0
current_lap = 1
total_laps = 3
checkpoints = []  # Will be populated with checkpoint positions
checkpoint_radius = 100
lap_times = []
best_lap_time = float('inf')
race_start_time = 0
lap_start_time = 0
current_time = 0

# Collision and physics
off_track_penalty = 0.5  # Speed multiplier when off track
is_off_track = False
collision_bounce = 30
obstacles = []  # Trees and buildings positions

# Visual effects
speed_lines = []
boost_points = []
boost_active = False
boost_timer = 0
boost_speed_multiplier = 1.5

# Birds for animation
birds = []

# Sun rotation
sun_angle = 0

# Clouds
clouds = []

class Bird:
    def __init__(self):
        self.pos = [random.uniform(-GRID_LENGTH, GRID_LENGTH), 
                   random.uniform(-GRID_LENGTH, GRID_LENGTH), 
                   random.uniform(200, 400)]
        self.velocity = [random.uniform(-5, 5), random.uniform(-5, 5), 0]
        self.wing_angle = 0
        
    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.wing_angle = math.sin(time.time() * 10) * 30
        
        # Wrap around
        if abs(self.pos[0]) > GRID_LENGTH:
            self.pos[0] = -self.pos[0]
        if abs(self.pos[1]) > GRID_LENGTH:
            self.pos[1] = -self.pos[1]

class Cloud:
    def __init__(self):
        self.pos = [random.uniform(-GRID_LENGTH, GRID_LENGTH),
                   random.uniform(-GRID_LENGTH, GRID_LENGTH),
                   random.uniform(300, 500)]
        self.size = random.uniform(30, 60)
        self.drift_speed = random.uniform(0.5, 2)
    
    def update(self):
        self.pos[0] += self.drift_speed
        if self.pos[0] > GRID_LENGTH:
            self.pos[0] = -GRID_LENGTH

def init_game():
    """Initialize game components"""
    global checkpoints, obstacles, birds, boost_points, clouds, car_pos, car_rotation
    
    # Reset car to start position on track - on the straight part facing along track
    # Position at the right side of track (x=800, y=0) facing upward (90 degrees)
    car_pos = [800, 0, 5]
    car_rotation = 90  # 90 degrees = facing upward along Y axis (along the track)
    
    # Clear previous data
    checkpoints.clear()
    obstacles.clear()
    birds.clear()
    boost_points.clear()
    clouds.clear()
    
    # Create circular track with checkpoints properly oriented perpendicular to track direction
    num_checkpoints = 6
    for i in range(num_checkpoints):
        angle = (i * 360 / num_checkpoints) * math.pi / 180
        radius = 800
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        
        # Calculate the direction perpendicular to the track at this point
        # The track is circular, so the checkpoint should be perpendicular to the tangent
        # Tangent direction is perpendicular to radius, so checkpoint aligns with radius
        checkpoint_angle = angle * 180 / math.pi  # Convert to degrees, align with radius from center
        
        checkpoints.append({'pos': (x, y), 'angle': checkpoint_angle})
    
    # Create properly placed obstacles
    # Trees inside the track circle - avoid track area
    for i in range(6):
        angle = random.uniform(0, 360) * math.pi / 180
        radius = random.uniform(400, 650)  # Well inside track
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        obstacles.append({'pos': (x, y), 'type': 'tree', 'radius': 20})
    
    # Trees outside the track - avoid track area
    for i in range(10):
        angle = random.uniform(0, 360) * math.pi / 180
        radius = random.uniform(950, 1400)  # Well outside track
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        obstacles.append({'pos': (x, y), 'type': 'tree', 'radius': 20})
    
    # Buildings further out
    for i in range(6):
        angle = (i * 60 + 30) * math.pi / 180
        radius = 1200
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        obstacles.append({'pos': (x, y), 'type': 'building', 'radius': 35})
    
    # Create birds
    for i in range(5):
        birds.append(Bird())
    
    # Create clouds
    for i in range(8):
        clouds.append(Cloud())
    
    # Create boost points on the track
    for i in range(3):
        angle = (i * 120 + 60) * math.pi / 180
        radius = 800  # On the track centerline
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        boost_points.append({'pos': (x, y), 'collected': False})

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Draw text on screen"""
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_sports_car():
    """Draw a Lamborghini/Porsche style sports car"""
    global car_speed
    
    glPushMatrix()
    glTranslatef(car_pos[0], car_pos[1], car_pos[2])
    glRotatef(car_rotation, 0, 0, 1)
    
    # Car body - sleek sports car design
    speed_ratio = abs(car_speed) / car_max_speed
    
    # Main body color - metallic blue to red based on speed
    glColor3f(0.1 + speed_ratio * 0.8, 0.1, 0.8 - speed_ratio * 0.6)
    
    # Main chassis - low and wide like a Lamborghini
    glPushMatrix()
    glScalef(2.2, 1.5, 0.3)
    glutSolidCube(25)
    glPopMatrix()
    
    # Front hood - sloped aerodynamic
    glPushMatrix()
    glTranslatef(20, 0, 2)
    glRotatef(-15, 0, 1, 0)
    glScalef(1.8, 1.4, 0.2)
    glutSolidCube(20)
    glPopMatrix()
    
    # Rear engine cover - raised like Lamborghini
    glPushMatrix()
    glTranslatef(-18, 0, 4)
    glRotatef(10, 0, 1, 0)
    glScalef(1.5, 1.3, 0.25)
    glutSolidCube(20)
    glPopMatrix()
    
    # Cockpit - low profile windshield
    glColor3f(0.1, 0.1, 0.15)
    glPushMatrix()
    glTranslatef(0, 0, 8)
    glRotatef(-20, 0, 1, 0)
    glScalef(0.8, 1.0, 0.3)
    glutSolidCube(18)
    glPopMatrix()
    
    # Side air intakes (Lamborghini style)
    glColor3f(0.05, 0.05, 0.05)
    for y_side in [-15, 15]:
        glPushMatrix()
        glTranslatef(-5, y_side, 4)
        glScalef(0.8, 0.2, 0.3)
        glutSolidCube(15)
        glPopMatrix()
    
    # Rear spoiler - large racing style
    glColor3f(0.15, 0.15, 0.15)
    glPushMatrix()
    glTranslatef(-25, 0, 12)
    glScalef(0.15, 1.8, 0.4)
    glutSolidCube(20)
    glPopMatrix()
    
    # Spoiler supports
    for y_sup in [-12, 12]:
        glPushMatrix()
        glTranslatef(-22, y_sup, 6)
        glScalef(0.1, 0.1, 0.6)
        glutSolidCube(15)
        glPopMatrix()
    
    # Wheels - larger racing wheels
    glColor3f(0.05, 0.05, 0.05)
    wheel_positions = [
        (15, -16, -2),   # Front left
        (15, 16, -2),    # Front right
        (-15, -18, -2),  # Rear left (wider rear track)
        (-15, 18, -2)    # Rear right
    ]
    
    for x, y, z in wheel_positions:
        glPushMatrix()
        glTranslatef(x, y, z)
        glRotatef(90, 1, 0, 0)
        # Wheel with rim detail
        gluCylinder(gluNewQuadric(), 5, 5, 4, 10, 2)
        # Rim center
        glColor3f(0.7, 0.7, 0.7)
        gluDisk(gluNewQuadric(), 0, 3, 8, 1)
        glTranslatef(0, 0, 4)
        gluDisk(gluNewQuadric(), 0, 3, 8, 1)
        glColor3f(0.05, 0.05, 0.05)
        glPopMatrix()
    
    # Headlights - angular sports car style
    if car_speed > 0:
        glColor3f(1, 1, 0.8)
        for y in [-8, 8]:
            glPushMatrix()
            glTranslatef(27, y, 2)
            glScalef(0.5, 1, 0.7)
            glutSolidCube(5)
            glPopMatrix()
    
    # Tail lights - LED strip style
    glColor3f(0.8, 0, 0)
    glPushMatrix()
    glTranslatef(-28, 0, 4)
    glScalef(0.2, 1.5, 0.2)
    glutSolidCube(15)
    glPopMatrix()
    
    # Front grille
    glColor3f(0.2, 0.2, 0.2)
    glPushMatrix()
    glTranslatef(28, 0, 0)
    glScalef(0.1, 1.2, 0.4)
    glutSolidCube(15)
    glPopMatrix()
    
    glPopMatrix()

def draw_sun():
    """Draw a sun in the sky"""
    global sun_angle
    sun_angle += 0.1
    
    glPushMatrix()
    glTranslatef(1000, 1000, 600)
    glRotatef(sun_angle, 0, 0, 1)
    
    # Sun sphere
    glColor3f(1, 0.9, 0)
    gluSphere(gluNewQuadric(), 80, 20, 20)
    
    # Sun rays
    glColor3f(1, 1, 0.3)
    for i in range(8):
        angle = i * 45
        glPushMatrix()
        glRotatef(angle, 0, 0, 1)
        glTranslatef(100, 0, 0)
        glScalef(2, 0.3, 0.3)
        glutSolidCube(40)
        glPopMatrix()
    
    glPopMatrix()

def draw_clouds():
    """Draw clouds in the sky"""
    for cloud in clouds:
        glPushMatrix()
        glTranslatef(cloud.pos[0], cloud.pos[1], cloud.pos[2])
        
        glColor3f(1, 1, 1)
        # Cloud made of multiple spheres
        for i in range(3):
            glPushMatrix()
            glTranslatef(i * cloud.size * 0.6, 0, 0)
            gluSphere(gluNewQuadric(), cloud.size, 10, 10)
            glPopMatrix()
        
        glPushMatrix()
        glTranslatef(cloud.size * 0.3, 0, cloud.size * 0.3)
        gluSphere(gluNewQuadric(), cloud.size * 0.8, 10, 10)
        glPopMatrix()
        
        glPopMatrix()
        cloud.update()

def draw_realistic_tree(x, y):
    """Draw a more realistic tree"""
    glPushMatrix()
    glTranslatef(x, y, 0)
    
    # Tree trunk - brown cylinder
    glColor3f(0.4, 0.2, 0.05)
    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 8, 6, 50, 8, 8)
    glPopMatrix()
    
    # Tree foliage - multiple green spheres for fuller look
    glColor3f(0, 0.5, 0)
    
    # Main foliage
    glPushMatrix()
    glTranslatef(0, 0, 50)
    gluSphere(gluNewQuadric(), 25, 10, 10)
    glPopMatrix()
    
    # Additional foliage layers
    glColor3f(0, 0.6, 0)
    glPushMatrix()
    glTranslatef(10, 0, 45)
    gluSphere(gluNewQuadric(), 15, 8, 8)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(-10, 5, 48)
    gluSphere(gluNewQuadric(), 15, 8, 8)
    glPopMatrix()
    
    glColor3f(0, 0.4, 0)
    glPushMatrix()
    glTranslatef(0, -10, 52)
    gluSphere(gluNewQuadric(), 18, 8, 8)
    glPopMatrix()
    
    glPopMatrix()

def draw_track():
    """Draw the racing track"""
    # Main track (circular) - asphalt color
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUAD_STRIP)
    for i in range(37):
        angle = i * 10 * math.pi / 180
        inner_radius = 700
        outer_radius = 900
        
        x_inner = math.cos(angle) * inner_radius
        y_inner = math.sin(angle) * inner_radius
        x_outer = math.cos(angle) * outer_radius
        y_outer = math.sin(angle) * outer_radius
        
        glVertex3f(x_inner, y_inner, 0)
        glVertex3f(x_outer, y_outer, 0)
    glEnd()
    
    # Track center line - dashed white
    glColor3f(1, 1, 1)
    glLineWidth(3)
    glBegin(GL_LINES)
    for i in range(36):
        angle = i * 10 * math.pi / 180
        radius = 800
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        next_angle = (i + 1) * 10 * math.pi / 180
        next_x = math.cos(next_angle) * radius
        next_y = math.sin(next_angle) * radius
        
        if i % 2 == 0:
            glVertex3f(x, y, 1)
            glVertex3f(next_x, next_y, 1)
    glEnd()
    
    # Track edges - yellow lines
    glColor3f(1, 1, 0)
    glLineWidth(4)
    glBegin(GL_LINE_LOOP)
    for i in range(37):
        angle = i * 10 * math.pi / 180
        x = math.cos(angle) * 700
        y = math.sin(angle) * 700
        glVertex3f(x, y, 1)
    glEnd()
    
    glBegin(GL_LINE_LOOP)
    for i in range(37):
        angle = i * 10 * math.pi / 180
        x = math.cos(angle) * 900
        y = math.sin(angle) * 900
        glVertex3f(x, y, 1)
    glEnd()
    
    # Start/Finish line - checkered pattern on the straight part
    glLineWidth(8)
    # Draw at the rightmost part of the track (x=800, y around 0)
    for i in range(10):
        if i % 2 == 0:
            glColor3f(1, 1, 1)
        else:
            glColor3f(0, 0, 0)
        
        glBegin(GL_QUADS)
        glVertex3f(700, -50 + i * 10, 1)
        glVertex3f(900, -50 + i * 10, 1)
        glVertex3f(900, -40 + i * 10, 1)
        glVertex3f(700, -40 + i * 10, 1)
        glEnd()

def draw_checkpoint_arch(checkpoint_data, index):
    """Draw a half-circle arch checkpoint perpendicular to the track direction"""
    x, y = checkpoint_data['pos']
    angle = checkpoint_data['angle']
    
    # Checkpoint passed - green, not passed - red
    if index < current_checkpoint or (current_lap > 1 and index == 0):
        glColor3f(0, 1, 0)
    else:
        glColor3f(1, 0, 0)
    
    glPushMatrix()
    glTranslatef(x, y, 0)
    # Rotate checkpoint to be perpendicular to track direction (aligned with radius)
    glRotatef(angle, 0, 0, 1)
    
    # Draw arch supports (pillars) perpendicular to track
    arch_width = 100  # Width of the checkpoint arch
    for side in [-arch_width, arch_width]:
        glPushMatrix()
        glTranslatef(0, side, 0)  # Place pillars along Y axis (perpendicular to radius)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 5, 5, 80, 8, 8)
        glPopMatrix()
    
    # Draw half-circle arch spanning across the track
    glLineWidth(10)
    glBegin(GL_LINE_STRIP)
    for i in range(19):  # 0 to 180 degrees for half circle
        arch_angle = i * 10 * math.pi / 180
        arch_y = math.cos(arch_angle) * arch_width  # Span across track width
        arch_z = math.sin(arch_angle) * arch_width + 80
        glVertex3f(0, arch_y, arch_z)
    glEnd()
    
    # Fill the arch for better visibility
    glBegin(GL_QUAD_STRIP)
    for i in range(19):
        arch_angle = i * 10 * math.pi / 180
        inner_r = arch_width - 5
        outer_r = arch_width + 5
        
        y_inner = math.cos(arch_angle) * inner_r
        y_outer = math.cos(arch_angle) * outer_r
        z_pos = math.sin(arch_angle) * arch_width + 80
        
        glVertex3f(0, y_inner, z_pos)
        glVertex3f(0, y_outer, z_pos)
    glEnd()
    
    # Add checkpoint flag/banner on top
    glColor3f(1, 1, 1)
    glPushMatrix()
    glTranslatef(0, 0, 180)
    glScalef(0.2, 1, 0.3)
    glutSolidCube(40)
    glPopMatrix()
    
    # Add checkpoint number text effect
    if index == 0:
        # Start/Finish line gets special treatment
        glColor3f(1, 0, 0)
        glPushMatrix()
        glTranslatef(0, 0, 200)
        glScalef(0.3, 1.5, 0.2)
        glutSolidCube(40)
        glPopMatrix()
    
    glPopMatrix()

def draw_obstacle(obstacle):
    """Draw trees or buildings"""
    x, y = obstacle['pos']
    
    if obstacle['type'] == 'tree':
        draw_realistic_tree(x, y)
    else:
        # Building
        glPushMatrix()
        glTranslatef(x, y, 0)
        
        # Building base
        glColor3f(0.6, 0.6, 0.7)
        glPushMatrix()
        glScalef(1, 1, 4)
        glutSolidCube(40)
        glPopMatrix()
        
        # Windows
        glColor3f(0.2, 0.2, 0.8)
        for z in [20, 40, 60]:
            for offset in [-10, 10]:
                glPushMatrix()
                glTranslatef(offset, -21, z)
                glutSolidCube(8)
                glPopMatrix()
        
        glPopMatrix()

def draw_environment():
    """Draw grass and environment"""
    # Grass terrain with gradient
    glBegin(GL_QUADS)
    glColor3f(0.1, 0.5, 0.1)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, -1)
    glColor3f(0.1, 0.4, 0.1)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, -1)
    glColor3f(0.1, 0.5, 0.1)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, -1)
    glColor3f(0.1, 0.4, 0.1)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, -1)
    glEnd()
    
    # Spectator stands
    for angle in [45, 135, 225, 315]:
        rad = angle * math.pi / 180
        x = math.cos(rad) * 1100
        y = math.sin(rad) * 1100
        
        glPushMatrix()
        glTranslatef(x, y, 0)
        glRotatef(angle + 180, 0, 0, 1)
        
        # Stand structure
        glColor3f(0.7, 0.7, 0.8)
        glPushMatrix()
        glScalef(3, 1, 1.5)
        glutSolidCube(50)
        glPopMatrix()
        
        # Stand roof
        glColor3f(0.8, 0.2, 0.2)
        glPushMatrix()
        glTranslatef(0, 0, 40)
        glScalef(3.2, 1.1, 0.2)
        glutSolidCube(50)
        glPopMatrix()
        
        glPopMatrix()

def draw_birds():
    """Draw animated birds"""
    for bird in birds:
        glPushMatrix()
        glTranslatef(bird.pos[0], bird.pos[1], bird.pos[2])
        
        # Body
        glColor3f(0.2, 0.2, 0.2)
        gluSphere(gluNewQuadric(), 5, 6, 6)
        
        # Wings
        glColor3f(0.3, 0.3, 0.3)
        glPushMatrix()
        glRotatef(bird.wing_angle, 0, 1, 0)
        glScalef(3, 0.2, 1)
        glutSolidCube(10)
        glPopMatrix()
        
        glPushMatrix()
        glRotatef(-bird.wing_angle, 0, 1, 0)
        glScalef(3, 0.2, 1)
        glutSolidCube(10)
        glPopMatrix()
        
        glPopMatrix()
        bird.update()

def draw_boost_points():
    """Draw boost pickup points"""
    for boost in boost_points:
        if not boost['collected']:
            x, y = boost['pos']
            
            glPushMatrix()
            glTranslatef(x, y, 20)
            
            # Rotating boost icon
            glRotatef(time.time() * 100 % 360, 0, 0, 1)
            
            # Boost star shape
            glColor3f(1, 1, 0)
            glBegin(GL_TRIANGLES)
            for i in range(8):
                angle1 = i * 45 * math.pi / 180
                angle2 = (i + 1) * 45 * math.pi / 180
                
                if i % 2 == 0:
                    r1, r2 = 20, 10
                else:
                    r1, r2 = 10, 20
                
                glVertex3f(0, 0, 0)
                glVertex3f(math.cos(angle1) * r1, math.sin(angle1) * r1, 0)
                glVertex3f(math.cos(angle2) * r2, math.sin(angle2) * r2, 0)
            glEnd()
            
            glPopMatrix()

def draw_speed_effects():
    """Draw speed lines from the sides of the car"""
    if abs(car_speed) > 200:
        glPushMatrix()
        glTranslatef(car_pos[0], car_pos[1], car_pos[2])
        glRotatef(car_rotation, 0, 0, 1)
        
        glColor4f(1, 1, 1, 0.4)
        glLineWidth(2)
        glBegin(GL_LINES)
        
        # Speed lines from the sides of the car
        for i in range(8):
            for side in [-20, 20]:  # Left and right sides
                # Random variation in line position
                y_offset = side + random.uniform(-5, 5)
                z_offset = random.uniform(0, 15)
                
                # Lines streaming backwards from car sides
                glVertex3f(20, y_offset, z_offset)  # Start near front
                glVertex3f(-50 - random.uniform(0, 50), y_offset + random.uniform(-10, 10), z_offset)
        
        glEnd()
        glPopMatrix()

def check_checkpoint():
    """Check if car passed through checkpoint"""
    global current_checkpoint, current_lap, lap_start_time, best_lap_time, game_state
    
    if current_checkpoint < len(checkpoints):
        checkpoint_x, checkpoint_y = checkpoints[current_checkpoint]['pos']
        dist = math.sqrt((car_pos[0] - checkpoint_x)**2 + (car_pos[1] - checkpoint_y)**2)
        
        if dist < checkpoint_radius + 50:
            current_checkpoint += 1
            
            # Completed a lap
            if current_checkpoint >= len(checkpoints):
                lap_time = time.time() - lap_start_time
                lap_times.append(lap_time)
                
                if lap_time < best_lap_time:
                    best_lap_time = lap_time
                
                if current_lap < total_laps:
                    current_lap += 1
                    current_checkpoint = 0
                    lap_start_time = time.time()
                else:
                    # Race finished
                    game_state = GAME_STATE_FINISHED

def check_boost_collision():
    """Check if car collected boost point"""
    global boost_active, boost_timer
    
    for boost in boost_points:
        if not boost['collected']:
            x, y = boost['pos']
            dist = math.sqrt((car_pos[0] - x)**2 + (car_pos[1] - y)**2)
            
            if dist < 40:
                boost['collected'] = True
                boost_active = True
                boost_timer = time.time() + 3  # 3 seconds boost

def check_track_position():
    """Check if car is on track"""
    global is_off_track
    
    dist_from_center = math.sqrt(car_pos[0]**2 + car_pos[1]**2)
    is_off_track = dist_from_center < 700 or dist_from_center > 900

def check_obstacle_collision():
    """Check collision with obstacles - reduce speed when off track"""
    global car_speed, car_pos, car_rotation
    
    car_radius = 25  # Car's collision radius
    
    for obstacle in obstacles:
        x, y = obstacle['pos']
        dist = math.sqrt((car_pos[0] - x)**2 + (car_pos[1] - y)**2)
        
        collision_distance = obstacle['radius'] + car_radius
        
        if dist < collision_distance:
            # Calculate bounce direction - push car away from obstacle
            if dist > 0:  # Avoid division by zero
                push_x = (car_pos[0] - x) / dist
                push_y = (car_pos[1] - y) / dist
            else:
                push_x = 1
                push_y = 0
            
            # Push car outside collision radius
            overlap = collision_distance - dist + 5  # Extra 5 units for safety
            car_pos[0] += push_x * overlap
            car_pos[1] += push_y * overlap
            
            # Significantly reduce speed when hitting obstacle off track
            if is_off_track:
                car_speed *= 0.2  # Heavy penalty when off track
            else:
                car_speed *= 0.5  # Normal penalty on track
            
            # Add small random rotation for realism
            car_rotation += random.uniform(-15, 15)
            
            # Prevent car from getting stuck
            if abs(car_speed) < 10:
                car_speed = -20  # Give a small reverse push

def update_car_physics():
    """Update car position and physics"""
    global car_pos, car_speed, boost_active, boost_timer, car_rotation
    
    # Check boost status
    if boost_active and time.time() > boost_timer:
        boost_active = False
    
    # Apply boost multiplier
    speed_multiplier = boost_speed_multiplier if boost_active else 1.0
    
    # Apply off-track penalty
    if is_off_track:
        speed_multiplier *= off_track_penalty
    
    # Handle continuous key presses
    if keys_pressed[b'w']:
        if car_speed < car_max_speed:
            car_speed += car_acceleration
            if car_speed > car_max_speed:
                car_speed = car_max_speed
    
    if keys_pressed[b's']:
        if car_speed > car_reverse_max:
            car_speed -= car_deceleration
            if car_speed < car_reverse_max:
                car_speed = car_reverse_max
    
    # Turning - only works when moving
    if abs(car_speed) > 5:
        turn_factor = 1.0 - (abs(car_speed) / car_max_speed) * 0.5
        if keys_pressed[b'a']:
            car_rotation += car_turn_speed * turn_factor
        if keys_pressed[b'd']:
            car_rotation -= car_turn_speed * turn_factor
    
    # Update position based on speed and rotation
    if car_speed != 0:
        angle_rad = car_rotation * math.pi / 180
        # Car moves forward along its facing direction (X-axis based)
        car_pos[0] += math.cos(angle_rad) * car_speed * 0.1 * speed_multiplier
        car_pos[1] += math.sin(angle_rad) * car_speed * 0.1 * speed_multiplier
    
    # Apply friction
    if not keys_pressed[b'w'] and not keys_pressed[b's']:
        car_speed *= car_friction
        if abs(car_speed) < 1:
            car_speed = 0

def keyboardListener(key, x, y):
    """Handle keyboard inputs - key press"""
    global game_state, camera_mode
    global race_start_time, lap_start_time, current_checkpoint, current_lap
    global boost_points, keys_pressed, car_pos, car_rotation, car_speed
    
    if key == b' ' and game_state == GAME_STATE_START:
        game_state = GAME_STATE_RACING
        race_start_time = time.time()
        lap_start_time = time.time()
        # Reset car to start position - facing along track
        car_pos = [800, 0, 5]
        car_rotation = 90  # Face upward along the track
    
    elif game_state == GAME_STATE_RACING:
        # Record key press
        if key in keys_pressed:
            keys_pressed[key] = True
        
        # Change camera
        if key == b'c':
            camera_mode = (camera_mode + 1) % 2
    
    # Restart game
    if key == b'r':
        # Reset everything
        game_state = GAME_STATE_START
        car_pos[:] = [800, 0, 5]
        car_rotation = 90  # Face upward along the track
        car_speed = 0
        current_checkpoint = 0
        current_lap = 1
        lap_times.clear()
        best_lap_time = float('inf')
        
        # Reset key states
        for k in keys_pressed:
            keys_pressed[k] = False
        
        # Reset boost points
        for boost in boost_points:
            boost['collected'] = False

def keyboardUpListener(key, x, y):
    """Handle keyboard inputs - key release"""
    global keys_pressed
    
    if key in keys_pressed:
        keys_pressed[key] = False

def specialKeyListener(key, x, y):
    """Handle arrow keys for camera adjustment - fixed"""
    global fovY
    
    # Adjust field of view with arrow keys for zoom effect
    if key == GLUT_KEY_UP:
        if fovY > 30:  # Zoom in
            fovY -= 5
    elif key == GLUT_KEY_DOWN:
        if fovY < 90:  # Zoom out
            fovY += 5
    elif key == GLUT_KEY_LEFT:
        pass  # Can add other camera adjustments if needed
    elif key == GLUT_KEY_RIGHT:
        pass  # Can add other camera adjustments if needed

def mouseListener(button, state, x, y):
    """Handle mouse inputs"""
    pass

def setupCamera():
    """Configure camera based on mode"""
    global camera_pos
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 3000)
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    if game_state == GAME_STATE_RACING:
        if camera_mode == CAMERA_FIRST_PERSON:
            # True first person - from driver's seat (no car visible)
            angle_rad = car_rotation * math.pi / 180
            
            # Camera positioned at driver's eye level
            cam_x = car_pos[0] + math.cos(angle_rad) * 5  # Slightly forward from center
            cam_y = car_pos[1] + math.sin(angle_rad) * 5
            cam_z = car_pos[2] + 15  # Driver's eye height
            
            # Look ahead in the direction car is facing
            look_x = cam_x + math.cos(angle_rad) * 100
            look_y = cam_y + math.sin(angle_rad) * 100
            look_z = car_pos[2] + 10
            
            gluLookAt(cam_x, cam_y, cam_z,
                     look_x, look_y, look_z,
                     0, 0, 1)
        else:
            # Third person - behind and above car (car visible)
            angle_rad = car_rotation * math.pi / 180
            
            # Camera positioned behind and above the car
            cam_distance = 150
            cam_height = 80
            cam_x = car_pos[0] - math.cos(angle_rad) * cam_distance
            cam_y = car_pos[1] - math.sin(angle_rad) * cam_distance
            cam_z = car_pos[2] + cam_height
            
            # Look at the car
            gluLookAt(cam_x, cam_y, cam_z,
                     car_pos[0], car_pos[1], car_pos[2] + 20,
                     0, 0, 1)
    else:
        # Overview camera for start/finish screens
        gluLookAt(1000, 1000, 800,
                 0, 0, 0,
                 0, 0, 1)

def idle():
    """Idle function for continuous updates"""
    global current_time
    
    if game_state == GAME_STATE_RACING:
        current_time = time.time() - race_start_time
        update_car_physics()
        check_checkpoint()
        check_track_position()
        check_obstacle_collision()
        check_boost_collision()
    
    glutPostRedisplay()

def showScreen():
    """Main display function"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    
    setupCamera()
    
    # Enable depth testing
    glEnable(GL_DEPTH_TEST)
    
    if game_state == GAME_STATE_START:
        # Start screen
        draw_environment()
        draw_sun()
        draw_clouds()
        draw_track()
        draw_sports_car()  # Show car at starting position
        
        for i, checkpoint in enumerate(checkpoints):
            draw_checkpoint_arch(checkpoint, i)
        for obstacle in obstacles:
            draw_obstacle(obstacle)
        
        draw_text(350, 500, "3D RACING CIRCUIT", GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(380, 450, "Press SPACE to Start")
        draw_text(350, 400, "Controls:")
        draw_text(350, 370, "W - Accelerate (Hold)")
        draw_text(350, 340, "S - Brake/Reverse (Hold)")
        draw_text(350, 310, "A/D - Turn Left/Right (Hold)")
        draw_text(350, 280, "C - Toggle Camera View")
        draw_text(350, 250, "R - Restart")
        draw_text(350, 220, "Arrow Keys - Zoom In/Out")
        draw_text(350, 180, "Complete 3 laps to win!")
        draw_text(350, 150, "Collect yellow boosts for speed!")
        draw_text(350, 120, "Rating: <60s Excellent, <90s Good")
        
    elif game_state == GAME_STATE_RACING:
        # Racing
        draw_environment()
        draw_sun()
        draw_clouds()
        draw_track()
        draw_birds()
        draw_boost_points()
        
        for i, checkpoint in enumerate(checkpoints):
            draw_checkpoint_arch(checkpoint, i)
        
        for obstacle in obstacles:
            draw_obstacle(obstacle)
        
        # Only draw car if in third person view
        if camera_mode == CAMERA_THIRD_PERSON:
            draw_sports_car()
        
        draw_speed_effects()
        
        # HUD
        draw_text(10, 770, f"Lap: {current_lap}/{total_laps}")
        draw_text(10, 740, f"Checkpoint: {current_checkpoint}/{len(checkpoints)}")
        draw_text(10, 710, f"Speed: {int(abs(car_speed))} km/h")
        draw_text(10, 680, f"Time: {int(current_time)}s")
        
        if best_lap_time != float('inf'):
            draw_text(10, 650, f"Best Lap: {int(best_lap_time)}s")
        
        # Camera mode indicator
        camera_text = "Camera: First Person" if camera_mode == CAMERA_FIRST_PERSON else "Camera: Third Person"
        draw_text(10, 620, camera_text)
        
        if is_off_track:
            draw_text(400, 400, "OFF TRACK!", GLUT_BITMAP_TIMES_ROMAN_24)
        
        if boost_active:
            draw_text(400, 450, "BOOST ACTIVE!", GLUT_BITMAP_TIMES_ROMAN_24)
        
        # First person view indicators
        if camera_mode == CAMERA_FIRST_PERSON:
            # Dashboard/speedometer effect
            draw_text(450, 100, f"{int(abs(car_speed))}", GLUT_BITMAP_TIMES_ROMAN_24)
            draw_text(450, 70, "KM/H")
    
    elif game_state == GAME_STATE_FINISHED:
        # Finish screen
        draw_environment()
        draw_sun()
        draw_clouds()
        draw_track()
        
        total_time = sum(lap_times)
        # Updated rating system: Excellent < 60s, Good < 90s, Try Again > 100s
        if total_time < 60:
            rating = "Excellent!"
        elif total_time < 90:
            rating = "Good!"
        else:
            rating = "Try Again!"
        
        draw_text(350, 500, "RACE FINISHED!", GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(350, 450, f"Total Time: {int(total_time)}s")
        draw_text(350, 420, f"Best Lap: {int(best_lap_time)}s")
        draw_text(350, 390, f"Rating: {rating}")
        draw_text(350, 350, "Lap Times:")
        
        for i, lap_time in enumerate(lap_times):
            draw_text(350, 320 - i * 30, f"  Lap {i + 1}: {int(lap_time)}s")
        
        draw_text(350, 200, "Press R to Restart")
    
    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"3D Racing Circuit Game")
    
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.5, 0.7, 1.0, 1.0)  # Sky blue background
    
    init_game()
    
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)  # Important for continuous movement
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    
    glutMainLoop()

if __name__ == "__main__":
    main()