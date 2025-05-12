import pygame
import random
import asyncio
import platform
from heapq import heappush, heappop
from typing import List, Tuple
import math

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
WIDTH, HEIGHT = 800, 600
GRID_SIZE = 20
GRID_WIDTH = WIDTH // GRID_SIZE
GRID_HEIGHT = HEIGHT // GRID_SIZE
FPS = 5

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
YELLOW = (255, 255, 0)
NEON_CYAN = (0, 255, 255)
NEON_PINK = (255, 0, 255)

# Fonts
FONT = pygame.font.SysFont('arial', 24)
TITLE_FONT = pygame.font.SysFont('arial', 48)

# Sounds
try:
    BITE_SOUND = pygame.mixer.Sound('big-crunch-2-90138.wav')  # Placeholder: replace with actual file
    COLLISION_SOUND = pygame.mixer.Sound('Voicy_TITANIC FLUTE.wav')
    pygame.mixer.music.load('80s-synthwave-vibe-loop-22508.mp3')  # Placeholder: replace with actual file
    pygame.mixer.music.set_volume(0.3)
except:
    # Fallback if sound files are missing
    BITE_SOUND = None
    COLLISION_SOUND = None
    pygame.mixer.music = None


class Snake:
    def __init__(self, color, is_ai=False):
        self.color = color
        self.is_ai = is_ai
        self.reset()

    def reset(self):
        self.body = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        self.direction = (1, 0)
        self.score = 0
        self.alive = True
        self.path = []  # Store A* path
        self.score_anim = 0  # For score bounce animation

    def move(self, food, other_snake):
        if not self.alive:
            return

        if self.is_ai:
            self.path = self.find_path(food, other_snake)
            if self.path and len(self.path) > 1:
                next_pos = self.path[1]
                dx = next_pos[0] - self.body[0][0]
                dy = next_pos[1] - self.body[0][1]
                self.direction = (dx, dy)
            else:
                directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
                valid_directions = [d for d in directions if d != (-self.direction[0], -self.direction[1])]
                self.direction = random.choice(valid_directions) if valid_directions else self.direction

        head = (self.body[0][0] + self.direction[0], self.body[0][1] + self.direction[1])
        if (head[0] < 0 or head[0] >= GRID_WIDTH or
                head[1] < 0 or head[1] >= GRID_HEIGHT or
                head in self.body[1:] or
                head in other_snake.body):
            self.alive = False
            if COLLISION_SOUND:
                COLLISION_SOUND.play()
            return

        self.body.insert(0, head)
        if head == food.position:
            self.score += 1
            self.score_anim = 10  # Trigger score bounce
            food.respawn(self, other_snake)
            if BITE_SOUND:
                BITE_SOUND.play()
        else:
            self.body.pop()

    def find_path(self, food, other_snake):
        start = self.body[0]
        goal = food.position
        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: abs(start[0] - goal[0]) + abs(start[1] - goal[1])}
        closed_set = set(self.body[1:] + other_snake.body +
                         [(x, y) for x in (-1, GRID_WIDTH) for y in range(GRID_HEIGHT)] +
                         [(x, y) for y in (-1, GRID_HEIGHT) for x in range(GRID_WIDTH)])

        while open_set:
            _, current = heappop(open_set)
            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if neighbor in closed_set:
                    continue
                tentative_g_score = g_score[current] + 1
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + abs(neighbor[0] - goal[0]) + abs(neighbor[1] - goal[1])
                    heappush(open_set, (f_score[neighbor], neighbor))
        return []


class Food:
    def __init__(self):
        self.position = (0, 0)
        self.respawn(None, None)
        self.anim_scale = 1.0

    def respawn(self, snake1, snake2):
        while True:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            if (x, y) not in (snake1.body if snake1 else []) and (x, y) not in (snake2.body if snake2 else []):
                self.position = (x, y)
                break

    def update(self):
        # Pulse animation
        t = pygame.time.get_ticks() / 1000
        self.anim_scale = 1.0 + 0.1 * math.sin(t * 5)


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Snake AI vs Player (A* Enhanced)")
        self.clock = pygame.time.Clock()
        self.player_snake = Snake(BLUE)
        self.ai_snake = Snake(GREEN, is_ai=True)
        self.food = Food()
        self.state = "start"  # start, playing, paused, over
        self.winner = None
        self.games_played = 0
        self.ai_success_rate = 0.0
        self.transition_alpha = 0
        self.background_colors = [(30, 0, 60), (60, 0, 120)]  # Gradient colors
        if pygame.mixer.music:
            pygame.mixer.music.play(-1)  # Loop background music

    def draw_background(self):
        # Dynamic color-shifting gradient
        t = pygame.time.get_ticks() / 10000
        c1 = (int(30 + 20 * math.sin(t)), 0, int(60 + 20 * math.cos(t)))
        c2 = (int(60 + 20 * math.cos(t)), 0, int(120 + 20 * math.sin(t)))
        surface = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            alpha = y / HEIGHT
            color = tuple(int(c1[i] * (1 - alpha) + c2[i] * alpha) for i in range(3))
            pygame.draw.line(surface, color, (0, y), (WIDTH, y))
        self.screen.blit(surface, (0, 0))

    def draw_neon_grid(self):
        surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for x in range(0, WIDTH, GRID_SIZE):
            pygame.draw.line(surface, (*NEON_CYAN, 100), (x, 0), (x, HEIGHT), 2)
        for y in range(0, HEIGHT, GRID_SIZE):
            pygame.draw.line(surface, (*NEON_CYAN, 100), (0, y), (WIDTH, y), 2)
        self.screen.blit(surface, (0, 0))

    def draw_snake(self, snake):
        surface = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        for i, segment in enumerate(snake.body):
            # Gradient glow effect
            alpha = 255 - i * 10
            if alpha < 50:
                alpha = 50
            pygame.draw.rect(surface, (*snake.color, alpha), (0, 0, GRID_SIZE, GRID_SIZE))
            pygame.draw.rect(surface, WHITE, (0, 0, GRID_SIZE, GRID_SIZE), 1)
            self.screen.blit(surface, (segment[0] * GRID_SIZE, segment[1] * GRID_SIZE))
            surface.fill((0, 0, 0, 0))

    def draw(self):
        self.draw_background()

        if self.state in ["playing", "paused"]:
            self.draw_neon_grid()

            # Draw snakes with glow
            self.draw_snake(self.player_snake)
            self.draw_snake(self.ai_snake)

            # Draw animated food
            surface = pygame.Surface((GRID_SIZE * 2, GRID_SIZE * 2), pygame.SRCALPHA)
            scale = self.food.anim_scale
            size = int(GRID_SIZE * scale)
            pygame.draw.ellipse(surface, RED, ((GRID_SIZE * 2 - size) // 2, (GRID_SIZE * 2 - size) // 2, size, size))
            self.screen.blit(surface, (self.food.position[0] * GRID_SIZE - (GRID_SIZE * (scale - 1)) / 2,
                                       self.food.position[1] * GRID_SIZE - (GRID_SIZE * (scale - 1)) / 2))

            # Draw A* path
            if self.ai_snake.alive and self.ai_snake.path:
                for pos in self.ai_snake.path[1:]:
                    pygame.draw.circle(self.screen, (*YELLOW, 150),
                                       (pos[0] * GRID_SIZE + GRID_SIZE // 2, pos[1] * GRID_SIZE + GRID_SIZE // 2),
                                       GRID_SIZE // 4)

            # Draw scores with bounce animation
            player_score = FONT.render(f"Player: {self.player_snake.score}", True, NEON_CYAN)
            ai_score = FONT.render(f"AI: {self.ai_snake.score}", True, NEON_PINK)
            player_offset = 10 * math.sin(self.player_snake.score_anim) if self.player_snake.score_anim > 0 else 0
            ai_offset = 10 * math.sin(self.ai_snake.score_anim) if self.ai_snake.score_anim > 0 else 0
            self.screen.blit(player_score, (10, 10 + player_offset))
            self.screen.blit(ai_score, (10, 40 + ai_offset))
            games = FONT.render(f"Games: {self.games_played}", True, WHITE)
            success_rate = FONT.render(f"AI Success: {self.ai_success_rate:.1%}", True, WHITE)
            self.screen.blit(games, (WIDTH - 150, 10))
            self.screen.blit(success_rate, (WIDTH - 150, 40))

            # Update animations
            if self.player_snake.score_anim > 0:
                self.player_snake.score_anim -= 1
            if self.ai_snake.score_anim > 0:
                self.ai_snake.score_anim -= 1
            self.food.update()

        if self.state == "start":
            title = TITLE_FONT.render("Neon Snake Battle", True, NEON_CYAN)
            start_text = FONT.render("Press S to Start", True, WHITE)
            instr_text = FONT.render("Arrow Keys: Move | P: Pause | R: Restart", True, WHITE)
            exit_text = FONT.render("Press Q to Exit", True, WHITE)
            self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 3))
            self.screen.blit(start_text, (WIDTH // 2 - start_text.get_width() // 2, HEIGHT // 2))
            self.screen.blit(instr_text, (WIDTH // 2 - instr_text.get_width() // 2, HEIGHT // 2 + 50))
            self.screen.blit(exit_text, (WIDTH // 2 - exit_text.get_width() // 2, HEIGHT // 2 + 100))

        if self.state == "paused":
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(150)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
            pause_text = TITLE_FONT.render("Paused", True, NEON_PINK)
            resume_text = FONT.render("Press P to Resume", True, WHITE)
            self.screen.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - 50))
            self.screen.blit(resume_text, (WIDTH // 2 - resume_text.get_width() // 2, HEIGHT // 2 + 50))

        if self.state == "over":
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(self.transition_alpha)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
            winner_text = TITLE_FONT.render(f"{self.winner} Wins!", True, NEON_CYAN)
            restart_text = FONT.render("Press R to Restart", True, WHITE)
            self.screen.blit(winner_text, (WIDTH // 2 - winner_text.get_width() // 2, HEIGHT // 2 - 50))
            self.screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 50))
            self.transition_alpha = min(self.transition_alpha + 10, 200)

        pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return False
                if self.state == "start":
                    if event.key == pygame.K_s:
                        self.state = "playing"
                elif self.state == "playing":
                    if event.key == pygame.K_p:
                        self.state = "paused"
                    elif event.key == pygame.K_UP and self.player_snake.direction != (0, 1):
                        self.player_snake.direction = (0, -1)
                    elif event.key == pygame.K_DOWN and self.player_snake.direction != (0, -1):
                        self.player_snake.direction = (0, 1)
                    elif event.key == pygame.K_LEFT and self.player_snake.direction != (1, 0):
                        self.player_snake.direction = (-1, 0)
                    elif event.key == pygame.K_RIGHT and self.player_snake.direction != (-1, 0):
                        self.player_snake.direction = (1, 0)
                elif self.state == "paused":
                    if event.key == pygame.K_p:
                        self.state = "playing"
                elif self.state == "over":
                    if event.key == pygame.K_r:
                        self.reset()
        return True

    def reset(self):
        if self.games_played > 0:
            self.ai_success_rate = (self.ai_success_rate * self.games_played +
                                    (1 if self.ai_snake.score > 0 else 0)) / (self.games_played + 1)
        self.games_played += 1
        self.player_snake.reset()
        self.ai_snake.reset()
        self.food.respawn(self.player_snake, self.ai_snake)
        self.state = "playing"
        self.winner = None
        self.transition_alpha = 0

    def update_loop(self):
        if self.state == "playing":
            self.player_snake.move(self.food, self.ai_snake)
            self.ai_snake.move(self.food, self.player_snake)

            if not self.player_snake.alive and not self.ai_snake.alive:
                self.state = "over"
                self.winner = "AI" if self.ai_snake.score > self.player_snake.score else "Player" if self.player_snake.score > self.ai_snake.score else "Tie"
            elif not self.player_snake.alive:
                self.state = "over"
                self.winner = "AI"
            elif not self.ai_snake.alive:
                self.state = "over"
                self.winner = "Player"

        self.draw()

    def setup(self):
        self.food.respawn(self.player_snake, self.ai_snake)


async def main():
    game = Game()
    game.setup()
    running = True
    while running:
        running = game.handle_events()
        game.update_loop()
        await asyncio.sleep(1.0 / FPS)


if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())