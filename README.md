I will only explain my own contributions to this project, as this was a team effort.

The theme of this project was to make an app for a Raspberry Pi 4 that can convince high school students to come to our faculty. We decided to do this through fast-paced games, with a public leaderboard, that are based on the main areas of study of our faculty (Automation, Computer Science, Electrical Engineering).

### `harta.py`
This file acts as a level selector, using the map of the university campus, focusing on the main buildings of our faculty: Building Y (used mainly for Electrical Engineering), Building G (used mainly for Computer Science), and Building J (used mainly for Automation).

When first entering the file, you will see an aerial view of the campus. In order to proceed further, you must press **"START JOURNEY"**, after which you will be able to select one of three buildings in order to enter a game associated with that building.
To enter a game, you must first select the building you want to "enter" by using the side arrows, and then pressing the button **"Enter Building"**.

## The Games

> *Note: The automation game with the robot was not my creation and thus I will not cover it in this area.*

### Building G, the Computer Science game (`calculatoare_joc.py`)
This game uses camera body tracking via **MediaPipe**, tracking only your arms and head. The main objective of the game is to get as high a score as possible and try to survive for as long as possible.

There are 3 main objects in the game:
* **The red circles ("errors"):** You must avoid these with your head, else you will get damaged.
* **The purple circles ("restanțe" / failed exam):** Which act as minibosses. They have a health bar and deal double the damage of the red circles if they hit your head, but they also damage you if they reach the bottom of the screen without you breaking them (which you can do if you hit them fast enough with your hands).
* **The blue squares ("patches"):** You must touch these with your hands in order to gain score and a "combo"; collecting more squares in a row without losing HP increases your combo and the amount of points you get from breaking purple circles and collecting blue squares.

As the game progresses, the objects start to move faster, creating a **soft cap** on how long the game can last due to not having enough time to break the purple circles before they reach the bottom and damage you.
The time soft cap and the increased speed (as well as the fun of having to beat up and destroy the possibility of failing an exam) make this an exciting and fast-paced experience for any person that wishes to try this game.

### Building Y, the Electrical Engineering game (`electronica.py`, `electronica.bk.py`, `amogus.py`)
> *Note: `electronica.py` and `electronica.bk.py` feature the same game, but the backup is a lighter version that works a bit clunkier, existing in case the main file cannot run or is too laggy for a Raspberry Pi.*

This game uses camera tracking in order to track the light sources in the room.
The objective of the game is to "collect" the attention of the app using your phone flashlight (this can be done by activating your flashlight and then moving the flashlight over the green circle that displays the focus of the app).

Once you have gotten the focus of the app, you must then try your best to avoid other sources of light in the room whilst trying to get to the red circle on the left side of the screen; this acts as the starting point of the next part of the game.

If you are over the red circle with your light source and the focus of the app, you can press **Space** to enter the next segment, a "circuit" that you will have to go through using your flashlight, simulating light traveling through cables.

In this area, as long as you do not turn your phone away or obscure the light source in any way, no matter what, you will not lose focus of your light, even if inside your circuit there are other light sources.
* This is due to a **"fog of war"** mechanic that I added that makes it so that everything outside of the circuit gets dimmer. Since the light sources in the circuit will be blocked out by your phone as you move it through, trying to reach the end, it means you cannot lose the focus of the app unless you tilt your phone accidentally.

If you reach the finish line, congrats, your time to travel through the circuit will be imported into a leaderboard; if you exit the circuit at any point, you will trigger a short circuit.

**Short circuit:** After triggering it, your screen will shake for a bit. After this, you will be sent to `amogus.py` (THIS WAS NOT CREATED BY ME), where you have to play an *Among Us* style game where you have to connect cables in order to fix the circuit.

## Leaderboard
Each game features a leaderboard that records either the time it took to complete the game (the case for `electronica.py`) or the score you got (the case for `calculatoare_joc.py`).

To enter your score/time into the leaderboard, you must first enter 3 letters that represent your username; this is done due to the fact that it is annoying to type on a Raspberry Pi keyboard, and to also simulate the retro arcade game feel.

Once entered, your data will be uploaded into the respective `.csv` file of that game.
At the end of the games, there will be a display showing the top 5 scores of that respective game.

*The leaderboard API (`leaderboard.py`) was not developed by me; however, I was the one that implemented it into all the games.*
