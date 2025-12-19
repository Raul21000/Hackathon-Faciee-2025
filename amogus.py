import cv2
import mediapipe as mp
import pygame
import math
import random
import time  # <--- AM IMPORTAT TIME

# --- CONFIGURĂRI ---
WIDTH, HEIGHT = 800, 600
CAP_WIDTH, CAP_HEIGHT = 640, 480
PINCH_THRESHOLD = 40

COLORS = {
    'red': (255, 0, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
    'pink': (255, 0, 255)
}
COLOR_KEYS = list(COLORS.keys())


# --- FUNCȚIE GRAFICĂ SIMBOLURI ---
def draw_symbol(surface, color_name, rect):
    center = rect.center
    x, y = center
    if color_name == 'yellow':
        pygame.draw.circle(surface, (0, 0, 0), center, 12, 3)
    elif color_name == 'blue':
        off = 10
        pygame.draw.line(surface, (0, 0, 0), (x - off, y - off), (x + off, y + off), 4)
        pygame.draw.line(surface, (0, 0, 0), (x + off, y - off), (x - off, y + off), 4)
    elif color_name == 'red':
        pts = [(x, y - 12), (x - 12, y + 10), (x + 12, y + 10)]
        pygame.draw.polygon(surface, (0, 0, 0), pts, 3)
    elif color_name == 'pink':
        rect_s = pygame.Rect(0, 0, 16, 16)
        rect_s.center = center
        pygame.draw.rect(surface, (0, 0, 0), rect_s, 2)


# --- CLASA CABLU ---
class Wire:
    def __init__(self, color_name, y_pos, is_left):
        self.color_name = color_name
        self.color = COLORS[color_name]
        self.y = y_pos
        self.is_left = is_left

        if is_left:
            self.rect = pygame.Rect(50, y_pos - 20, 40, 40)
            self.start_pos = (90, y_pos)
            self.end_pos = (90, y_pos)
        else:
            self.rect = pygame.Rect(WIDTH - 90, y_pos - 20, 40, 40)
            self.target_pos = (WIDTH - 90, y_pos)

        self.connected = False
        self.dragging = False

    def reset(self):
        self.end_pos = self.start_pos
        self.dragging = False
        self.connected = False

    def update(self, cursor_pos, is_pinching, right_wires):
        if self.connected: return

        if is_pinching:
            # Toleranță (inflate) pentru a prinde cablul mai ușor
            if self.rect.inflate(20, 20).collidepoint(cursor_pos) and not self.dragging:
                self.dragging = True

            if self.dragging:
                self.end_pos = cursor_pos
        else:
            if self.dragging:
                connected_correctly = False
                for target_wire in right_wires:
                    # Verificăm dacă culoarea corespunde
                    if target_wire.color_name == self.color_name:
                        # Verificăm coliziunea cu conectorul din dreapta
                        if target_wire.rect.inflate(30, 30).collidepoint(cursor_pos):
                            self.end_pos = target_wire.target_pos
                            self.connected = True
                            connected_correctly = True
                            break
                if not connected_correctly:
                    self.reset()
                self.dragging = False

    def draw(self, surface):
        pygame.draw.rect(surface, (100, 100, 100), self.rect)
        pygame.draw.rect(surface, self.color, self.rect, 5)
        draw_symbol(surface, self.color_name, self.rect)

        if self.is_left:
            pygame.draw.line(surface, self.color, self.start_pos, self.end_pos, 15)
            pygame.draw.circle(surface, (184, 115, 51), self.end_pos, 10)


# --- GENERARE NIVEL ---
def create_level():
    left_order = COLOR_KEYS.copy()
    right_order = COLOR_KEYS.copy()
    random.shuffle(left_order)
    random.shuffle(right_order)
    l_wires, r_wires = [], []
    spacing = 100
    start_y = 150
    for i, color in enumerate(left_order):
        l_wires.append(Wire(color, start_y + i * spacing, is_left=True))
    for i, color in enumerate(right_order):
        r_wires.append(Wire(color, start_y + i * spacing, is_left=False))
    return l_wires, r_wires


# --- FUNCTIA DE START (IMPORTANTA PENTRU TRANZITIE) ---
def start_game():
    # --- INIȚIALIZARE ---
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Among Us Wiring - Hand Controller")
    clock = pygame.time.Clock()

    # Fonturi
    font_btn = pygame.font.SysFont("Arial", 20, bold=True)
    font_win = pygame.font.SysFont("Arial", 50, bold=True)

    # --- CONFIGURARE BUTON EXIT ---
    EXIT_BUTTON_RECT = pygame.Rect(20, 20, 100, 50)  # x, y, width, height
    EXIT_COLOR_NORMAL = (180, 0, 0)
    EXIT_COLOR_HOVER = (255, 50, 50)

    # Inițializare MediaPipe
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

    cap = cv2.VideoCapture(0)
    cap.set(3, CAP_WIDTH)
    cap.set(4, CAP_HEIGHT)

    # Asiguram lumina buna
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
    cap.set(cv2.CAP_PROP_EXPOSURE, 0)

    left_wires, right_wires = create_level()

    # --- DELAY DE 0.5 SECUNDE LA START ---
    # Acest lucru ajuta la tranzitia vizuala intre jocuri
    time.sleep(0.5)

    # --- BUCLA PRINCIPALĂ ---
    run = True
    while run:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:  # Resetare nivel
                    left_wires, right_wires = create_level()
                if event.key == pygame.K_ESCAPE:  # Ieșire și pe tasta ESC
                    run = False

        # 2. Webcam & MediaPipe
        success, img = cap.read()
        if not success: continue

        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)

        cursor_pos = (0, 0)
        is_pinching = False

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                h, w, c = img.shape
                x_index = int(hand_lms.landmark[8].x * WIDTH)
                y_index = int(hand_lms.landmark[8].y * HEIGHT)
                x_thumb = int(hand_lms.landmark[4].x * WIDTH)
                y_thumb = int(hand_lms.landmark[4].y * HEIGHT)

                # Cursorul este media dintre degetul mare și arătător
                cursor_pos = ((x_index + x_thumb) // 2, (y_index + y_thumb) // 2)
                distance = math.hypot(x_index - x_thumb, y_index - y_thumb)

                if distance < PINCH_THRESHOLD:
                    is_pinching = True

        # --- 3. LOGICĂ SUPLIMENTARĂ (EXIT) ---

        # Verificăm dacă cursorul este peste butonul de EXIT
        is_hovering_exit = EXIT_BUTTON_RECT.collidepoint(cursor_pos)

        # Dacă suntem peste buton și facem PINCH -> Ieșim
        if is_hovering_exit and is_pinching:
            run = False

        # --- 4. DESENARE ---
        # Convertim imaginea OpenCV pentru Pygame
        try:
            img_surface = pygame.image.frombuffer(img.tobytes(), img.shape[1::-1], "BGR")
        except AttributeError:
            # Fallback pentru versiuni mai vechi de numpy/cv2
            img_surface = pygame.image.frombuffer(img.tostring(), img.shape[1::-1], "BGR")

        img_surface = pygame.transform.scale(img_surface, (WIDTH, HEIGHT))
        img_surface.set_alpha(150)  # Transparență pentru a vedea jocul clar

        screen.fill((30, 30, 30))
        screen.blit(img_surface, (0, 0))

        # Desenare Buton EXIT
        current_btn_color = EXIT_COLOR_HOVER if is_hovering_exit else EXIT_COLOR_NORMAL
        pygame.draw.rect(screen, current_btn_color, EXIT_BUTTON_RECT, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), EXIT_BUTTON_RECT, 2, border_radius=10)  # Contur alb

        # Text Buton
        text_surf = font_btn.render("EXIT", True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=EXIT_BUTTON_RECT.center)
        screen.blit(text_surf, text_rect)

        # Desenare Cabluri (întâi cele din dreapta - țintele)
        for wire in right_wires:
            wire.draw(screen)

        # Verificăm dacă tragem vreun cablu
        dragging_any = any(w.dragging for w in left_wires)

        # Desenăm cablurile din stânga
        for wire in left_wires:
            # Actualizăm doar dacă nu tragem altceva SAU dacă acesta e cel tras
            if not dragging_any or wire.dragging:
                wire.update(cursor_pos, is_pinching, right_wires)
            wire.draw(screen)

        # Cursor
        cursor_color = (0, 255, 0) if is_pinching else (255, 0, 0)
        pygame.draw.circle(screen, cursor_color, cursor_pos, 10)
        pygame.draw.circle(screen, (255, 255, 255), cursor_pos, 12, 2)

        # Mesaj Victorie
        if all(w.connected for w in left_wires):
            text = font_win.render("GOOD JOB!", True, (0, 255, 0))
            screen.blit(text, (WIDTH // 2 - 100, HEIGHT // 2))

        pygame.display.flip()
        clock.tick(60)

    cap.release()
    # pygame.quit() # Lasam asta comentat, gestionam inchiderea din fisierul principal


if __name__ == "__main__":
    start_game()