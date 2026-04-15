import tkinter as tk
from tkinter import font as tkfont
import threading
import time

ROWS, COLS = 6, 7
CELL = 90
PAD  = 12
WIDTH  = COLS * CELL + (COLS + 1) * PAD
HEIGHT = ROWS * CELL + (ROWS + 1) * PAD

BG      = "#1a1a2e"
BOARD   = "#1565c0"
EMPTY   = "#0d47a1"
RED     = "#e53935"
YELLOW  = "#fdd835"
RED_HL  = "#ff8a80"
YEL_HL  = "#fff176"
WHITE   = "#eeeeee"
GREY    = "#aaaaaa"


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
    if p == 4:           return  100
    if p == 3 and e == 1: return   5
    if p == 2 and e == 2: return   2
    if o == 3 and e == 1: return  -4
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
    # Check for terminal win
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


def best_move(board, ai_player):
    best_val, best_col = -10**9, 3
    for c in range(COLS):
        r = get_open_row(board, c)
        if r == -1:
            continue
        board[r][c] = ai_player
        val = minimax(board, 5, -10**9, 10**9, False, ai_player)
        board[r][c] = None
        if val > best_val:
            best_val, best_col = val, c
    return best_col


# ── Main game window ─────────────────────────────────────────────────────────
class Connect4(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Connect 4")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.board       = [[None] * COLS for _ in range(ROWS)]
        self.current     = "red"
        self.game_over   = False
        self.vs_ai       = False
        self.scores      = {"red": 0, "yellow": 0, "draw": 0}
        self.win_cells   = []
        self.flash_on    = False
        self._flash_job  = None
        self.hover_col   = None

        self._build_ui()
        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<Button-1>", self._on_click)

    # ── UI construction ──────────────────────────────────────────
    def _build_ui(self):
        big   = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        med   = tkfont.Font(family="Segoe UI", size=12)
        small = tkfont.Font(family="Segoe UI", size=10)

        # Title
        tk.Label(self, text="CONNECT 4", bg=BG, fg="#f0c040",
                 font=big).pack(pady=(18, 4))

        # Score bar
        score_frame = tk.Frame(self, bg=BG)
        score_frame.pack(pady=(0, 8))

        self.lbl_p1 = tk.Label(score_frame, text="Player 1", bg=BG,
                                fg=RED, font=small)
        self.lbl_p1.grid(row=0, column=0, padx=20)
        tk.Label(score_frame, text="Draws", bg=BG, fg=GREY,
                 font=small).grid(row=0, column=1, padx=20)
        self.lbl_p2 = tk.Label(score_frame, text="Player 2", bg=BG,
                                fg=YELLOW, font=small)
        self.lbl_p2.grid(row=0, column=2, padx=20)

        self.score_red  = tk.Label(score_frame, text="0", bg=BG,
                                    fg=RED,    font=big)
        self.score_red.grid(row=1, column=0, padx=20)
        self.score_draw = tk.Label(score_frame, text="0", bg=BG,
                                    fg=GREY,   font=big)
        self.score_draw.grid(row=1, column=1, padx=20)
        self.score_yel  = tk.Label(score_frame, text="0", bg=BG,
                                    fg=YELLOW, font=big)
        self.score_yel.grid(row=1, column=2, padx=20)

        # Status
        self.status_var = tk.StringVar(value="Red's turn")
        self.status_lbl = tk.Label(self, textvariable=self.status_var,
                                    bg=BG, fg=RED, font=med)
        self.status_lbl.pack(pady=(0, 8))

        # Canvas
        self.canvas = tk.Canvas(self, width=WIDTH, height=HEIGHT,
                                 bg=BOARD, highlightthickness=0)
        self.canvas.pack(padx=20)

        # Buttons
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=14)

        tk.Button(btn_frame, text="New Game", command=self._new_game,
                  bg="#f0c040", fg=BG, font=med, padx=16, pady=6,
                  relief="flat", cursor="hand2").grid(row=0, column=0, padx=8)

        self.mode_btn = tk.Button(btn_frame, text="vs CPU",
                                   command=self._toggle_mode,
                                   bg="#26a69a", fg="white", font=med,
                                   padx=16, pady=6, relief="flat",
                                   cursor="hand2")
        self.mode_btn.grid(row=0, column=1, padx=8)

        self._draw_board()

    # ── Drawing ──────────────────────────────────────────────────
    def _cell_xy(self, row, col):
        x = PAD + col * (CELL + PAD) + CELL // 2
        y = PAD + row * (CELL + PAD) + CELL // 2
        return x, y

    def _draw_board(self):
        self.canvas.delete("all")
        for r in range(ROWS):
            for c in range(COLS):
                self._draw_cell(r, c)

    def _draw_cell(self, r, c, flash=False):
        x, y = self._cell_xy(r, c)
        r0, r1 = x - CELL // 2 + 4, x + CELL // 2 - 4
        t0, t1 = y - CELL // 2 + 4, y + CELL // 2 - 4

        val = self.board[r][c]

        if val is None:
            # Show ghost piece when hovering
            if (not self.game_over and self.hover_col == c
                    and get_open_row(self.board, c) == r):
                ghost = RED_HL if self.current == "red" else YEL_HL
                self.canvas.create_oval(r0, t0, r1, t1,
                                         fill=ghost, outline="", stipple="gray50")
            else:
                self.canvas.create_oval(r0, t0, r1, t1,
                                         fill=EMPTY, outline="")
        elif val == "red":
            colour = RED_HL if flash else RED
            self.canvas.create_oval(r0, t0, r1, t1,
                                     fill=colour, outline="")
        else:
            colour = YEL_HL if flash else YELLOW
            self.canvas.create_oval(r0, t0, r1, t1,
                                     fill=colour, outline="")

    def _redraw_win_cells(self):
        if not self.win_cells:
            return
        self.flash_on = not self.flash_on
        for wr, wc in self.win_cells:
            self._draw_cell(wr, wc, flash=self.flash_on)
        self._flash_job = self.after(500, self._redraw_win_cells)

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
        widget = event.widget
        # translate to canvas coords
        try:
            cx = self.canvas.winfo_rootx()
            cy = self.canvas.winfo_rooty()
            rx = event.x_root - cx
            ry = event.y_root - cy
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
            self._set_status(f"{name} wins! 🎉", self.current)
            self.game_over = True
            self._redraw_win_cells()
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
        # Run minimax in a thread so the UI doesn't freeze
        def run():
            col = best_move(self.board, "yellow")
            self.after(0, lambda: self._drop(col))
        threading.Thread(target=run, daemon=True).start()

    # ── Helpers ──────────────────────────────────────────────────
    def _set_status(self, text, player):
        self.status_var.set(text)
        if player == "red":
            self.status_lbl.config(fg=RED)
        elif player == "yellow":
            self.status_lbl.config(fg=YELLOW)
        else:
            self.status_lbl.config(fg=WHITE)

    def _update_scores(self):
        self.score_red.config( text=str(self.scores["red"]))
        self.score_yel.config( text=str(self.scores["yellow"]))
        self.score_draw.config(text=str(self.scores["draw"]))

    def _new_game(self):
        if self._flash_job:
            self.after_cancel(self._flash_job)
            self._flash_job = None
        self.board     = [[None] * COLS for _ in range(ROWS)]
        self.current   = "red"
        self.game_over = False
        self.win_cells = []
        self.flash_on  = False
        self.hover_col = None
        self._draw_board()
        self._set_status("Red's turn", "red")

    def _toggle_mode(self):
        self.vs_ai = not self.vs_ai
        self.mode_btn.config(text="vs Human" if self.vs_ai else "vs CPU")
        self.lbl_p2.config(text="CPU" if self.vs_ai else "Player 2")
        self.scores = {"red": 0, "yellow": 0, "draw": 0}
        self._update_scores()
        self._new_game()


if __name__ == "__main__":
    app = Connect4()
    app.mainloop()
