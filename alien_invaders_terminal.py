#!/usr/bin/env python3
"""
Alien Invaders ‒ a lightweight Space Invaders‑style game for any Linux/UNIX terminal.
======================================================================
Run it with:
    python3 alien_invaders_terminal.py
Quit anytime with "q".

Controls
--------
←/→  Move ship left/right
SPACE Fire laser
q/Q  Quit

Tips
----
* The window auto‑scales to your terminal size (≥ 80×24 recommended).
* Aliens get faster after each cleared wave.
* Resize the terminal while playing if lines don’t refresh properly.

(Tested with Python ≥ 3.8 and ncurses on Debian/Ubuntu, Fedora, Arch.)
"""

import curses
import random
import time
from typing import List, Tuple

# ╭──────────────────────────────────────────────────────────╮
# │ Sprite helpers                                           │
# ╰──────────────────────────────────────────────────────────╯

class Sprite:
    def __init__(self, x: int, y: int, char: str):
        self.x = x
        self.y = y
        self.char = char

    def draw(self, win):
        try:
            win.addch(self.y, self.x, self.char)
        except curses.error:
            # Ignore drawing errors near borders
            pass

class Laser(Sprite):
    def __init__(self, x: int, y: int, direction: int):
        super().__init__(x, y, "|")
        self.dir = direction  # -1 up, 1 down

    def update(self):
        self.y += self.dir

class Player(Sprite):
    def __init__(self, x: int, y: int, max_x: int):
        super().__init__(x, y, "A")
        self.max_x = max_x

    def move(self, dx: int):
        self.x = max(1, min(self.max_x - 2, self.x + dx))

class Alien(Sprite):
    FRAMES = ["/", "V", "\\", "Λ"]

    def __init__(self, x: int, y: int):
        super().__init__(x, y, Alien.FRAMES[0])
        self.frame = 0

    def animate(self):
        self.frame = (self.frame + 1) % len(Alien.FRAMES)
        self.char = Alien.FRAMES[self.frame]

# ╭──────────────────────────────────────────────────────────╮
# │ Game state container                                     │
# ╰──────────────────────────────────────────────────────────╯

class GameState:
    def __init__(self, win):
        self.win = win
        self.height, self.width = win.getmaxyx()
        self.player = Player(self.width // 2, self.height - 2, self.width)
        self.aliens: List[Alien] = []
        self.player_lasers: List[Laser] = []
        self.alien_lasers: List[Laser] = []
        self.alien_dir = 1  # 1 → right, -1 → left
        self.tick = 0
        self.score = 0
        self.level = 1
        self.game_over = False
        self.init_aliens()

    # Create a grid of aliens
    def init_aliens(self):
        rows, cols = 5, 11
        x_margin = (self.width - cols * 4) // 2
        for r in range(rows):
            for c in range(cols):
                x = x_margin + c * 4
                y = 2 + r * 2
                self.aliens.append(Alien(x, y))

    # Speed ramps up as levels progress
    def alien_speed(self):
        return max(0.05, 0.3 - (self.level - 1) * 0.03)

# ╭──────────────────────────────────────────────────────────╮
# │ Main game loop                                           │
# ╰──────────────────────────────────────────────────────────╯

def play(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    state = GameState(stdscr)

    last_move = time.time()
    last_anim = time.time()

    while not state.game_over:
        now = time.time()
        key = stdscr.getch()

        # ── Input ──────────────────────────────
        if key in (ord("q"), ord("Q")):
            break
        elif key == curses.KEY_LEFT:
            state.player.move(-1)
        elif key == curses.KEY_RIGHT:
            state.player.move(1)
        elif key in (ord(" "), ord("z")):
            # Fire
            if len(state.player_lasers) < 3:  # limit shots on screen
                state.player_lasers.append(Laser(state.player.x, state.player.y - 1, -1))

        # ── Update aliens movement ────────────
        if now - last_move > state.alien_speed():
            edge_hit = False
            for alien in state.aliens:
                alien.x += state.alien_dir
                # Check borders
                if alien.x <= 1 or alien.x >= state.width - 2:
                    edge_hit = True
            if edge_hit:
                state.alien_dir *= -1
                for alien in state.aliens:
                    alien.y += 1
                    # If an alien reaches the player row → game over
                    if alien.y >= state.player.y:
                        state.game_over = True
            last_move = now

        # ── Alien animation ───────────────────
        if now - last_anim > 0.3:
            for alien in state.aliens:
                alien.animate()
            last_anim = now

        # ── Aliens fire randomly ──────────────
        if state.aliens and random.random() < 0.02:
            shooter = random.choice(state.aliens)
            state.alien_lasers.append(Laser(shooter.x, shooter.y + 1, 1))

        # ── Update lasers ─────────────────────
        for laser in state.player_lasers[:]:
            laser.update()
            if laser.y <= 1:
                state.player_lasers.remove(laser)

        for laser in state.alien_lasers[:]:
            laser.update()
            if laser.y >= state.height - 1:
                state.alien_lasers.remove(laser)

        # ── Collisions ────────────────────────
        # Player lasers hit aliens
        for laser in state.player_lasers[:]:
            for alien in state.aliens[:]:
                if laser.x == alien.x and laser.y == alien.y:
                    state.aliens.remove(alien)
                    state.player_lasers.remove(laser)
                    state.score += 10
                    break

        # Alien lasers hit player
        for laser in state.alien_lasers[:]:
            if laser.x == state.player.x and laser.y == state.player.y:
                state.game_over = True

        # Check level cleared
        if not state.aliens:
            state.level += 1
            state.init_aliens()
            state.player_lasers.clear()
            state.alien_lasers.clear()

        # ── Draw everything ───────────────────
        stdscr.erase()
        # Borders
        stdscr.border()
        # Score & level
        stdscr.addstr(0, 2, f" Score: {state.score} ")
        stdscr.addstr(0, state.width - 15, f" Level: {state.level} ")

        # Draw sprites
        state.player.draw(stdscr)
        for s in state.aliens + state.player_lasers + state.alien_lasers:
            s.draw(stdscr)

        stdscr.refresh()
        time.sleep(0.01)

    # ── Game over screen ──────────────────────
    stdscr.nodelay(False)
    msg = "GAME OVER ‒ Press any key to exit"
    stdscr.addstr(state.height // 2, (state.width - len(msg)) // 2, msg)
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(play)
