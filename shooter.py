import io
import math
import random
import struct
import wave

import pygame


WIDTH = 600
HEIGHT = 700
FPS = 60
PLAYER_SPEED = 360
PLAYER_Y = HEIGHT - 70
LEVEL_GOALS = (8, 12, 16, 20, 24)
BACKGROUND = (8, 13, 32)
CYAN = (84, 225, 255)
WHITE = (240, 245, 255)


def make_tone(start_frequency, end_frequency, duration_ms):
    sample_rate = 22050
    sample_count = sample_rate * duration_ms // 1000
    frames = bytearray()

    for index in range(sample_count):
        progress = index / sample_count
        frequency = start_frequency + (end_frequency - start_frequency) * progress
        phase = 2 * math.pi * (
            start_frequency * index / sample_rate
            + (end_frequency - start_frequency) * index * progress / (2 * sample_rate)
        )
        sample = int(12000 * (1 - progress) * math.sin(phase))
        frames.extend(struct.pack("<h", sample))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as sound_file:
        sound_file.setnchannels(1)
        sound_file.setsampwidth(2)
        sound_file.setframerate(sample_rate)
        sound_file.writeframes(frames)
    buffer.seek(0)
    return pygame.mixer.Sound(file=buffer)


class ShooterGame:
    def __init__(self):
        pygame.init()
        self.sound_enabled = True
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.sounds = {
                "shoot": make_tone(900, 420, 65),
                "hit": make_tone(520, 160, 150),
            }
        except pygame.error as error:
            print(f"Audio is unavailable: {error}")
            self.sound_enabled = False
            self.sounds = {}

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Star Defender")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 23)
        self.title_font = pygame.font.Font(None, 72)
        self.stars = [
            (random.randrange(WIDTH), random.randrange(HEIGHT), random.choice((1, 1, 2)))
            for _ in range(90)
        ]
        self.state = "menu"
        self.running = True
        self.score = 0
        self.level = 1
        self.reset_level()

    def reset_level(self):
        self.player_x = WIDTH / 2
        self.bullets = []
        self.enemies = []
        self.enemies_defeated = 0
        self.spawn_clock = 0
        self.shoot_cooldown = 0

    def start_game(self):
        self.score = 0
        self.level = 1
        self.reset_level()
        self.state = "playing"

    def play_sound(self, sound_name):
        if self.sound_enabled:
            self.sounds[sound_name].play()

    def spawn_enemy(self):
        size = random.randint(15, 23)
        speed = random.uniform(115, 175) + (self.level - 1) * 32
        self.enemies.append({
            "x": random.randint(size, WIDTH - size),
            "y": -size,
            "size": size,
            "speed": speed,
        })

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif self.state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_game()
            elif self.state in ("level_complete", "game_over", "victory"):
                if event.key == pygame.K_m:
                    self.state = "menu"
                elif self.state == "level_complete" and event.key in (
                    pygame.K_RETURN, pygame.K_SPACE
                ):
                    self.level += 1
                    self.reset_level()
                    self.state = "playing"
                elif self.state in ("game_over", "victory") and event.key in (
                    pygame.K_RETURN, pygame.K_SPACE
                ):
                    self.start_game()

    def update(self, delta_time):
        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player_x -= PLAYER_SPEED * delta_time
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player_x += PLAYER_SPEED * delta_time
        self.player_x = max(22, min(WIDTH - 22, self.player_x))

        self.shoot_cooldown = max(0, self.shoot_cooldown - delta_time)
        if keys[pygame.K_SPACE] and self.shoot_cooldown == 0:
            self.play_sound("shoot")
            self.bullets.append({"x": self.player_x, "y": PLAYER_Y - 22})
            self.shoot_cooldown = 0.18
        self.spawn_clock += delta_time
        spawn_interval = max(0.35, 0.9 - (self.level - 1) * 0.1)
        if (self.enemies_defeated + len(self.enemies) < LEVEL_GOALS[self.level - 1]
                and self.spawn_clock >= spawn_interval):
            self.spawn_enemy()
            self.spawn_clock = 0

        for bullet in self.bullets:
            bullet["y"] -= 680 * delta_time
        self.bullets = [bullet for bullet in self.bullets if bullet["y"] > 0]

        player_rect = pygame.Rect(self.player_x - 17, PLAYER_Y - 20, 34, 40)
        survivors = []
        for enemy in self.enemies:
            enemy["y"] += enemy["speed"] * delta_time
            enemy_rect = pygame.Rect(
                enemy["x"] - enemy["size"],
                enemy["y"] - enemy["size"],
                enemy["size"] * 2,
                enemy["size"] * 2,
            )
            hit_bullet = next(
                (
                    bullet for bullet in self.bullets
                    if enemy_rect.colliderect(
                        pygame.Rect(bullet["x"] - 3, bullet["y"] - 8, 6, 16)
                    )
                ),
                None,
            )
            if hit_bullet is not None:
                self.bullets.remove(hit_bullet)
                self.play_sound("hit")
                self.enemies_defeated += 1
                self.score += 10
            elif enemy_rect.colliderect(player_rect) or enemy["y"] > HEIGHT + enemy["size"]:
                self.state = "game_over"
                return
            else:
                survivors.append(enemy)
        self.enemies = survivors

        if (self.enemies_defeated >= LEVEL_GOALS[self.level - 1]
                and not self.enemies):
            self.state = "victory" if self.level == len(LEVEL_GOALS) else "level_complete"

    def draw_text(self, text, font, color, center):
        image = font.render(text, True, color)
        self.screen.blit(image, image.get_rect(center=center))

    def draw_background(self):
        self.screen.fill(BACKGROUND)
        for x, y, size in self.stars:
            pygame.draw.circle(self.screen, (130, 155, 210), (x, y), size)

    def draw_player(self):
        x = int(self.player_x)
        pygame.draw.polygon(
            self.screen, CYAN,
            ((x, PLAYER_Y - 22), (x - 18, PLAYER_Y + 18),
             (x, PLAYER_Y + 9), (x + 18, PLAYER_Y + 18)),
        )
        pygame.draw.polygon(
            self.screen, WHITE,
            ((x, PLAYER_Y - 22), (x - 18, PLAYER_Y + 18),
             (x, PLAYER_Y + 9), (x + 18, PLAYER_Y + 18)), 2,
        )

    def draw_game(self):
        self.draw_background()
        if self.state == "menu":
            self.draw_text("STAR DEFENDER", self.title_font, CYAN, (WIDTH // 2, 245))
            self.draw_text("Five levels. One ship. Save the galaxy.",
                           self.small_font, WHITE, (WIDTH // 2, 310))
            self.draw_text("Press ENTER or SPACE to start",
                           self.font, WHITE, (WIDTH // 2, 410))
            self.draw_text("Move: A/D or arrows    Shoot: SPACE    Quit: ESC",
                           self.small_font, (169, 190, 222), (WIDTH // 2, 465))
        elif self.state == "playing":
            self.draw_text(f"Score: {self.score}", self.font, WHITE, (78, 25))
            self.draw_text(f"Level: {self.level}/5", self.font, WHITE, (WIDTH - 78, 25))
            goal = LEVEL_GOALS[self.level - 1]
            self.draw_text(
                f"Enemies: {self.enemies_defeated}/{goal}",
                self.small_font, (169, 190, 222), (WIDTH // 2, 26),
            )
            self.draw_player()
            for bullet in self.bullets:
                pygame.draw.rect(self.screen, (255, 242, 122),
                                 (int(bullet["x"] - 3), int(bullet["y"] - 8), 6, 16))
            for enemy in self.enemies:
                x, y, size = int(enemy["x"]), int(enemy["y"]), enemy["size"]
                pygame.draw.circle(self.screen, (255, 85, 119), (x, y), size)
                pygame.draw.circle(self.screen, (255, 192, 204), (x, y), size, 2)
                pygame.draw.circle(self.screen, (80, 18, 53), (x, y), max(3, size // 4))
        else:
            if self.state == "level_complete":
                title = f"LEVEL {self.level} COMPLETE"
                detail = f"Score: {self.score}"
                prompt = "Press ENTER to continue"
            elif self.state == "victory":
                title = "YOU SAVED THE GALAXY!"
                detail = f"Final score: {self.score}"
                prompt = "Press ENTER to play again"
            else:
                title = "GAME OVER"
                detail = f"Reached level {self.level}  |  Score: {self.score}"
                prompt = "Press ENTER to retry"
            self.draw_text(title, self.title_font, CYAN if self.state != "game_over" else (255, 113, 139),
                           (WIDTH // 2, 285))
            self.draw_text(detail, self.font, WHITE, (WIDTH // 2, 355))
            self.draw_text(prompt, self.small_font, (169, 190, 222), (WIDTH // 2, 405))
            self.draw_text("Press M for menu  |  ESC to quit",
                           self.small_font, (169, 190, 222), (WIDTH // 2, 455))

        pygame.display.flip()

    def run(self):
        while self.running:
            delta_time = min(self.clock.tick(FPS) / 1000, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(delta_time)
            self.draw_game()
        pygame.quit()


if __name__ == "__main__":
    ShooterGame().run()
