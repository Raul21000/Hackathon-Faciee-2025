import pygame
import cv2
import mediapipe as mp
import math
import sys
import random
import leaderboard  # NOU: Importul modulului extern

# --- CONFIGURARE GENERALĂ ---
pygame.init()
WIDTH, HEIGHT = 800, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Robo-Factory: 30s TIME ATTACK")

# --- CONFIGURARE CAMERĂ ---
cap = cv2.VideoCapture(0)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# --- SETĂRI JOC ---
FPS = 30
BELT_SPEED = 10  # Viteză constantă mare
SPAWN_RATE = 40  # Rata de apariție piese
SCALE_FACTOR = 0.20
PINCH_THRESHOLD = 60

# ### AICI SCHIMBI DURATA TOTALĂ A JOCULUI ###
GAME_DURATION = 30.0  # Secunde

# NOU: Calea fișierului de clasament
LEADERBOARD_GAME_FILE = "automatica.csv"

# Culori
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BAR_BG = (50, 50, 50)  # Gri închis pentru fundal bară
GOLD = (255, 215, 0)  # Culoare pentru scor mare

# Fonturi
try:
    font_score = pygame.font.SysFont("impact", 40)
    font_msg = pygame.font.SysFont("arial", 40, bold=True)
    font_timer = pygame.font.SysFont("consolas", 28, bold=True)
    font_popup = pygame.font.SysFont("arial", 50, bold=True)  # Pt "+100"
    font_leaderboard = pygame.font.SysFont('consolas', 25, bold=True)  # NOU: Font Leaderboard
    font_input = pygame.font.SysFont('consolas', 40, bold=True)  # NOU: Font Input
except:
    font_score = pygame.font.Font(None, 50)
    font_msg = pygame.font.Font(None, 50)
    font_timer = pygame.font.Font(None, 30)
    font_popup = pygame.font.Font(None, 60)
    font_leaderboard = pygame.font.Font(None, 30)
    font_input = pygame.font.Font(None, 50)


# --- CLASE ---
class RobotSlot:
    def __init__(self, name, img_path, x, y):
        self.name = name
        self.filled = False
        self.is_falling = False
        self.vx = 0
        self.vy = 0
        self.gravity = 0.9
        self.falling_rect = None

        try:
            # Atenție: Aceste fișiere de imagine (ex: picioare_robot.png) trebuie să existe!
            raw = pygame.image.load(img_path).convert_alpha()
            w = int(raw.get_width() * SCALE_FACTOR)
            h = int(raw.get_height() * SCALE_FACTOR)
            self.image = pygame.transform.smoothscale(raw, (w, h))
            self.ghost_image = self.image.copy()
            self.ghost_image.fill((255, 255, 255, 100), None, pygame.BLEND_RGBA_MULT)
        except:
            self.image = pygame.Surface((50, 50))
            self.image.fill(GREEN)
            self.ghost_image = self.image.copy()
            self.ghost_image.set_alpha(100)

        self.rect = self.image.get_rect(center=(x, y))
        self.original_pos = (x, y)

    def reset(self):
        self.filled = False
        self.is_falling = False
        self.rect.center = self.original_pos
        self.vx = 0
        self.vy = 0

    def trigger_fall(self):
        if self.filled:
            self.is_falling = True
            self.falling_rect = self.rect.copy()
            self.vy = random.uniform(-12, -6)
            self.vx = random.uniform(-6, 6)

    def update_fall(self):
        if self.is_falling and self.falling_rect:
            self.vy += self.gravity
            self.falling_rect.x += self.vx
            self.falling_rect.y += self.vy

    def draw(self, surface):
        if self.is_falling and self.falling_rect:
            surface.blit(self.image, self.falling_rect)
        elif self.filled:
            surface.blit(self.image, self.rect)
        else:
            surface.blit(self.ghost_image, self.rect)
            pygame.draw.rect(surface, (200, 200, 200), self.rect, 1)


class MovingPart:
    def __init__(self, name, img_surface, offset_x=0):
        self.name = name
        self.image = img_surface
        self.rect = self.image.get_rect(center=(WIDTH + 60 + offset_x, HEIGHT - 70))
        self.is_dragging = False

    def update(self, speed):
        if not self.is_dragging:
            self.rect.x -= speed

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        if self.is_dragging:
            pygame.draw.rect(surface, YELLOW, self.rect, 3)


# --- ZONA DE REGLAJ MANUAL ---
ROBOT_X = WIDTH // 2
ROBOT_Y_START = 120

slots_config = [
    ("Picioare", "picioare_robot.png", ROBOT_X, ROBOT_Y_START + 180),
    ("Trunchi", "trunchi_robot.png", ROBOT_X, ROBOT_Y_START + 90),
    ("Cap", "cap_robot.png", ROBOT_X, ROBOT_Y_START),
    # Mâna Stângă (Jos)
    ("Mana_Stg", "mana_stanga.png", ROBOT_X - 75, ROBOT_Y_START + 130),
    # Mâna Dreaptă (Sus)
    ("Mana_Dr", "mana_dreapta.png", ROBOT_X + 75, ROBOT_Y_START + 50),
]

robot_slots = []
parts_library = {}

for name, path, x, y in slots_config:
    slot = RobotSlot(name, path, x, y)
    robot_slots.append(slot)
    parts_library[name] = slot.image


# --- LOGICA DE SPAWN ---
def get_spawn_part():
    # 70% șansă să dea ce trebuie pentru viteză
    missing = [s.name for s in robot_slots if not s.filled]
    if not missing: return random.choice(list(parts_library.keys()))

    if random.random() < 0.7:
        return random.choice(missing)
    else:
        return random.choice(list(parts_library.keys()))


# --- MAIN LOOP ---
def main():
    clock = pygame.time.Clock()

    # Resetăm sloturile la start
    for slot in robot_slots: slot.reset()

    conveyor_parts = []
    spawn_timer = 0
    score = 0

    # Stări joc
    game_state = "PLAYING"  # Poate fi PLAYING, EXPLODING, INPUT_NAME, SHOW_LEADERBOARD
    shake_timer = 0

    # Cronometru GLOBAL
    time_left = GAME_DURATION
    game_started = False

    # Leaderboard State Variables
    input_name = ""
    current_leaderboard_data = []

    # Control pentru trecerea la state-ul de Leaderboard
    score_checked_on_end = False

    dragged_part = None

    # Efect vizual "+100"
    popup_timer = 0
    popup_text = None

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            # --- EVENIMENTE LEADERBOARD ---
            if game_state == "INPUT_NAME":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        input_name = input_name[:-1]
                    elif event.key == pygame.K_RETURN:
                        if len(input_name) == 3:
                            # PASUL 3: Salvarea scorului
                            leaderboard.update_leaderboard(input_name, score, LEADERBOARD_GAME_FILE)

                            # PASUL 4: Citirea clasamentului actualizat
                            current_leaderboard_data = leaderboard.import_highscores(LEADERBOARD_GAME_FILE)

                            game_state = "SHOW_LEADERBOARD"

                    elif len(input_name) < 3:
                        if event.unicode.isalnum():
                            input_name += event.unicode.upper()

            elif game_state == "SHOW_LEADERBOARD":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    main()  # RESTART
                    return

            # --- RESTART (cu mouse/pinch) ---
            elif game_state == "GAME_OVER_NO_SCORE":  # Stare de final daca nu ai High Score
                if event.type == pygame.MOUSEBUTTONDOWN:
                    main()
                    return

        success, frame = cap.read()
        if not success: continue
        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = hands.process(frame_rgb)

        hand_pos = (-100, -100)
        is_pinching = False

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                idx = hand_lms.landmark[8]
                thb = hand_lms.landmark[4]
                cx, cy = int(idx.x * WIDTH), int(idx.y * HEIGHT)
                tx, ty = int(thb.x * WIDTH), int(thb.y * HEIGHT)
                hand_pos = (cx, cy)
                if math.hypot(cx - tx, cy - ty) < PINCH_THRESHOLD:
                    is_pinching = True

        # --- LOGICA DE JOC ---
        if game_state == "PLAYING":

            # Start joc la prima interacțiune
            if is_pinching and not game_started:
                game_started = True

            # Scădere timp doar dacă a început
            if game_started:
                time_left -= dt
                if time_left <= 0:
                    time_left = 0
                    game_state = "EXPLODING"
                    shake_timer = 60
                    # Declanșăm explozia
                    for slot in robot_slots:
                        if slot.filled: slot.trigger_fall()

            # GRAB Logic
            if is_pinching and not dragged_part:
                for part in reversed(conveyor_parts):
                    if part.rect.inflate(40, 40).collidepoint(hand_pos):
                        dragged_part = part
                        part.is_dragging = True
                        break
            if is_pinching and dragged_part:
                dragged_part.rect.center = hand_pos

            # DROP Logic
            if not is_pinching and dragged_part:
                for slot in robot_slots:
                    if slot.name == dragged_part.name and not slot.filled:
                        if math.hypot(dragged_part.rect.centerx - slot.rect.centerx,
                                      dragged_part.rect.centery - slot.rect.centery) < 80:
                            slot.filled = True
                            if dragged_part in conveyor_parts: conveyor_parts.remove(dragged_part)
                            break
                dragged_part.is_dragging = False
                dragged_part = None

            # CHECK WIN (Robot Complet)
            if all(s.filled for s in robot_slots):
                score += 100  # +100 PUNCTE
                shake_timer = 10

                # Resetăm imediat sloturile pentru următorul robot
                for s in robot_slots: s.reset()

                # Activăm popup "+100"
                popup_text = font_popup.render("+100", True, GOLD)
                popup_timer = 20  # durată afișare

            # SPAWN (Burst)
            spawn_timer += 1
            if spawn_timer > SPAWN_RATE:
                spawn_timer = 0
                burst = random.randint(1, 3)
                for i in range(burst):
                    p_name = get_spawn_part()
                    new_part = MovingPart(p_name, parts_library[p_name], offset_x=i * 100)
                    conveyor_parts.append(new_part)

            # BELT UPDATE
            for part in conveyor_parts:
                part.update(BELT_SPEED)
                if part.rect.right < 0: conveyor_parts.remove(part)

        # --- EXPLOSION STATE (La finalul timpului) ---
        elif game_state == "EXPLODING":
            parts_still_falling = False
            for slot in robot_slots:
                if slot.is_falling:
                    slot.update_fall()
                    if slot.falling_rect.top < HEIGHT: parts_still_falling = True

            if not parts_still_falling and shake_timer <= 0:

                # NOU: LOGICĂ DE LEADERBOARD LA FINALUL JOCULUI
                if not score_checked_on_end:
                    # PASUL 2: Verifică dacă scorul este High Score
                    if leaderboard.check_score(score, LEADERBOARD_GAME_FILE):
                        game_state = "INPUT_NAME"
                    else:
                        # Dacă nu e High Score, treci direct la afișarea clasamentului
                        current_leaderboard_data = leaderboard.import_highscores(LEADERBOARD_GAME_FILE)
                        game_state = "SHOW_LEADERBOARD"

                    score_checked_on_end = True

        # --- DESENARE ---
        bg_surf = pygame.image.frombuffer(frame_rgb.tobytes(), (WIDTH, HEIGHT), "RGB")
        screen.blit(bg_surf, (0, 0))

        ox, oy = 0, 0
        if shake_timer > 0:
            intensity = 15 if game_state == "EXPLODING" else 5
            ox = random.randint(-intensity, intensity)
            oy = random.randint(-intensity, intensity)
            shake_timer -= 1

        # Banda Rulanta
        belt_surf = pygame.Surface((WIDTH, 140))
        belt_surf.set_alpha(180)
        belt_surf.fill((30, 30, 40))
        screen.blit(belt_surf, (0, HEIGHT - 140))

        # Robot & Piese
        for slot in robot_slots:
            if slot.is_falling:
                slot.draw(screen)
            else:
                prev = slot.rect.center
                slot.rect.center = (prev[0] + ox, prev[1] + oy)
                slot.draw(screen)
                slot.rect.center = prev

        if game_state != "EXPLODING":
            for part in conveyor_parts: part.draw(screen)

        # --- UI (User Interface) ---
        cx = WIDTH // 2

        # 1. SCOR
        score_surf = font_score.render(f"SCORE: {score}", True, WHITE)
        screen.blit(score_surf, (20, 20))

        # 2. POPUP +100
        if popup_timer > 0:
            popup_timer -= 1
            screen.blit(popup_text, (ROBOT_X + 100, ROBOT_Y_START))

        # 3. BARA DE TIMP (30s)
        if game_state == "PLAYING":
            # Fundal bară
            bar_w = 400
            bx = WIDTH // 2 - bar_w // 2
            by = 30
            pygame.draw.rect(screen, BAR_BG, (bx, by, bar_w, 25))

            # Bara colorată
            ratio = max(0, time_left / GAME_DURATION)
            col = GREEN
            if ratio < 0.5: col = YELLOW
            if ratio < 0.2: col = RED

            pygame.draw.rect(screen, col, (bx, by, int(bar_w * ratio), 25))

            # Text Timp (Ex: 12.5s)
            t_txt = font_timer.render(f"{time_left:.1f}s", True, WHITE)
            screen.blit(t_txt, (bx + bar_w + 10, by))

            if not game_started:
                start_msg = font_timer.render("GRAB A PART TO START!", True, GOLD)
                screen.blit(start_msg, (WIDTH // 2 - start_msg.get_width() // 2, HEIGHT // 2 + 100))

        # 4. CURSOR
        if hand_pos[0] > 0 and game_state == "PLAYING":
            col = GREEN if is_pinching else YELLOW
            pygame.draw.circle(screen, col, hand_pos, 15, 3)

        # 5. ECRANE FINALE (LEADERBOARD)
        if game_state in ["INPUT_NAME", "SHOW_LEADERBOARD"]:
            s = pygame.Surface((WIDTH, HEIGHT))
            s.set_alpha(220)
            s.fill((0, 0, 0))
            screen.blit(s, (0, 0))

            # --- INPUT NAME (PASUL 3) ---
            if game_state == "INPUT_NAME":
                end_title = font_msg.render("NEW HIGH SCORE!", True, GOLD)
                screen.blit(end_title, (cx - end_title.get_width() // 2, HEIGHT // 2 - 100))

                final_score_txt = font_popup.render(f"SCORE: {score}", True, WHITE)
                screen.blit(final_score_txt, (cx - final_score_txt.get_width() // 2, HEIGHT // 2 - 30))

                txt_prompt = font_timer.render("ENTER INITIALS (3):", True, WHITE)
                screen.blit(txt_prompt, (cx - txt_prompt.get_width() // 2, HEIGHT // 2 + 40))

                input_rect = pygame.Rect(cx - 100, HEIGHT // 2 + 80, 200, 50)
                pygame.draw.rect(screen, BAR_BG, input_rect)
                pygame.draw.rect(screen, GOLD, input_rect, 3)

                txt_input = font_input.render(input_name, True, YELLOW)
                screen.blit(txt_input, (cx - txt_input.get_width() // 2, input_rect.y + 5))

                if len(input_name) == 3:
                    txt_enter = font_timer.render("PRESS [ENTER] TO SAVE", True, GREEN)
                    if (pygame.time.get_ticks() // 500) % 2 == 0:
                        screen.blit(txt_enter, (cx - txt_enter.get_width() // 2, HEIGHT // 2 + 150))

            # --- SHOW LEADERBOARD (PASUL 5) ---
            elif game_state == "SHOW_LEADERBOARD":
                end_title = font_msg.render("TOP ROBOT BUILDERS", True, GOLD)
                screen.blit(end_title, (cx - end_title.get_width() // 2, 50))

                start_y = 120

                # Afișarea clasamentului (Limitat vizual la 5)
                for i, (name, s) in enumerate(current_leaderboard_data):
                    if i >= 5: break

                    color = GOLD if i == 0 else WHITE
                    txt_name = font_leaderboard.render(f"{i + 1}. {name}", True, color)
                    txt_s = font_leaderboard.render(str(s), True, color)
                    screen.blit(txt_name, (cx - 150, start_y + i * 35))
                    screen.blit(txt_s, (cx + 80, start_y + i * 35))

                rst = font_timer.render("CLICK SCREEN TO RESTART", True, WHITE)
                screen.blit(rst, (cx - rst.get_width() // 2, HEIGHT - 50))

        pygame.display.flip()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        pygame.quit()
        sys.exit()