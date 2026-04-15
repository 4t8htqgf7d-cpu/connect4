import tkinter as tk
from tkinter import font as tkfont
import threading
import random
import math

ROWS, COLS = 6, 7
CELL = 90
PAD  = 12
WIDTH  = COLS * CELL + (COLS + 1) * PAD
HEIGHT = ROWS * CELL + (ROWS + 1) * PAD

BG       = "#12122a"
BOARD    = "#1565c0"
BOARD_LT = "#1976d2"   # top edge of board gradient
EMPTY    = "#0b3d8f"   # deeper hole colour
HOLE_RIM = "#0d47a1"   # rim around the hole
RED      = "#e53935"
RED_HL   = "#ff6b6b"   # specular highlight colour
YELLOW   = "#fdd835"
YEL_HL   = "#ffe57f"
WHITE    = "#eeeeee"
GREY     = "#888888"
INDIGO   = "#3949ab"   # mode button colour (replaces teal)

# Difficulty → minimax depth (0 = random / Easy)
DIFFICULTIES = [("Easy", 0), ("Medium", 3), ("Hard", 6)]


# ── AI helpers ──────────────────────────────────────────────────────────────
def get_open_row(board, col):
    for r in range(ROWS - 1, -1, -1):
        if board[r][col] is None:
            return r
    return -1


def check_win(board, row, col, player):
    dirs = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dr, dc in dirs:
        cells = [(row, col)]
        for sign in (1, -1):
            r, c = row + dr * sign, col + dc * sign
            while 0 <= r < ROWS and 0 <= c < COLS and board[r][c] == player:
                cells.append((r, c))
                r += dr * sign
                c += dc * sign
        if len(cells) >= 4:
            return cells
    return None


def score_window(window, player):
    opp = "red" if player == "yellow" else "yellow"
    p = window.count(player)
    e = window.count(None)
    o = window.count(opp)
    if p == 4:            return  100
    if p == 3 and e == 1: return    5
    if p == 2 and e == 2: return    2
    if o == 3 and e == 1: return   -4
    if o == 4:            return -100
    return 0


def score_board(board, player):
    s = 0
    for r in range(ROWS):
        if board[r][3] == player:     s += 3
        elif board[r][3] is not None: s -= 3
    dirs = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in dirs:
                w = []
                for i in range(4):
                    nr, nc = r + dr * i, c + dc * i
                    if 0 <= nr < ROWS and 0 <= nc < COLS:
                        w.append(board[nr][nc])
                if len(w) == 4:
                    s += score_window(w, player)
    return s


def minimax(board, depth, alpha, beta, maximizing, ai_player):
    human = "red" if ai_player == "yellow" else "yellow"
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] is not None:
                if check_win(board, r, c, board[r][c]):
                    return (1000 + depth) if board[r][c] == ai_player else -(1000 + depth)
    if depth == 0 or all(board[0][c] is not None for c in range(COLS)):
        return score_board(board, ai_player)

    if maximizing:
        val = -10**9
        for c in range(COLS):
            r = get_open_row(board, c)
            if r == -1:
                continue
            board[r][c] = ai_player
            val = max(val, minimax(board, depth - 1, alpha, beta, False, ai_player))
            board[r][c] = None
            alpha = max(alpha, val)
            if alpha >= beta:
                break
        return val
    else:
        val = 10**9
        for c in range(COLS):
            r = get_open_row(board, c)
            if r == -1:
                continue
            board[r][c] = human
            val = min(val, minimax(board, depth - 1, alpha, beta, True, ai_player))
            board[r][c] = None
            beta = min(beta, val)
            if alpha >= beta:
                break
        return val


def best_move(board, ai_player, depth):
    if depth == 0:
        valid = [c for c in range(COLS) if get_open_row(board, c) != -1]
        return random.choice(valid)
    best_val, best_col = -10**9, 3
    for c in range(COLS):
        r = get_open_row(board, c)
        if r == -1:
            continue
        board[r][c] = ai_player
        val = minimax(board, depth, -10**9, 10**9, False, ai_player)
        board[r][c] = None
        if val > best_val:
            best_val, best_col = val, c
    return best_col


# ── Fireworks particle system ────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 8)
        self.x  = x
        self.y  = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.r  = random.randint(3, 6)
        self.color = color
        self.life  = random.randint(40, 80)
        self.max_life = self.life
        self._id = None  # canvas item id

    def step(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.18   # gravity
        self.vx *= 0.99
        self.life -= 2


# ── Main game window ─────────────────────────────────────────────────────────
class Connect4(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Connect 4")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.board        = [[None] * COLS for _ in range(ROWS)]
        self.current      = "red"
        self.game_over    = False
        self.vs_ai        = False
        self.ai_depth     = 0       # Easy by default
        self.scores       = {"red": 0, "yellow": 0, "draw": 0}
        self.win_cells    = []
        self.flash_on     = False
        self._flash_job   = None
        self.hover_col    = None
        self._fw_job      = None
        self._particles   = []

        self._build_ui()
        self.bind("<Motion>",   self._on_mouse_move)
        self.bind("<Button-1>", self._on_click)

    # ── UI construction ──────────────────────────────────────────
    def _build_ui(self):
        big   = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        med   = tkfont.Font(family="Segoe UI", size=12)
        small = tkfont.Font(family="Segoe UI", size=10)
        tiny  = tkfont.Font(family="Segoe UI", size=9, weight="bold")

        tk.Label(self, text="CONNECT 4", bg=BG, fg="#f0c040", font=big).pack(pady=(18, 4))

        # Score bar
        score_frame = tk.Frame(self, bg=BG)
        score_frame.pack(pady=(0, 8))

        self.lbl_p1 = tk.Label(score_frame, text="Player 1", bg=BG, fg=RED,    font=small)
        self.lbl_p1.grid(row=0, column=0, padx=20)
        tk.Label(score_frame, text="Draws",    bg=BG, fg=GREY,   font=small).grid(row=0, column=1, padx=20)
        self.lbl_p2 = tk.Label(score_frame, text="Player 2", bg=BG, fg=YELLOW, font=small)
        self.lbl_p2.grid(row=0, column=2, padx=20)

        self.score_red  = tk.Label(score_frame, text="0", bg=BG, fg=RED,    font=big)
        self.score_red.grid(row=1, column=0, padx=20)
        self.score_draw = tk.Label(score_frame, text="0", bg=BG, fg=GREY,   font=big)
        self.score_draw.grid(row=1, column=1, padx=20)
        self.score_yel  = tk.Label(score_frame, text="0", bg=BG, fg=YELLOW, font=big)
        self.score_yel.grid(row=1, column=2, padx=20)

        # Status
        self.status_var = tk.StringVar(value="Red's turn")
        self.status_lbl = tk.Label(self, textvariable=self.status_var, bg=BG, fg=RED, font=med)
        self.status_lbl.pack(pady=(0, 8))

        # Main canvas (board + fireworks share the same canvas)
        self.canvas = tk.Canvas(self, width=WIDTH, height=HEIGHT,
                                bg=BOARD, highlightthickness=0)
        self.canvas.pack(padx=20)

        # Button row
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=(10, 4))

        tk.Button(btn_frame, text="New Game", command=self._new_game,
                  bg="#f0c040", fg=BG, font=med, padx=16, pady=6,
                  relief="flat", cursor="hand2").grid(row=0, column=0, padx=8)

        self.mode_btn = tk.Button(btn_frame, text="vs CPU",
                                  command=self._toggle_mode,
                                  bg=INDIGO, fg="white", font=med,
                                  padx=16, pady=6, relief="flat", cursor="hand2")
        self.mode_btn.grid(row=0, column=1, padx=8)

        # Difficulty row (shown only in CPU mode)
        self.diff_frame = tk.Frame(self, bg=BG)
        self.diff_frame.pack(pady=(4, 14))

        tk.Label(self.diff_frame, text="Difficulty:", bg=BG, fg=GREY,
                 font=small).grid(row=0, column=0, padx=(0, 6))

        self._diff_btns = []
        for i, (label, depth) in enumerate(DIFFICULTIES):
            colors = {
                "Easy":   ("#2e7d32", "#4caf50"),
                "Medium": ("#e65100", "#ff9800"),
                "Hard":   ("#b71c1c", "#ef5350"),
            }
            bg_on, _ = colors[label]
            btn = tk.Button(
                self.diff_frame, text=label, font=tiny,
                padx=10, pady=3, relief="flat", cursor="hand2",
                command=lambda d=depth, idx=i: self._set_difficulty(d, idx)
            )
            btn.grid(row=0, column=i + 1, padx=4)
            self._diff_btns.append((btn, bg_on, label))

        self._set_difficulty(0, 0)   # start on Easy
        self.diff_frame.pack_forget() # hidden until CPU mode

        self._draw_board()

    # ── Difficulty ───────────────────────────────────────────────
    def _set_difficulty(self, depth, active_idx):
        self.ai_depth = depth
        labels = {"Easy": ("#2e7d32","#fff"), "Medium": ("#e65100","#fff"), "Hard": ("#b71c1c","#fff")}
        for i, (btn, bg_on, label) in enumerate(self._diff_btns):
            if i == active_idx:
                btn.config(bg=bg_on, fg="#fff", relief="solid")
            else:
                btn.config(bg="#16213e", fg=GREY, relief="flat")

    # ── Drawing ──────────────────────────────────────────────────
    def _cell_xy(self, row, col):
        x = PAD + col * (CELL + PAD) + CELL // 2
        y = PAD + row * (CELL + PAD) + CELL // 2
        return x, y

    def _draw_board(self):
        self.canvas.delete("board")
        for r in range(ROWS):
            for c in range(COLS):
                self._draw_cell(r, c)

    def _draw_cell(self, r, c, flash=False):
        x, y = self._cell_xy(r, c)
        margin = 4
        x0, x1 = x - CELL // 2 + margin, x + CELL // 2 - margin
        y0, y1 = y - CELL // 2 + margin, y + CELL // 2 - margin
        val = self.board[r][c]

        if val is None:
            # Dark rim (hole edge)
            self.canvas.create_oval(x0 - 2, y0 - 2, x1 + 2, y1 + 2,
                                    fill="#071e4a", outline="", tags="board")
            is_ghost = (not self.game_over and self.hover_col == c
                        and get_open_row(self.board, c) == r)
            if is_ghost:
                ghost = RED_HL if self.current == "red" else YEL_HL
                self.canvas.create_oval(x0, y0, x1, y1,
                                        fill=ghost, outline="", stipple="gray50", tags="board")
            else:
                self.canvas.create_oval(x0, y0, x1, y1,
                                        fill=EMPTY, outline="", tags="board")
        else:
            # Base piece colour
            base  = (RED_HL  if flash else RED)    if val == "red" else (YEL_HL if flash else YELLOW)
            dark  = "#b71c1c" if val == "red" else "#f57f17"
            # Dark bottom shadow oval
            self.canvas.create_oval(x0, y0 + 4, x1, y1 + 4,
                                    fill=dark, outline="", tags="board")
            # Main piece
            self.canvas.create_oval(x0, y0, x1, y1,
                                    fill=base, outline="", tags="board")
            # Specular highlight (small bright oval, top-left)
            hw = (x1 - x0) * 0.32
            hh = (y1 - y0) * 0.18
            hx, hy = x0 + (x1 - x0) * 0.28, y0 + (y1 - y0) * 0.18
            self.canvas.create_oval(hx, hy, hx + hw, hy + hh,
                                    fill="white", outline="", stipple="gray50", tags="board")

    def _redraw_win_cells(self):
        if not self.win_cells:
            return
        self.flash_on = not self.flash_on
        for wr, wc in self.win_cells:
            self._draw_cell(wr, wc, flash=self.flash_on)
        self._flash_job = self.after(500, self._redraw_win_cells)

    # ── Fireworks ────────────────────────────────────────────────
    def _launch_fireworks(self, winner):
        if self._fw_job:
            self.after_cancel(self._fw_job)
        self.canvas.delete("fw")
        self._particles = []

        red_colors    = ["#ef5350","#ff8a80","#ff1744","#ffcdd2","#ff6d00","white"]
        yellow_colors = ["#fdd835","#fff176","#ffea00","#fffde7","#ff6f00","white"]
        colors = red_colors if winner == "red" else yellow_colors

        # Several bursts at staggered times
        for i in range(6):
            self.after(i * 400, lambda c=colors: self._burst(c))

        self._fw_animate()

    def _burst(self, colors):
        cx = random.randint(WIDTH  // 5, WIDTH  * 4 // 5)
        cy = random.randint(HEIGHT // 6, HEIGHT * 2 // 3)
        for _ in range(90):
            p = Particle(cx, cy, random.choice(colors))
            self._particles.append(p)

    def _fw_animate(self):
        self.canvas.delete("fw")
        alive = []
        for p in self._particles:
            p.step()
            if p.life > 0:
                alpha_ratio = p.life / p.max_life
                # Fake alpha by blending toward background colour
                colour = p.color
                r0, r1 = p.x - p.r, p.x + p.r
                c0, c1 = p.y - p.r, p.y + p.r
                self.canvas.create_oval(r0, c0, r1, c1,
                                        fill=colour, outline="", tags="fw")
                alive.append(p)
        self._particles = alive
        if self._particles:
            self._fw_job = self.after(30, self._fw_animate)
        else:
            self._fw_job = None

    # ── Interaction ──────────────────────────────────────────────
    def _col_from_x(self, x):
        for c in range(COLS):
            lx = PAD + c * (CELL + PAD)
            if lx <= x <= lx + CELL:
                return c
        return None

    def _on_mouse_move(self, event):
        if self.game_over:
            return
        try:
            cx = self.canvas.winfo_rootx()
            rx = event.x_root - cx
        except Exception:
            return
        col = self._col_from_x(rx)
        if col != self.hover_col:
            self.hover_col = col
            self._draw_board()

    def _on_click(self, event):
        if self.game_over:
            return
        if self.vs_ai and self.current == "yellow":
            return
        cx = self.canvas.winfo_rootx()
        rx = event.x_root - cx
        col = self._col_from_x(rx)
        if col is not None:
            self._drop(col)

    def _drop(self, col):
        row = get_open_row(self.board, col)
        if row == -1:
            return

        self.board[row][col] = self.current
        self._draw_board()

        wins = check_win(self.board, row, col, self.current)
        if wins:
            self.win_cells = wins
            self.scores[self.current] += 1
            self._update_scores()
            name = "Red" if self.current == "red" else ("CPU" if self.vs_ai else "Yellow")
            self._set_status(f"{name} wins!", self.current)
            self.game_over = True
            self._redraw_win_cells()
            self._launch_fireworks(self.current)
            return

        if all(self.board[0][c] is not None for c in range(COLS)):
            self.scores["draw"] += 1
            self._update_scores()
            self._set_status("It's a draw!", None)
            self.game_over = True
            return

        self.current = "yellow" if self.current == "red" else "red"

        if self.vs_ai and self.current == "yellow":
            self._set_status("CPU is thinking…", "yellow")
            self.after(50, self._ai_move)
        else:
            name = "Red" if self.current == "red" else "Yellow"
            self._set_status(f"{name}'s turn", self.current)

    def _ai_move(self):
        depth = self.ai_depth

        def run():
            col = best_move(self.board, "yellow", depth)
            self.after(0, lambda: self._drop(col))

        threading.Thread(target=run, daemon=True).start()

    # ── Helpers ──────────────────────────────────────────────────
    def _set_status(self, text, player):
        self.status_var.set(text)
        if player == "red":       self.status_lbl.config(fg=RED)
        elif player == "yellow":  self.status_lbl.config(fg=YELLOW)
        else:                     self.status_lbl.config(fg=WHITE)

    def _update_scores(self):
        self.score_red.config( text=str(self.scores["red"]))
        self.score_yel.config( text=str(self.scores["yellow"]))
        self.score_draw.config(text=str(self.scores["draw"]))

    def _new_game(self):
        for job in (self._flash_job, self._fw_job):
            if job:
                self.after_cancel(job)
        self._flash_job = self._fw_job = None
        self.canvas.delete("fw")
        self._particles = []
        self.board      = [[None] * COLS for _ in range(ROWS)]
        self.current    = "red"
        self.game_over  = False
        self.win_cells  = []
        self.flash_on   = False
        self.hover_col  = None
        self._draw_board()
        self._set_status("Red's turn", "red")

    def _toggle_mode(self):
        self.vs_ai = not self.vs_ai
        self.mode_btn.config(text="vs Human" if self.vs_ai else "vs CPU")
        self.lbl_p2.config(text="CPU" if self.vs_ai else "Player 2")
        if self.vs_ai:
            self.diff_frame.pack(pady=(4, 14))
        else:
            self.diff_frame.pack_forget()
        self.scores = {"red": 0, "yellow": 0, "draw": 0}
        self._update_scores()
        self._new_game()


if __name__ == "__main__":
    app = Connect4()
    app.mainloop()
