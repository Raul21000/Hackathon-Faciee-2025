import cv2
import mediapipe as mp
import numpy as np
import pygame
import random
import math
import os
import csv
import leaderboard

# --- CONFIGURARE ---
WINDOW_SIZE = (800, 480)
# NOU: Folosim calea către fișierul CSV al clasamentului
LEADERBOARD_GAME_FILE = "calculatoare_joc.csv"
SMOOTHING_FACTOR = 0.3  # 0.1 = Foarte lent/smooth, 0.9 = Foarte rapid/tremurat (0.3 e ideal)

# Culori Neon
COLOR_SKELETON = (0, 255, 255)
COLOR_HEAD_ZONE = (255, 255, 0)
COLOR_PATCH = (0, 150, 255)
COLOR_ERROR = (255, 50, 50)
COLOR_BOSS = (148, 0, 211)
COLOR_TEXT = (255, 255, 255)
COLOR_HIGHSCORE = (255, 215, 0)
COLOR_INPUT_BG = (50, 50, 50)

# --- INITIALIZARE MEDIAPIPE ---
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5, model_complexity=0)


# --- FUNCTIE DE SMOOTHING (LERP) ---
def lerp(start, end, alpha):
    """Calculeaza o pozitie intermediara pentru miscare fluida."""
    return start + (end - start) * alpha


def lerp_point(p1, p2, alpha):
    """Aplica Lerp pe un tuplu (x, y)."""
    x = lerp(p1[0], p2[0], alpha)
    y = lerp(p1[1], p2[1], alpha)
    return (int(x), int(y))


# --- FUNCTII VECHI DE LEADERBOARD AU FOST ELIMINATE ---
# S-a trecut la utilizarea modulului extern 'leaderboard'


# --- CLASE JOC ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-5, 5)
        self.life = random.randint(15, 30)
        self.size = random.randint(2, 6)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(0, self.size - 0.1)

    def draw(self, surface, offset_x=0, offset_y=0):
        if self.life > 0:
            pygame.draw.circle(surface, self.color, (int(self.x + offset_x), int(self.y + offset_y)), int(self.size))


class FallingItem:
    def __init__(self, difficulty_multiplier=1.0):
        self.x = random.randint(60, WINDOW_SIZE[0] - 60)
        self.y = -50
        self.speed = random.uniform(4, 7) * difficulty_multiplier
        self.size = 30
        self.angle = 0
        self.hit_by_left = False
        self.hit_by_right = False

        rand_val = random.random()
        if rand_val < 0.4:
            self.type = "EROARE"
        elif rand_val < 0.9:
            self.type = "PATCH"
        else:
            self.type = "BOSS"
            self.hp = 5
            self.max_hp = 5
            self.size = 50
            self.speed *= 0.5

    def move(self):
        self.y += self.speed
        self.angle += 5

    def draw(self, surface, font_boss, font_small, offset_x=0, offset_y=0):
        draw_x = int(self.x + offset_x)
        draw_y = int(self.y + offset_y)

        if self.type == "EROARE":
            pulse = math.sin(pygame.time.get_ticks() * 0.01) * 4
            r = int(self.size + pulse)
            pygame.draw.circle(surface, COLOR_ERROR, (draw_x, draw_y), r)
            pygame.draw.circle(surface, (150, 0, 0), (draw_x, draw_y), int(self.size - 8))
            pygame.draw.line(surface, (255, 255, 255), (draw_x - 8, draw_y - 8), (draw_x + 8, draw_y + 8), 3)
            pygame.draw.line(surface, (255, 255, 255), (draw_x + 8, draw_y - 8), (draw_x - 8, draw_y + 8), 3)

        elif self.type == "PATCH":
            pulse = math.sin(pygame.time.get_ticks() * 0.01) * 3
            w = self.size * 2 + pulse
            rect = pygame.Rect(draw_x - self.size, draw_y - self.size, w, w)
            pygame.draw.rect(surface, COLOR_PATCH, rect, border_radius=6)
            pygame.draw.rect(surface, (200, 255, 255), rect, 2, border_radius=6)
            txt = font_small.render("PATCH", True, (255, 255, 255))
            surface.blit(txt, (draw_x - txt.get_width() // 2, draw_y - txt.get_height() // 2))

        elif self.type == "BOSS":
            pulse = math.sin(pygame.time.get_ticks() * 0.05) * 5
            r = int(self.size + pulse)
            pygame.draw.circle(surface, COLOR_BOSS, (draw_x, draw_y), r)
            pygame.draw.circle(surface, (255, 255, 255), (draw_x, draw_y), r, 3)
            text_surf = font_boss.render("RESTANTA", True, (255, 255, 255))
            surface.blit(text_surf, (draw_x - text_surf.get_width() // 2, draw_y - 10))

            bar_width = 60
            bar_height = 8
            fill_width = int((self.hp / self.max_hp) * bar_width)
            bar_x = draw_x - bar_width // 2
            bar_y = draw_y - self.size - 15
            pygame.draw.rect(surface, (0, 0, 0), (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, fill_width, bar_height))


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.NOFRAME)
    pygame.display.set_caption("IT Defender - Smooth Edition")
    clock = pygame.time.Clock()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # --- FONTS ---
    font_ui = pygame.font.SysFont('Consolas', 20, bold=True)
    font_small = pygame.font.SysFont('Arial', 12, bold=True)
    font_boss = pygame.font.SysFont('Consolas', 18, bold=True)
    font_combo = pygame.font.SysFont('Impact', 30)
    font_big = pygame.font.SysFont('Consolas', 40, bold=True)
    font_leaderboard = pygame.font.SysFont('Consolas', 25, bold=True)

    items = []
    particles = []
    spawn_timer = 0
    score = 0
    health = 100

    game_over = False

    input_name = ""
    saved_to_leaderboard = False
    current_leaderboard_data = []
    awaiting_name = False  # Stare pentru a aștepta numele (dacă scorul e Highscore)

    combo = 0
    max_combo = 0
    difficulty = 1.0
    screen_shake = 0

    # --- VARIABILE PENTRU SMOOTHING ---
    cx, cy = WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2
    curr_nose = (cx, cy)
    curr_l_hand = (cx - 50, cy + 50)
    curr_r_hand = (cx + 50, cy + 50)
    curr_l_sh = (cx - 30, cy)
    curr_r_sh = (cx + 30, cy)
    curr_l_elb = (cx - 40, cy + 30)
    curr_r_elb = (cx + 40, cy + 30)

    running = True
    while running:
        # --- EVENIMENTE ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if game_over:
                # LOGICA NOUA: AȘTEAPTĂ NUMELE PENTRU UN NOU HIGH SCORE (Pasul 2, 3)
                if awaiting_name and not saved_to_leaderboard:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_BACKSPACE:
                            input_name = input_name[:-1]
                        elif event.key == pygame.K_RETURN:
                            if len(input_name) == 3:
                                # PASUL 3: Chemati update_leaderboard (salvarea scorului în CSV)
                                leaderboard.update_leaderboard(input_name, score, LEADERBOARD_GAME_FILE)

                                # PASUL 4: Chemati import_highscores (citirea datelor noi)
                                current_leaderboard_data = leaderboard.import_highscores(LEADERBOARD_GAME_FILE)

                                saved_to_leaderboard = True
                                awaiting_name = False
                        elif len(input_name) < 3:
                            if event.unicode.isalnum():
                                input_name += event.unicode.upper()

                # LOGICA AFISARE CLASAMENT SAU DACA NU E HIGH SCORE (ready for reboot)
                else:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            # RESETARE JOC
                            items = []
                            particles = []
                            score = 0
                            health = 100
                            combo = 0
                            max_combo = 0
                            difficulty = 1.0
                            input_name = ""
                            saved_to_leaderboard = False
                            awaiting_name = False
                            game_over = False
                        if event.key == pygame.K_ESCAPE:
                            running = False
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, WINDOW_SIZE)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        # Shake Logic
        shake_x = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0
        shake_y = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0
        if screen_shake > 0: screen_shake -= 1

        # Fundal
        frame_dimmed = cv2.addWeighted(frame, 0.3, np.zeros(frame.shape, frame.dtype), 0, 0)
        frame_rgb_dim = cv2.cvtColor(frame_dimmed, cv2.COLOR_BGR2RGB)
        surf_cam = pygame.surfarray.make_surface(frame_rgb_dim.swapaxes(0, 1))
        screen.blit(surf_cam, (shake_x, shake_y))

        user_detected = False

        if results.pose_landmarks:
            user_detected = True
            landmarks = results.pose_landmarks.landmark

            def to_px(lm):
                return (int(lm.x * WINDOW_SIZE[0]), int(lm.y * WINDOW_SIZE[1]))

            # 1. Obtinem tintele BRUTE (Raw Targets)
            target_nose = to_px(landmarks[mp_pose.PoseLandmark.NOSE])
            target_l_hand = to_px(landmarks[mp_pose.PoseLandmark.LEFT_WRIST])
            target_r_hand = to_px(landmarks[mp_pose.PoseLandmark.RIGHT_WRIST])
            target_l_sh = to_px(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER])
            target_r_sh = to_px(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER])
            target_l_elb = to_px(landmarks[mp_pose.PoseLandmark.LEFT_ELBOW])
            target_r_elb = to_px(landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW])

            # 2. Aplicam LERP (Smoothing)
            curr_nose = lerp_point(curr_nose, target_nose, SMOOTHING_FACTOR)
            curr_l_hand = lerp_point(curr_l_hand, target_l_hand, SMOOTHING_FACTOR)
            curr_r_hand = lerp_point(curr_r_hand, target_r_hand, SMOOTHING_FACTOR)
            curr_l_sh = lerp_point(curr_l_sh, target_l_sh, SMOOTHING_FACTOR)
            curr_r_sh = lerp_point(curr_r_sh, target_r_sh, SMOOTHING_FACTOR)
            curr_l_elb = lerp_point(curr_l_elb, target_l_elb, SMOOTHING_FACTOR)
            curr_r_elb = lerp_point(curr_r_elb, target_r_elb, SMOOTHING_FACTOR)

            # Helpers desenare
            def d_line(p1, p2, col, w):
                pygame.draw.line(screen, col, (p1[0] + shake_x, p1[1] + shake_y), (p2[0] + shake_x, p2[1] + shake_y), w)

            def d_circ(pos, col, r, w=0):
                pygame.draw.circle(screen, col, (pos[0] + shake_x, pos[1] + shake_y), r, w)

            # Desenam Scheletul folosind valorile SMOOTH (curr_)
            d_line(curr_l_sh, curr_r_sh, COLOR_SKELETON, 3)
            d_line(curr_l_sh, curr_l_elb, COLOR_SKELETON, 2)
            d_line(curr_l_elb, curr_l_hand, COLOR_SKELETON, 2)
            d_line(curr_r_sh, curr_r_elb, COLOR_SKELETON, 2)
            d_line(curr_r_elb, curr_r_hand, COLOR_SKELETON, 2)

            d_circ(curr_nose, COLOR_HEAD_ZONE, 12)
            d_circ(curr_nose, (255, 50, 50), 25, 2)

            glow = 20 + int(math.sin(pygame.time.get_ticks() * 0.02) * 5)
            d_circ(curr_l_hand, COLOR_PATCH, glow)
            d_circ(curr_r_hand, COLOR_PATCH, glow)

        else:
            msg = font_ui.render("SCANARE... INTRA IN CADRU", True, (0, 255, 0))
            screen.blit(msg, (WINDOW_SIZE[0] // 2 - msg.get_width() // 2, WINDOW_SIZE[1] // 2))

        if not game_over and user_detected:
            difficulty = 1.0 + (score / 500.0)
            spawn_timer += 1
            if spawn_timer > max(20, 45 - int(score / 100)):
                items.append(FallingItem(difficulty))
                spawn_timer = 0

            for item in items[:]:
                item.move()
                item.draw(screen, font_boss, font_small, shake_x, shake_y)

                if item.y > WINDOW_SIZE[1]:
                    if item.type == "PATCH":
                        combo = 0
                        screen_shake = 5
                    if item.type == "BOSS":
                        health -= 30
                        screen_shake = 20
                        combo = 0
                    items.remove(item)
                    continue

                # Folosim coordonatele SMOOTH pentru detectia coliziunilor!
                dist_nose = math.hypot(item.x - curr_nose[0], item.y - curr_nose[1])
                dist_lh = math.hypot(item.x - curr_l_hand[0], item.y - curr_l_hand[1])
                dist_rh = math.hypot(item.x - curr_r_hand[0], item.y - curr_r_hand[1])
                hit_radius = item.size + 25

                if item.type == "BOSS":
                    if dist_lh < hit_radius:
                        if not item.hit_by_left:
                            item.hp -= 1
                            item.hit_by_left = True
                            screen_shake = 8
                            for _ in range(5): particles.append(Particle(item.x, item.y, (255, 255, 255)))
                    else:
                        item.hit_by_left = False

                    if dist_rh < hit_radius:
                        if not item.hit_by_right:
                            item.hp -= 1
                            item.hit_by_right = True
                            screen_shake = 8
                            for _ in range(5): particles.append(Particle(item.x, item.y, (255, 255, 255)))
                    else:
                        item.hit_by_right = False

                    if item.hp <= 0:
                        score += 100
                        items.remove(item)
                        screen_shake = 20
                        for _ in range(20): particles.append(Particle(item.x, item.y, COLOR_BOSS))
                        continue

                    if dist_nose < hit_radius:
                        health -= 30
                        items.remove(item)
                        screen_shake = 20
                        combo = 0
                        for _ in range(15): particles.append(Particle(item.x, item.y, (255, 0, 0)))

                elif item.type == "EROARE":
                    if dist_nose < hit_radius:
                        health -= 15
                        items.remove(item)
                        screen_shake = 15
                        combo = 0
                        for _ in range(10): particles.append(Particle(item.x, item.y, (255, 50, 0)))

                elif item.type == "PATCH":
                    if dist_lh < hit_radius or dist_rh < hit_radius:
                        points = 10 + combo
                        score += points
                        combo += 1
                        if combo > max_combo: max_combo = combo
                        items.remove(item)
                        for _ in range(8): particles.append(Particle(item.x, item.y, (100, 255, 255)))

            if health <= 0:
                game_over = True

                # PASUL 2: Chemati check_score (cu calea fișierului CSV)
                if leaderboard.check_score(score, LEADERBOARD_GAME_FILE):
                    awaiting_name = True  # Activează starea de introducere nume
                else:
                    # Dacă nu este High Score, afișăm direct clasamentul existent
                    # PASUL 4 (pentru afișare): Chemati import_highscores
                    current_leaderboard_data = leaderboard.import_highscores(LEADERBOARD_GAME_FILE)
                    saved_to_leaderboard = True  # Afișăm direct clasamentul

        for p in particles[:]:
            p.update()
            p.draw(screen, shake_x, shake_y)
            if p.life <= 0: particles.remove(p)

        # UI
        pygame.draw.rect(screen, (0, 0, 0), (10, 10, 180, 40), border_radius=10)
        pygame.draw.rect(screen, COLOR_PATCH, (10, 10, 180, 40), 2, border_radius=10)
        screen.blit(font_ui.render(f"SCOR: {score}", True, COLOR_PATCH), (20, 18))

        if combo > 1:
            combo_col = (255, 255, 0) if combo < 10 else (255, 0, 255)
            combo_surf = font_combo.render(f"{combo}x COMBO!", True, combo_col)
            screen.blit(combo_surf, (20, 60))

        bar_max_w = 200
        x_bar = WINDOW_SIZE[0] - bar_max_w - 20
        pygame.draw.rect(screen, (0, 0, 0), (x_bar - 10, 10, bar_max_w + 20, 40), border_radius=10)
        pygame.draw.rect(screen, (50, 0, 0), (x_bar, 18, bar_max_w, 24))

        if health > 0:
            width_hp = int(bar_max_w * (health / 100))
            hp_color = (0, 255, 0)
            if health < 50: hp_color = (255, 255, 0)
            if health < 25: hp_color = (255, 0, 0)
            pygame.draw.rect(screen, hp_color, (x_bar, 18, width_hp, 24))

        screen.blit(font_ui.render(f"HP: {health}%", True, (255, 255, 255)), (x_bar, 45))

        if game_over:
            overlay = pygame.Surface(WINDOW_SIZE)
            overlay.set_alpha(240)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))

            cx, cy = WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2
            txt_over = font_big.render("SISTEM CAZUT", True, (255, 50, 50))
            screen.blit(txt_over, (cx - txt_over.get_width() // 2, 40))

            # Afisare camp de introducere nume (Pasul 2, 3)
            if awaiting_name and not saved_to_leaderboard:
                txt_score = font_ui.render(f"SCOR FINAL: {score}", True, COLOR_PATCH)
                screen.blit(txt_score, (cx - txt_score.get_width() // 2, 100))
                txt_prompt = font_ui.render("HIGH SCORE! INTRODUCE INITIALE (3):", True, (255, 255, 255))
                screen.blit(txt_prompt, (cx - txt_prompt.get_width() // 2, 180))

                input_rect = pygame.Rect(cx - 100, 220, 200, 60)
                pygame.draw.rect(screen, COLOR_INPUT_BG, input_rect)
                pygame.draw.rect(screen, COLOR_PATCH, input_rect, 3)
                txt_input = font_big.render(input_name, True, (255, 255, 0))
                screen.blit(txt_input, (cx - txt_input.get_width() // 2, 230))

                if len(input_name) == 3:
                    txt_enter = font_ui.render("APASA [ENTER] PENTRU A SALVA", True, (0, 255, 0))
                    if (pygame.time.get_ticks() // 500) % 2 == 0:
                        screen.blit(txt_enter, (cx - txt_enter.get_width() // 2, 300))
                else:
                    txt_info = font_small.render("Tastatura necesara", True, (150, 150, 150))
                    screen.blit(txt_info, (cx - txt_info.get_width() // 2, 300))

            # Afisare Leaderboard (Pasul 5)
            elif saved_to_leaderboard:
                txt_lb_title = font_leaderboard.render("TOP 5 HACKERS", True, COLOR_HIGHSCORE)
                screen.blit(txt_lb_title, (cx - txt_lb_title.get_width() // 2, 100))
                start_y = 160

                # Afișarea datelor din lista returnată de import_highscores()
                for i, (name, s) in enumerate(current_leaderboard_data):
                    # Afișăm primele 5 rezultate, chiar dacă modulul returnează 10
                    if i >= 5: break

                    color = COLOR_HIGHSCORE if i == 0 else (255, 255, 255)
                    txt_name = font_ui.render(f"{i + 1}. {name}", True, color)
                    txt_sc = font_ui.render(str(s), True, color)
                    screen.blit(txt_name, (cx - 150, start_y + i * 35))
                    screen.blit(txt_sc, (cx + 80, start_y + i * 35))

                txt_restart = font_ui.render("Apasa SPACE pentru Reboot", True, COLOR_PATCH)
                if (pygame.time.get_ticks() // 700) % 2 == 0:
                    screen.blit(txt_restart, (cx - txt_restart.get_width() // 2, 380))

        pygame.display.flip()
        clock.tick(30)

    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()