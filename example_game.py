#!/usr/bin/env python3
"""
Example Pygame Game for Streaming
A simple bouncing ball demo that works great with RTMP streaming
"""

import pygame
import random
import os
import sys

# Initialize Pygame
pygame.init()

# Set up display - use environment variable if available (for streaming)
if os.environ.get('DISPLAY'):
    # Running on virtual display (streaming mode)
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Streaming Game - Live!")
else:
    # Running locally
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Local Game")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (255, 0, 255)
COLORS = [RED, BLUE, GREEN, YELLOW, PURPLE]

# Ball properties
class Ball:
    def __init__(self):
        self.x = random.randint(50, screen.get_width() - 50)
        self.y = random.randint(50, screen.get_height() - 50)
        self.dx = random.choice([-5, -4, -3, 3, 4, 5])
        self.dy = random.choice([-5, -4, -3, 3, 4, 5])
        self.radius = random.randint(20, 40)
        self.color = random.choice(COLORS)
    
    def move(self):
        self.x += self.dx
        self.y += self.dy
        
        # Bounce off walls
        if self.x - self.radius <= 0 or self.x + self.radius >= screen.get_width():
            self.dx = -self.dx
        if self.y - self.radius <= 0 or self.y + self.radius >= screen.get_height():
            self.dy = -self.dy
    
    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)

# Create balls
balls = [Ball() for _ in range(8)]

# Game loop
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)
running = True
frame_count = 0

print("🎮 Pygame streaming demo started!")
print(f"Display: {screen.get_size()}")
print("Press SPACE to add more balls, ESC or close window to quit")

while running:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                # Add a new ball
                balls.append(Ball())
                print(f"Added ball! Total balls: {len(balls)}")
    
    # Update
    for ball in balls:
        ball.move()
    
    # Draw
    screen.fill(WHITE)
    
    # Draw balls
    for ball in balls:
        ball.draw(screen)
    
    # Draw UI
    frame_count += 1
    fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0, 0, 0))
    balls_text = font.render(f"Balls: {len(balls)}", True, (0, 0, 0))
    frame_text = font.render(f"Frame: {frame_count}", True, (0, 0, 0))
    
    if os.environ.get('DISPLAY'):
        status_text = font.render("🔴 LIVE STREAMING", True, (255, 0, 0))
        screen.blit(status_text, (10, 10))
    
    screen.blit(fps_text, (10, 50))
    screen.blit(balls_text, (10, 90))
    screen.blit(frame_text, (10, 130))
    
    # Instructions
    if frame_count < 300:  # Show for first 5 seconds
        inst_text = font.render("SPACE: Add Ball | ESC: Quit", True, (100, 100, 100))
        text_rect = inst_text.get_rect(center=(screen.get_width()//2, screen.get_height() - 30))
        screen.blit(inst_text, text_rect)
    
    # Update display
    pygame.display.flip()
    clock.tick(60)  # 60 FPS

print("🎮 Game ended!")
pygame.quit()
sys.exit()
