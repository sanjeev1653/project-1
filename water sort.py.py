import pygame
import sys
import random
import os
import json
from pygame.locals import *

# Initialize pygame
pygame.init()
pygame.mixer.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TUBE_WIDTH = 60
TUBE_HEIGHT = 200
TUBE_CAPACITY = 4
COLOR_HEIGHT = TUBE_HEIGHT // TUBE_CAPACITY
MARGIN = 20
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (240, 240, 240)
TUBE_COLOR = (220, 220, 220)
BUTTON_COLOR = (100, 150, 200)
BUTTON_HOVER = (120, 170, 220)
LOCKED_COLOR = (150, 150, 150)

COLORS = [
    (255, 0, 0),    # Red
    (0, 255, 0),    # Green
    (0, 0, 255),    # Blue
    (255, 255, 0),  # Yellow
    (255, 0, 255),  # Purple
    (0, 255, 255),  # Cyan
    (255, 128, 0),  # Orange
    (128, 0, 128),  # Indigo
    (128, 128, 0),  # Olive
    (0, 128, 128),  # Teal
]

# Sound effects
try:
    POUR_SOUND = pygame.mixer.Sound("pour.wav") if os.path.exists("pour.wav") else None
    WIN_SOUND = pygame.mixer.Sound("win.wav") if os.path.exists("win.wav") else None
    CLICK_SOUND = pygame.mixer.Sound("click.wav") if os.path.exists("click.wav") else None
except:
    POUR_SOUND = None
    WIN_SOUND = None
    CLICK_SOUND = None

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Water Sort Puzzle')
clock = pygame.time.Clock()

# Level configuration
MAX_LEVELS = 50
LEVELS_PER_PAGE = 12
SAVE_FILE = "water_sort_save.json"

class Button:
    def __init__(self, x, y, width, height, text, action=None, enabled=True):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.hover = False
        self.enabled = enabled
    
    def draw(self, surface):
        if not self.enabled:
            color = LOCKED_COLOR
        else:
            color = BUTTON_HOVER if self.hover else BUTTON_COLOR
        
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, BLACK, self.rect, 2, border_radius=10)
        
        font = pygame.font.SysFont(None, 30)
        text_color = BLACK if self.enabled else (100, 100, 100)
        text_surf = font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def check_hover(self, pos):
        self.hover = self.rect.collidepoint(pos) and self.enabled
        return self.hover
    
    def handle_click(self, pos):
        if self.rect.collidepoint(pos) and self.action and self.enabled:
            if CLICK_SOUND:
                CLICK_SOUND.play()
            return self.action()
        return None

class Tube:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.colors = []
        self.selected = False
    
    def add_color(self, color):
        if len(self.colors) < TUBE_CAPACITY:
            self.colors.append(color)
    
    def is_empty(self):
        return len(self.colors) == 0
    
    def is_full(self):
        return len(self.colors) == TUBE_CAPACITY
    
    def is_complete(self):
        if self.is_empty():
            return False
        if len(self.colors) < TUBE_CAPACITY:
            return False
        first_color = self.colors[0]
        return all(color == first_color for color in self.colors)
    
    def top_color(self):
        if self.is_empty():
            return None
        return self.colors[-1]
    
    def top_color_count(self):
        if self.is_empty():
            return 0
        top_color = self.top_color()
        count = 0
        for color in reversed(self.colors):
            if color == top_color:
                count += 1
            else:
                break
        return count
    
    def can_receive(self, color, amount):
        if self.is_empty():
            return amount <= TUBE_CAPACITY
        if self.top_color() != color:
            return False
        return len(self.colors) + amount <= TUBE_CAPACITY
    
    def pour_to(self, other_tube):
        if self.is_empty() or other_tube.is_full():
            return False
        
        top_color = self.top_color()
        top_count = self.top_color_count()
        
        available_space = TUBE_CAPACITY - len(other_tube.colors)
        pour_amount = min(top_count, available_space)
        
        if other_tube.is_empty() or other_tube.top_color() == top_color:
            for _ in range(pour_amount):
                other_tube.add_color(self.colors.pop())
            if POUR_SOUND:
                POUR_SOUND.play()
            return True
        return False
    
    def draw(self, surface):
        # Draw tube outline with curved bottom
        pygame.draw.rect(surface, TUBE_COLOR, (self.x, self.y, TUBE_WIDTH, TUBE_HEIGHT - 10), 2)
        pygame.draw.arc(surface, TUBE_COLOR, 
                       (self.x, self.y + TUBE_HEIGHT - 20, TUBE_WIDTH, 20), 
                       0, 3.14, 2)
        
        # Draw tube contents with liquid effect
        for i, color in enumerate(self.colors):
            # Create gradient effect for the liquid
            darker_color = tuple(max(0, c - 40) for c in color)
            rect = pygame.Rect(self.x + 2, self.y + TUBE_HEIGHT - (i+1)*COLOR_HEIGHT - 2, 
                             TUBE_WIDTH - 4, COLOR_HEIGHT)
            
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, darker_color, rect, 1)
            pygame.draw.line(surface, (255, 255, 255, 100), 
                           (rect.left + 2, rect.top + 2), 
                           (rect.right - 2, rect.top + 2), 1)
        
        # Draw selection highlight
        if self.selected:
            pygame.draw.rect(surface, (0, 200, 0), 
                           (self.x - 4, self.y - 4, TUBE_WIDTH + 8, TUBE_HEIGHT + 8), 
                           3, border_radius=5)

class Game:
    def __init__(self):
        self.level = 1
        self.max_unlocked = 1
        self.moves = 0
        self.game_state = "menu"  # menu, playing, win, level_select
        self.selected_tube = None
        self.history = []
        self.level_page = 0
        self.load_game()
        
        # Menu buttons
        self.buttons = [
            Button(SCREEN_WIDTH//2 - 100, 200, 200, 50, "Play", self.show_level_select),
            Button(SCREEN_WIDTH//2 - 100, 270, 200, 50, "Level Select", self.show_level_select),
            Button(SCREEN_WIDTH//2 - 100, 340, 200, 50, "Quit", self.quit_game)
        ]
    
    def load_game(self):
        try:
            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, 'r') as f:
                    data = json.load(f)
                    self.max_unlocked = data.get('max_unlocked', 1)
                    # Ensure we don't exceed our MAX_LEVELS
                    if self.max_unlocked > MAX_LEVELS:
                        self.max_unlocked = MAX_LEVELS
        except:
            self.max_unlocked = 1
    
    def save_game(self):
        data = {
            'max_unlocked': min(self.max_unlocked, MAX_LEVELS)
        }
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f)
    
    def setup_level(self, level):
        self.tubes = []
        self.moves = 0
        self.history = []
        self.selected_tube = None
        self.game_state = "playing"
        self.level = level
        
        # Dynamic difficulty progression
        base_colors = 4
        color_increase = (level - 1) // 5  # Increase colors every 5 levels
        num_colors = min(base_colors + color_increase, len(COLORS))
        
        base_tubes = num_colors + 2
        tube_increase = (level - 1) // 3  # Increase tubes every 3 levels
        num_tubes = min(base_tubes + tube_increase, 12)  # Max 12 tubes
        
        # Calculate tube positions
        tubes_per_row = min(num_tubes, 8)
        start_x = (SCREEN_WIDTH - tubes_per_row * (TUBE_WIDTH + MARGIN)) // 2
        
        for i in range(num_tubes):
            row = i // 8
            col = i % 8
            x = start_x + col * (TUBE_WIDTH + MARGIN)
            y = 100 + row * (TUBE_HEIGHT + MARGIN)
            self.tubes.append(Tube(x, y))
        
        # Fill tubes with colors
        color_pool = []
        colors_to_use = random.sample(COLORS, num_colors)
        for color in colors_to_use:
            color_pool.extend([color] * TUBE_CAPACITY)
        
        random.shuffle(color_pool)
        
        # Distribute colors to tubes (leave some empty)
        tubes_to_fill = num_tubes - 2  # Leave 2 empty tubes
        for i in range(tubes_to_fill):
            for _ in range(TUBE_CAPACITY):
                if color_pool:
                    self.tubes[i].add_color(color_pool.pop())
    
    def save_state(self):
        state = []
        for tube in self.tubes:
            state.append(list(tube.colors))
        self.history.append((state, self.moves))
        if len(self.history) > 10:
            self.history.pop(0)
    
    def undo(self):
        if self.history and self.game_state == "playing":
            state, moves = self.history.pop()
            for i, tube in enumerate(self.tubes):
                tube.colors = list(state[i])
                tube.selected = False
            self.moves = moves
            self.selected_tube = None
            return True
        return False
    
    def handle_click(self, pos):
        if self.game_state == "menu":
            for button in self.buttons:
                result = button.handle_click(pos)
                if result is not None:
                    return
        elif self.game_state == "level_select":
            for button in self.level_buttons:
                result = button.handle_click(pos)
                if result is not None:
                    return
            
            # Handle page navigation
            if self.prev_page_btn.check_hover(pos) and pygame.mouse.get_pressed()[0]:
                self.prev_page_btn.handle_click(pos)
            if self.next_page_btn.check_hover(pos) and pygame.mouse.get_pressed()[0]:
                self.next_page_btn.handle_click(pos)
            
            # Back button
            if self.back_btn.check_hover(pos) and pygame.mouse.get_pressed()[0]:
                self.back_btn.handle_click(pos)
        elif self.game_state == "playing":
            for tube in self.tubes:
                if (tube.x <= pos[0] <= tube.x + TUBE_WIDTH and 
                    tube.y <= pos[1] <= tube.y + TUBE_HEIGHT):
                    
                    if self.selected_tube is None:
                        if not tube.is_empty():
                            self.save_state()
                            tube.selected = True
                            self.selected_tube = tube
                    else:
                        if tube == self.selected_tube:
                            tube.selected = False
                            self.selected_tube = None
                            self.history.pop()
                        else:
                            if self.selected_tube.pour_to(tube):
                                self.moves += 1
                                self.selected_tube.selected = False
                                self.selected_tube = None
                                
                                if self.check_win():
                                    self.game_state = "level_complete"
                                    if self.level == self.max_unlocked and self.level < MAX_LEVELS:
                                        self.max_unlocked += 1
                                        self.save_game()
                                    if WIN_SOUND:
                                        WIN_SOUND.play()
                            else:
                                self.selected_tube.selected = False
                                if not tube.is_empty():
                                    self.save_state()
                                    tube.selected = True
                                    self.selected_tube = tube
                                else:
                                    self.selected_tube = None
                                    self.history.pop()
                    break
            
            # Check buttons
            mouse_pos = pygame.mouse.get_pos()
            if self.undo_btn.check_hover(mouse_pos) and pygame.mouse.get_pressed()[0]:
                self.undo_btn.handle_click(mouse_pos)
            if self.menu_btn.check_hover(mouse_pos) and pygame.mouse.get_pressed()[0]:
                self.menu_btn.handle_click(mouse_pos)
        elif self.game_state == "level_complete":
            for button in self.win_buttons:
                result = button.handle_click(pos)
                if result is not None:
                    return
    
    def check_win(self):
        for tube in self.tubes:
            if not tube.is_empty() and not tube.is_complete():
                return False
        return True
    
    def show_level_select(self):
        self.game_state = "level_select"
        self.level_page = 0
        self.update_level_buttons()
    
    def update_level_buttons(self):
        self.level_buttons = []
        start_level = self.level_page * LEVELS_PER_PAGE + 1
        end_level = min((self.level_page + 1) * LEVELS_PER_PAGE, MAX_LEVELS)
        
        # Calculate grid position
        cols = 4
        rows = 3
        button_size = 70
        margin = 20
        start_x = (SCREEN_WIDTH - (cols * button_size + (cols - 1) * margin)) // 2
        start_y = 150
        
        # Create level buttons
        for i in range(start_level, end_level + 1):
            row = (i - start_level) // cols
            col = (i - start_level) % cols
            x = start_x + col * (button_size + margin)
            y = start_y + row * (button_size + margin)
            
            enabled = i <= self.max_unlocked
            action = lambda lvl=i: self.start_level(lvl)
            self.level_buttons.append(Button(x, y, button_size, button_size, str(i), action, enabled))
        
        # Create navigation buttons
        self.prev_page_btn = Button(50, SCREEN_HEIGHT - 70, 120, 50, "Previous", 
                                  lambda: self.change_page(-1), self.level_page > 0)
        self.next_page_btn = Button(SCREEN_WIDTH - 170, SCREEN_HEIGHT - 70, 120, 50, "Next", 
                                   lambda: self.change_page(1), (self.level_page + 1) * LEVELS_PER_PAGE < MAX_LEVELS)
        self.back_btn = Button(SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT - 70, 120, 50, "Back", self.show_menu)
    
    def change_page(self, delta):
        new_page = self.level_page + delta
        max_pages = (MAX_LEVELS - 1) // LEVELS_PER_PAGE
        if 0 <= new_page <= max_pages:
            self.level_page = new_page
            self.update_level_buttons()
    
    def start_level(self, level):
        self.setup_level(level)
    
    def next_level(self):
        if self.level < MAX_LEVELS:
            self.setup_level(self.level + 1)
        else:
            self.show_menu()
    
    def show_menu(self):
        self.game_state = "menu"
    
    def quit_game(self):
        pygame.quit()
        sys.exit()
    
    def draw(self, surface):
        surface.fill(LIGHT_GRAY)
        
        if self.game_state == "menu":
            self.draw_menu(surface)
        elif self.game_state == "playing":
            self.draw_game(surface)
        elif self.game_state == "level_complete":
            self.draw_level_complete(surface)
        elif self.game_state == "level_select":
            self.draw_level_select(surface)
        
        pygame.display.flip()
    
    def draw_menu(self, surface):
        # Title
        font = pygame.font.SysFont(None, 72)
        title = font.render("Water Sort Puzzle", True, BLACK)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        
        # Buttons
        for button in self.buttons:
            button.draw(surface)
    
    def draw_game(self, surface):
        # Level and moves info
        font = pygame.font.SysFont(None, 36)
        level_text = font.render(f"Level: {self.level}", True, BLACK)
        moves_text = font.render(f"Moves: {self.moves}", True, BLACK)
        surface.blit(level_text, (20, 20))
        surface.blit(moves_text, (20, 60))
        
        # Tubes
        for tube in self.tubes:
            tube.draw(surface)
        
        # Buttons
        self.undo_btn = Button(SCREEN_WIDTH - 120, 20, 100, 40, "Undo", self.undo)
        self.menu_btn = Button(SCREEN_WIDTH - 120, 70, 100, 40, "Menu", self.show_menu)
        
        mouse_pos = pygame.mouse.get_pos()
        self.undo_btn.check_hover(mouse_pos)
        self.menu_btn.check_hover(mouse_pos)
        
        self.undo_btn.draw(surface)
        self.menu_btn.draw(surface)
    
    def draw_level_complete(self, surface):
        # Transparent overlay
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        surface.blit(s, (0, 0))
        
        # Win message
        font = pygame.font.SysFont(None, 72)
        win_text = font.render("Level Complete!", True, WHITE)
        surface.blit(win_text, (SCREEN_WIDTH // 2 - win_text.get_width() // 2, 150))
        
        # Stats
        font = pygame.font.SysFont(None, 48)
        stats_text = font.render(f"Moves: {self.moves}", True, WHITE)
        surface.blit(stats_text, (SCREEN_WIDTH // 2 - stats_text.get_width() // 2, 250))
        
        # Buttons
        next_enabled = self.level < self.max_unlocked
        self.win_buttons = [
            Button(SCREEN_WIDTH//2 - 220, 350, 200, 50, "Next Level", self.next_level, next_enabled),
            Button(SCREEN_WIDTH//2 + 20, 350, 200, 50, "Main Menu", self.show_menu)
        ]
        
        mouse_pos = pygame.mouse.get_pos()
        for button in self.win_buttons:
            button.check_hover(mouse_pos)
            button.draw(surface)
    
    def draw_level_select(self, surface):
        # Title
        font = pygame.font.SysFont(None, 48)
        title = font.render("Select Level", True, BLACK)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        
        # Page info
        page_text = font.render(f"Page {self.level_page + 1}/{(MAX_LEVELS - 1) // LEVELS_PER_PAGE + 1}", True, BLACK)
        surface.blit(page_text, (SCREEN_WIDTH // 2 - page_text.get_width() // 2, 100))
        
        # Level buttons
        for button in self.level_buttons:
            button.draw(surface)
        
        # Navigation buttons
        self.prev_page_btn.draw(surface)
        self.next_page_btn.draw(surface)
        self.back_btn.draw(surface)

def main():
    game = Game()
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    game.handle_click(event.pos)
            elif event.type == MOUSEMOTION:
                if game.game_state in ["menu", "level_complete"]:
                    for button in game.buttons:
                        button.check_hover(mouse_pos)
                elif game.game_state == "level_select":
                    for button in game.level_buttons:
                        button.check_hover(mouse_pos)
                    game.prev_page_btn.check_hover(mouse_pos)
                    game.next_page_btn.check_hover(mouse_pos)
                    game.back_btn.check_hover(mouse_pos)
        
        game.draw(screen)
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
