import csv
import os

"""
fisierele csv vor avea denumirea jocului urmata de extensia .csv (ex: amongus_wiring.csv)
prima coloana va stoca numele, a doua scorul

IMPLEMENTARE:
    1. dati import in joc la leaderboard.py
    2. chemati functia check_score (returneaza un bool), daca returneaza True, playerul isi tasteaza numele
    3. chemati functia update_leaderboard, pasând noul nume si scor
    4. chemati functia import_highscores (returneaza o lista cu liste (numele, highscore) sortate crescator)
    5. afisati datele
"""


def export_highscores(highscores: list[list], file_path: str) -> None:
    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(highscores)
    print("CSV file updated successfully.")


def import_highscores(file_path: str) -> list[list]:
    # Verificăm dacă fișierul există, altfel returnăm listă goală
    if not os.path.exists(file_path):
        return []

    with open(file_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        highscores = []
        for row in reader:
            if row:  # Evităm rândurile goale
                # CRITIC: Convertim scorul la int, altfel sortarea e greșită ("9" > "100")
                try:
                    name = row[0]
                    score = int(row[1])
                    highscores.append([name, score])
                except ValueError:
                    continue  # Sărim peste rândurile corupte

        # Sortăm descrescător după scor (index 1)
        highscores.sort(key=lambda x: x[1], reverse=True)
        return highscores


def check_score(new_score: int, file_path: str) -> bool:
    highscores = import_highscores(file_path)

    # 1. Dacă leaderboard-ul nu e plin (< 10), orice scor intră
    if len(highscores) < 10:
        return True

    # 2. Dacă e plin, verificăm dacă e mai mare decât ultimul (cel mai mic)
    lowest_score = highscores[-1][1]
    if new_score > lowest_score:
        return True

    return False


def update_leaderboard(name: str, new_score: int, file_path: str) -> None:
    # Nu mai verificăm din nou condițiile aici, presupunem că check_score a dat True
    # sau pur și simplu forțăm inserarea și tăiem surplusul.

    highscores = import_highscores(file_path)

    # Adăugăm noul jucător
    highscores.append([name, new_score])

    # Sortăm din nou
    highscores.sort(key=lambda x: x[1], reverse=True)

    # Dacă lista depășește 10 elemente, tăiem coada
    if len(highscores) > 10:
        highscores = highscores[:10]  # Păstrăm doar primii 10

    export_highscores(highscores, file_path)
