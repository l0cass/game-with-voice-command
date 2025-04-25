import pygame
import sys
import random
import time
import threading
import json
import queue
from vosk import Model, KaldiRecognizer
import pyaudio

pygame.init()

WIDTH, HEIGHT = 800, 400
GROUND_HEIGHT = 350
PLAYER_SIZE = 40
PLAYER_SPEED = 5
GRAVITY = 1
JUMP_HEIGHT = 150
OBSTACLE_WIDTH = 30
OBSTACLE_HEIGHT = 60
MIN_OBSTACLE_DISTANCE = 300
MAX_OBSTACLE_DISTANCE = 600

GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Runner com Comandos de Voz")

class Player:
    def __init__(self):
        self.x = 100
        self.y = GROUND_HEIGHT - PLAYER_SIZE
        self.width = PLAYER_SIZE
        self.height = PLAYER_SIZE
        self.jumping = False
        self.jump_vel = 0
        self.moving = True

    def jump(self):
        if not self.jumping:
            self.jumping = True
            self.jump_vel = -20

    def update(self):
        if self.moving:
            self.x += PLAYER_SPEED
        if self.jumping:
            self.y += self.jump_vel
            self.jump_vel += GRAVITY
            if self.y >= GROUND_HEIGHT - PLAYER_SIZE:
                self.y = GROUND_HEIGHT - PLAYER_SIZE
                self.jumping = False
                self.jump_vel = 0

    def draw(self, camera_offset):
        screen_x = self.x - camera_offset
        pygame.draw.rect(screen, BLUE, (screen_x, self.y, self.width, self.height))

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

class Obstacle:
    def __init__(self, x):
        self.x = x
        self.y = GROUND_HEIGHT - OBSTACLE_HEIGHT
        self.width = OBSTACLE_WIDTH
        self.height = OBSTACLE_HEIGHT

    def draw(self, camera_offset):
        screen_x = self.x - camera_offset
        pygame.draw.rect(screen, GRAY, (screen_x, self.y, self.width, self.height))

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

def voice_recognition(command_queue):
    model_path = "vosk-model-small-pt-0.3"
    try:
        model = Model(model_path)
    except Exception as e:
        print(f"Erro ao carregar o modelo: {e}")
        return

    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1600)
    stream.start_stream()

    rec = KaldiRecognizer(model, 16000)

    print("Reconhecimento de voz em tempo real iniciado")
    print("Comandos: 'pular', 'parar', 'andar'")

    while True:
        try:
            data = stream.read(800, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                _ = json.loads(rec.Result())

            partial = json.loads(rec.PartialResult())
            if 'partial' in partial and partial['partial']:
                command = partial['partial'].lower()
                if "pular" in command or "pula" in command:
                    command_queue.put("jump")
                elif "parar" in command or "para" in command:
                    command_queue.put("stop")
                elif "andar" in command or "anda" in command or "continuar" in command or "continua" in command:
                    command_queue.put("move")
        except Exception as e:
            print(f"Erro no reconhecimento de voz: {e}")
            break

    stream.stop_stream()
    stream.close()
    audio.terminate()

def main():
    player = Player()
    command_queue = queue.Queue()
    voice_thread = threading.Thread(target=voice_recognition, args=(command_queue,), daemon=True)
    voice_thread.start()

    obstacles = [Obstacle(WIDTH + random.randint(100, 300))]

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    game_over = False
    start_time = time.time()
    score = 0
    camera_offset = 0

    while not game_over:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()
                elif event.key == pygame.K_s:
                    player.moving = False
                elif event.key == pygame.K_w:
                    player.moving = True

        while not command_queue.empty():
            cmd = command_queue.get()
            if cmd == "jump":
                player.jump()
            elif cmd == "stop":
                player.moving = False
            elif cmd == "move":
                player.moving = True

        player.update()
        camera_offset = player.x - 100
        if player.moving:
            score += PLAYER_SPEED / 10

        for obstacle in obstacles[:]:
            if obstacle.x < camera_offset - 100:
                obstacles.remove(obstacle)

        if len(obstacles) < 5:
            last_obstacle = obstacles[-1]
            new_x = last_obstacle.x + random.randint(MIN_OBSTACLE_DISTANCE, MAX_OBSTACLE_DISTANCE)
            obstacles.append(Obstacle(new_x))

        for obstacle in obstacles:
            if player.get_rect().colliderect(obstacle.get_rect()):
                game_over = True

        screen.fill(BLACK)
        pygame.draw.rect(screen, DARK_GRAY, (0, GROUND_HEIGHT, WIDTH, HEIGHT - GROUND_HEIGHT))
        player.draw(camera_offset)

        for obstacle in obstacles:
            screen_x = obstacle.x - camera_offset
            if -OBSTACLE_WIDTH <= screen_x <= WIDTH:
                obstacle.draw(camera_offset)

        current_time = time.time() - start_time
        timer_text = font.render(f"Tempo: {int(current_time)}s", True, WHITE)
        score_text = font.render(f"Pontuação: {int(score)}", True, WHITE)
        screen.blit(timer_text, (10, 10))
        screen.blit(score_text, (10, 50))

        pygame.display.update()
        clock.tick(60)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    main()
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

        screen.fill(BLACK)
        game_over_text = font.render("Game Over!", True, WHITE)
        final_score_text = font.render(f"Pontuação final: {int(score)}", True, WHITE)
        restart_text = font.render("Pressione R para reiniciar ou Q para sair", True, WHITE)

        screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 2 - 50))
        screen.blit(final_score_text, (WIDTH // 2 - final_score_text.get_width() // 2, HEIGHT // 2))
        screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 50))

        pygame.display.update()
        clock.tick(60)

if __name__ == "__main__":
    main()
