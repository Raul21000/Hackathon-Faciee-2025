import cv2
import numpy as np
import pygame
import math
import random
import sys
import os
import leaderboard  # NOU: Importul modulului extern

# --- IMPORT SAFE PENTRU AMOGUS ---
try:
    import amogus
except ImportError:
    print("ATENTIE: 'amogus.py' lipseste.")
    amogus = None

# --- CONFIGURARE ---
WINDOW_SIZE = (800, 480)
TRACK_WIDTH = 50
# Calea fișierului pentru clasament este acum CSV
LEADERBOARD_GAME_FILE = "electronica.csv"

# Culori
BLACK = (20, 20, 20)
GREEN_TRACE = (0, 200, 0)
PAD_COLOR = (192, 192, 192)
SOLDER_COLOR = (255, 255, 200)
FAIL_COLOR = (255, 50, 50)
TRACKER_OUTLINE_COLOR = (0, 255, 255)  # Cyan
COLOR_HIGHSCORE = (0, 255, 255)  # Cyan neon
COLOR_INPUT_BG = (50, 50, 50)
COLOR_TEXT = (255, 255, 255)

# Variabile Calibrare IMPLICITE
sensitivity = 240
lower_color = np.array([0, 0, sensitivity])
upper_color = np.array([180, 60, 255])

# Variabile Tracking
last_cx = 320
last_cy = 240
has_lock = False
SEARCH_RADIUS = 150

# START ZONE CONSTANT
START_ZONE_RADIUS = TRACK_WIDTH // 2 + 5


# --- FUNCTII VECHI DE LEADERBOARD AU FOST ELIMINATE ---
# load_leaderboard() și save_score_to_file() nu mai sunt necesare.


def create_level_surface():
    surf = pygame.Surface(WINDOW_SIZE)
    surf.fill(BLACK)

    points = [
        (50, 240), (150, 240), (200, 100), (350, 100),
        (400, 380), (550, 380), (600, 240), (750, 240)
    ]

    pygame.draw.lines(surf, GREEN_TRACE, False, points, TRACK_WIDTH)
    for p in points:
        pygame.draw.circle(surf, GREEN_TRACE, p, TRACK_WIDTH // 2)

    pygame.draw.circle(surf, PAD_COLOR, points[0], TRACK_WIDTH - 5)
    pygame.draw.circle(surf, PAD_COLOR, points[-1], TRACK_WIDTH - 5)

    font = pygame.font.SysFont('Arial', 20, bold=True)

    # Scrisul ALB
    surf.blit(font.render("START", True, (255, 255, 255)), (25, 230))
    surf.blit(font.render("LED", True, (255, 255, 255)), (730, 230))

    return surf, points[0], points[-1]


def create_circuit_mask_opencv(level_surf):
    """Create OpenCV mask from pygame surface - white where circuit exists"""
    # Convert pygame surface to numpy array
    arr = pygame.surfarray.array3d(level_surf)
    # Transpose to get correct orientation (width, height, channels) -> (height, width, channels)
    arr = np.transpose(arr, (1, 0, 2))

    # Create mask: white (255) where green channel > 50, else black (0)
    mask = np.where(arr[:, :, 1] > 50, 255, 0).astype(np.uint8)

    return mask


def update_color_bounds():
    global lower_color, upper_color, sensitivity
    lower_color = np.array([0, 0, sensitivity])
    upper_color = np.array([180, 100, 255])


def main():
    global sensitivity, last_cx, last_cy, has_lock

    pygame.init()
    # NOFRAME removes the top bar
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.NOFRAME)
    pygame.display.set_caption("PCB Solder - Auto Flashlight Mode")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont('Arial', 30, bold=True)
    big_font = pygame.font.SysFont('Consolas', 50, bold=True)
    small_font = pygame.font.SysFont('Arial', 20)
    font_leaderboard = pygame.font.SysFont('Consolas', 25, bold=True)

    cap = cv2.VideoCapture(0)
    # Warmup rapid
    for _ in range(5): cap.read()

    level_surf, start_pos, end_pos = create_level_surface()
    circuit_mask = create_circuit_mask_opencv(level_surf)

    player_pos = list(start_pos)
    target_pos = list(start_pos)

    visual_tracking_pos = None
    visual_tracking_radius = 10

    game_state = "CALIBRATE"
    fail_timer = 0
    shake_offset = [0, 0]
    in_start_zone = False

    # Leaderboard Variables
    input_name = ""
    current_leaderboard_data = []
    final_score = 0
    start_time = 0

    # Tracking Variables
    last_cx, last_cy = 320, 240
    has_lock = False

    # Variabilă pentru a preveni re-verificarea scorului în același frame (logica veche)
    score_checked_on_win = False

    running = True
    while running:
        # --- EVENIMENTE SI INPUT ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

            # INPUT NUME (Dupa WIN)
            if game_state == "INPUT_NAME":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        input_name = input_name[:-1]
                    elif event.key == pygame.K_RETURN:
                        if len(input_name) == 3:
                            # PASUL 3: Salvarea scorului prin modulul extern
                            leaderboard.update_leaderboard(input_name, final_score, LEADERBOARD_GAME_FILE)

                            # PASUL 4: Citirea clasamentului actualizat
                            current_leaderboard_data = leaderboard.import_highscores(LEADERBOARD_GAME_FILE)

                            game_state = "SHOW_LEADERBOARD"

                    elif len(input_name) < 3:
                        if event.unicode.isalnum():
                            input_name += event.unicode.upper()

            # RESTART (Dupa Leaderboard)
            elif game_state == "SHOW_LEADERBOARD":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    game_state = "CALIBRATE"
                    player_pos = list(start_pos)
                    target_pos = list(start_pos)
                    input_name = ""
                    has_lock = False
                    score_checked_on_win = False  # Reset

            # GAME CONTROLS
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    if game_state == "CALIBRATE":
                        if event.key == pygame.K_SPACE:
                            in_start_zone = False
                            if visual_tracking_pos:
                                dist_to_start = math.hypot(visual_tracking_pos[0] - start_pos[0],
                                                           visual_tracking_pos[1] - start_pos[1])
                                if dist_to_start < START_ZONE_RADIUS:
                                    in_start_zone = True

                            if visual_tracking_pos and in_start_zone:
                                game_state = "PLAY"
                                player_pos = list(target_pos)
                                start_time = pygame.time.get_ticks()
                            elif not visual_tracking_pos:
                                print("Nu vad lumina!")
                            elif not in_start_zone:
                                print("Trebuie sa fii in cercul de START!")

        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        cam_h, cam_w, _ = frame.shape

        keys = pygame.key.get_pressed()

        if game_state == "CALIBRATE":
            if keys[pygame.K_UP]:
                sensitivity = min(sensitivity + 1, 255)
                update_color_bounds()
            if keys[pygame.K_DOWN]:
                sensitivity = max(sensitivity - 1, 100)
                update_color_bounds()

        # --- PROCESARE VIDEO ---
        mask = cv2.inRange(hsv, lower_color, upper_color)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # APPLY CIRCUIT MASK IN PLAY MODE
        if game_state == "PLAY":
            # Resize circuit mask to camera resolution
            circuit_mask_cam = cv2.resize(circuit_mask, (cam_w, cam_h), interpolation=cv2.INTER_NEAREST)
            # Apply mask: only keep light detections within circuit area
            mask = cv2.bitwise_and(mask, mask, mask=circuit_mask_cam)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        found_target_this_frame = False
        current_contour = None

        if cnts:
            if not has_lock:
                c = max(cnts, key=cv2.contourArea)
                if cv2.contourArea(c) > 50:
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        last_cx = int(M["m10"] / M["m00"])
                        last_cy = int(M["m01"] / M["m00"])
                        has_lock = True
                        found_target_this_frame = True
                        current_contour = c
            else:
                best_contour = None
                min_dist = SEARCH_RADIUS
                temp_cx, temp_cy = 0, 0

                for c in cnts:
                    if cv2.contourArea(c) < 50: continue
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        dist = math.hypot(cx - last_cx, cy - last_cy)
                        if dist < min_dist:
                            min_dist = dist
                            best_contour = c
                            temp_cx = cx
                            temp_cy = cy

                if best_contour is not None:
                    last_cx = temp_cx
                    last_cy = temp_cy
                    found_target_this_frame = True
                    current_contour = best_contour

        if found_target_this_frame:
            screen_x = int((last_cx / cam_w) * WINDOW_SIZE[0])
            screen_y = int((last_cy / cam_h) * WINDOW_SIZE[1])
            visual_tracking_pos = (screen_x, screen_y)
            target_pos[0] = target_pos[0] * 0.5 + screen_x * 0.5
            target_pos[1] = target_pos[1] * 0.5 + screen_y * 0.5
            if current_contour is not None:
                visual_tracking_radius = int(math.sqrt(cv2.contourArea(current_contour)) / 2)
        else:
            visual_tracking_pos = None

        # --- LOGICA JOC ---
        shake_offset = [0, 0]

        if game_state == "PLAY":
            player_pos[0] += (target_pos[0] - player_pos[0]) * 0.2
            player_pos[1] += (target_pos[1] - player_pos[1]) * 0.2

            px, py = int(player_pos[0]), int(player_pos[1])
            px = max(0, min(WINDOW_SIZE[0] - 1, px))
            py = max(0, min(WINDOW_SIZE[1] - 1, py))

            try:
                col = level_surf.get_at((px, py))
                if col.g < 50 and col.r < 50 and col.b < 50:
                    game_state = "FAIL"
                    fail_timer = 120
            except:
                pass

            if math.hypot(px - end_pos[0], py - end_pos[1]) < 30:
                elapsed_time = (pygame.time.get_ticks() - start_time) / 1000.0
                time_penalty = int(elapsed_time * 100)
                final_score = max(100, 10000 - time_penalty)

                # NOU: VERIFICARE SCOR DUPA WIN
                if not score_checked_on_win:
                    # PASUL 2: Chemati check_score
                    if leaderboard.check_score(final_score, LEADERBOARD_GAME_FILE):
                        game_state = "INPUT_NAME"
                    else:
                        # Dacă nu este High Score, citim clasamentul pentru afișare
                        # PASUL 4 (pentru afișare imediată)
                        current_leaderboard_data = leaderboard.import_highscores(LEADERBOARD_GAME_FILE)
                        game_state = "SHOW_LEADERBOARD"
                    score_checked_on_win = True


        elif game_state == "FAIL":
            fail_timer -= 1

            if fail_timer > 60:
                shake_offset = [random.randint(-15, 15), random.randint(-15, 15)]

            if fail_timer <= 0:
                print("Lansare task reparatie...")
                cap.release()
                pygame.quit()
                if amogus: amogus.start_game()
                sys.exit()

        # --- DESENARE ---
        screen.fill(BLACK)

        dest_rect = level_surf.get_rect()
        dest_rect.move_ip(shake_offset)
        screen.blit(level_surf, dest_rect)

        player_draw = (int(player_pos[0] + shake_offset[0]), int(player_pos[1] + shake_offset[1]))
        if game_state != "CALIBRATE":
            pygame.draw.circle(screen, SOLDER_COLOR, player_draw, 15)

        cx, cy = WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2

        # --- ECRAN CALIBRARE ---
        if game_state == "CALIBRATE":
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, WINDOW_SIZE)
            surf_cam = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
            screen.blit(surf_cam, (0, 0))

            if visual_tracking_pos:
                dist_to_start = math.hypot(visual_tracking_pos[0] - start_pos[0], visual_tracking_pos[1] - start_pos[1])
                in_start_zone = dist_to_start < START_ZONE_RADIUS
            else:
                in_start_zone = False

            start_ring_color = (0, 255, 0) if in_start_zone else (255, 0, 0)
            pygame.draw.circle(screen, start_ring_color, start_pos, START_ZONE_RADIUS, 3)
            pygame.draw.line(screen, start_ring_color, (start_pos[0] - 10, start_pos[1]),
                             (start_pos[0] + 10, start_pos[1]), 1)
            pygame.draw.line(screen, start_ring_color, (start_pos[0], start_pos[1] - 10),
                             (start_pos[0], start_pos[1] + 10), 1)

            pygame.draw.rect(screen, (0, 0, 0), (0, 0, 350, 100))
            screen.blit(small_font.render(f"Prag Lumina: {sensitivity}", True, (200, 200, 200)), (10, 10))

            if not found_target_this_frame:
                status_txt = "CAUT LUMINA..."
                col_status = (255, 0, 0)
            elif not in_start_zone:
                status_txt = "POZITIONEAZA LA START"
                col_status = (255, 100, 0)
            else:
                status_txt = "SPACE - START"
                col_status = (0, 255, 0)
            screen.blit(font.render(status_txt, True, col_status), (10, 50))

            if visual_tracking_pos:
                pygame.draw.circle(screen, (0, 255, 0), visual_tracking_pos, visual_tracking_radius + 5, 2)

        # --- ECRAN PLAY - Draw tracking indicator ---
        elif game_state == "PLAY":
            if visual_tracking_pos:
                pygame.draw.circle(screen, (0, 255, 255), visual_tracking_pos, visual_tracking_radius + 5, 2)
                pygame.draw.circle(screen, (255, 255, 0), visual_tracking_pos, 3)

        # --- ECRAN FAIL ---
        elif game_state == "FAIL":
            if fail_timer > 60:
                txt = big_font.render("SCURTCIRCUIT!", True, (255, 0, 0))
                screen.blit(txt, (WINDOW_SIZE[0] // 2 - txt.get_width() // 2, WINDOW_SIZE[1] // 2))
            else:
                popup_rect = pygame.Rect(150, 100, 500, 280)
                pygame.draw.rect(screen, (50, 50, 50), popup_rect)
                pygame.draw.rect(screen, (255, 255, 255), popup_rect, 4)

                msg1 = font.render("PLACA STRICATA!", True, (255, 50, 50))
                msg2 = font.render("SE CERE REPARATIE MANUALA", True, (255, 255, 255))
                msg3 = font.render("SE INCARCA...", True, (0, 255, 0))

                screen.blit(msg1, (popup_rect.centerx - msg1.get_width() // 2, 140))
                screen.blit(msg2, (popup_rect.centerx - msg2.get_width() // 2, 190))
                screen.blit(msg3, (popup_rect.centerx - msg3.get_width() // 2, 300))

        # --- ECRAN INPUT NAME ---
        elif game_state == "INPUT_NAME":
            overlay = pygame.Surface(WINDOW_SIZE)
            overlay.set_alpha(240)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            txt_win = big_font.render("LIPITURA PERFECTA!", True, (0, 255, 0))
            screen.blit(txt_win, (cx - txt_win.get_width() // 2, 50))

            txt_score = font.render(f"SCOR: {final_score}", True, COLOR_HIGHSCORE)
            screen.blit(txt_score, (cx - txt_score.get_width() // 2, 120))

            txt_prompt = small_font.render("INTRODUCE INITIALE (3):", True, (255, 255, 255))
            screen.blit(txt_prompt, (cx - txt_prompt.get_width() // 2, 200))

            input_rect = pygame.Rect(cx - 100, 230, 200, 60)
            pygame.draw.rect(screen, COLOR_INPUT_BG, input_rect)
            pygame.draw.rect(screen, COLOR_HIGHSCORE, input_rect, 3)

            txt_input = big_font.render(input_name, True, (255, 255, 0))
            screen.blit(txt_input, (cx - txt_input.get_width() // 2, 235))

            if len(input_name) == 3:
                txt_enter = small_font.render("APASA [ENTER] PENTRU A SALVA", True, (0, 255, 0))
                if (pygame.time.get_ticks() // 500) % 2 == 0:
                    screen.blit(txt_enter, (cx - txt_enter.get_width() // 2, 310))

        # --- ECRAN SHOW LEADERBOARD ---
        elif game_state == "SHOW_LEADERBOARD":
            overlay = pygame.Surface(WINDOW_SIZE)
            overlay.set_alpha(240)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            txt_lb = big_font.render("TOP INGINERI", True, COLOR_HIGHSCORE)
            screen.blit(txt_lb, (cx - txt_lb.get_width() // 2, 40))

            start_y = 130
            # PASUL 5: Afișarea clasamentului
            for i, (name, s) in enumerate(current_leaderboard_data):
                # Afișăm doar primele 5 intrări pentru a se potrivi cu logica veche de afișare
                if i >= 5: break

                color = COLOR_HIGHSCORE if i == 0 else (255, 255, 255)
                txt_name = font.render(f"{i + 1}. {name}", True, color)
                txt_s = font.render(str(s), True, color)
                screen.blit(txt_name, (cx - 150, start_y + i * 40))
                screen.blit(txt_s, (cx + 80, start_y + i * 40))

            txt_restart = small_font.render("APASA [SPACE] PENTRU RESTART", True, (200, 200, 200))
            if (pygame.time.get_ticks() // 700) % 2 == 0:
                screen.blit(txt_restart, (cx - txt_restart.get_width() // 2, 400))

        pygame.display.flip()
        clock.tick(60)

    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()