# tiny-chess-01 engine (MIT, see LICENSE) - Stage (a): 0x88 move generator
import json
import os
import sys
import time
import urllib.error
import urllib.request

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")

PIECES = {'P':1, 'N':2, 'B':3, 'R':4, 'Q':5, 'K':6,
          'p':9, 'n':10, 'b':11, 'r':12, 'q':13, 'k':14}
VALUE = {"p": 1, "n": 3, "b": 3, "r": 5, "q": 9, "k": 100}

def sq_name(sq):
    return chr(97 + (sq & 7)) + str(8 - (sq >> 4))

def name_sq(name):
    return (8 - int(name[1])) * 16 + (ord(name[0]) - 97)

class Board:
    def __init__(self, fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"):
        self.b = [0] * 128
        parts = fen.split()
        rows = parts[0].split('/')
        for r, row in enumerate(rows):
            c = 0
            for char in row:
                if char.isdigit():
                    c += int(char)
                else:
                    self.b[(r << 4) + c] = PIECES[char]
                    c += 1
        self.turn = 0 if parts[1] == 'w' else 8
        self.castling = 0
        if len(parts) > 2 and parts[2] != '-':
            if 'K' in parts[2]: self.castling |= 1
            if 'Q' in parts[2]: self.castling |= 2
            if 'k' in parts[2]: self.castling |= 4
            if 'q' in parts[2]: self.castling |= 8
        self.ep = name_sq(parts[3]) if len(parts) > 3 and parts[3] != '-' else -1
        self.halfmove = int(parts[4]) if len(parts) > 4 else 0
        self.fullmove = int(parts[5]) if len(parts) > 5 else 1

    def attacked(self, sq, by_col):
        p_dirs = (17, 15) if by_col == 0 else (-17, -15)
        pawn_piece = 1 | by_col
        for d in p_dirs:
            t = sq + d
            if (t & 0x88) == 0 and self.b[t] == pawn_piece:
                return True

        n_piece = 2 | by_col
        for d in (-18, -33, -31, -14, 14, 31, 33, 18):
            t = sq + d
            if (t & 0x88) == 0 and self.b[t] == n_piece:
                return True

        k_piece = 6 | by_col
        for d in (-17, -16, -15, -1, 1, 15, 16, 17):
            t = sq + d
            if (t & 0x88) == 0 and self.b[t] == k_piece:
                return True

        bq = (3 | by_col, 5 | by_col)
        for d in (-17, -15, 15, 17):
            t = sq + d
            while (t & 0x88) == 0:
                p = self.b[t]
                if p:
                    if p in bq: return True
                    break
                t += d

        rq = (4 | by_col, 5 | by_col)
        for d in (-1, -16, 16, 1):
            t = sq + d
            while (t & 0x88) == 0:
                p = self.b[t]
                if p:
                    if p in rq: return True
                    break
                t += d
        return False

    def find_king(self, col):
        k = 6 | col
        for i in range(128):
            if (i & 0x88) == 0 and self.b[i] == k:
                return i
        return -1

    def generate_moves(self):
        moves = []
        us = self.turn
        them = 8 - us
        forward = -16 if us == 0 else 16
        start_row = 6 if us == 0 else 1
        promo_row = 0 if us == 0 else 7
        cap_dirs = (-17, -15) if us == 0 else (15, 17)

        for sq in range(128):
            if sq & 0x88: continue
            p = self.b[sq]
            if not p or (p & 8) != us: continue

            pt = p & 7
            if pt == 1: # Pawn
                t = sq + forward
                if (t & 0x88) == 0 and not self.b[t]:
                    if (t >> 4) == promo_row:
                        for promo in (5, 4, 3, 2):
                            moves.append((sq, t, promo))
                    else:
                        moves.append((sq, t, 0))
                        if (sq >> 4) == start_row:
                            t2 = t + forward
                            if (t2 & 0x88) == 0 and not self.b[t2]:
                                moves.append((sq, t2, 0))
                for d in cap_dirs:
                    t = sq + d
                    if (t & 0x88) == 0:
                        target = self.b[t]
                        if (target and (target & 8) == them) or t == self.ep:
                            if (t >> 4) == promo_row:
                                for promo in (5, 4, 3, 2):
                                    moves.append((sq, t, promo))
                            else:
                                moves.append((sq, t, 0))
            elif pt in (2, 6): # Knight or King
                offsets = (-18, -33, -31, -14, 14, 31, 33, 18) if pt == 2 else (-17, -16, -15, -1, 1, 15, 16, 17)
                for d in offsets:
                    t = sq + d
                    if (t & 0x88) == 0:
                        target = self.b[t]
                        if not target or (target & 8) == them:
                            moves.append((sq, t, 0))
                if pt == 6:
                    if us == 0:
                        if (self.castling & 1) and self.b[117] == 0 and self.b[118] == 0:
                            if not self.attacked(116, 8) and not self.attacked(117, 8) and not self.attacked(118, 8):
                                moves.append((116, 118, 0))
                        if (self.castling & 2) and self.b[115] == 0 and self.b[114] == 0 and self.b[113] == 0:
                            if not self.attacked(116, 8) and not self.attacked(115, 8) and not self.attacked(114, 8):
                                moves.append((116, 114, 0))
                    else:
                        if (self.castling & 4) and self.b[5] == 0 and self.b[6] == 0:
                            if not self.attacked(4, 0) and not self.attacked(5, 0) and not self.attacked(6, 0):
                                moves.append((4, 6, 0))
                        if (self.castling & 8) and self.b[3] == 0 and self.b[2] == 0 and self.b[1] == 0:
                            if not self.attacked(4, 0) and not self.attacked(3, 0) and not self.attacked(2, 0):
                                moves.append((4, 2, 0))
            else: # Sliders (B, R, Q)
                b_dirs = (-17, -15, 15, 17) if pt in (3, 5) else ()
                r_dirs = (-1, -16, 16, 1) if pt in (4, 5) else ()
                for d in b_dirs + r_dirs:
                    t = sq + d
                    while (t & 0x88) == 0:
                        target = self.b[t]
                        if not target:
                            moves.append((sq, t, 0))
                        else:
                            if (target & 8) == them:
                                moves.append((sq, t, 0))
                            break
                        t += d
        return moves

    def make_move(self, move):
        fr, to, promo = move
        p = self.b[fr]
        target = self.b[to]
        us = self.turn
        them = 8 - us
        undo = (p, target, self.castling, self.ep, self.halfmove, fr, to, promo)
        
        if (p & 7) == 1 or target != 0:
            self.halfmove = 0
        else:
            self.halfmove += 1
            
        ep_captured_sq = -1
        if (p & 7) == 1 and to == self.ep:
            ep_captured_sq = to + (16 if us == 0 else -16)
            target = self.b[ep_captured_sq]
            self.b[ep_captured_sq] = 0

        if (p & 7) == 6:
            if fr == 116 and to == 118:
                self.b[117] = self.b[119]; self.b[119] = 0
            elif fr == 116 and to == 114:
                self.b[115] = self.b[112]; self.b[112] = 0
            elif fr == 4 and to == 6:
                self.b[5] = self.b[7]; self.b[7] = 0
            elif fr == 4 and to == 2:
                self.b[3] = self.b[0]; self.b[0] = 0

        cm = 15
        if fr == 116 or to == 116: cm &= ~3
        if fr == 119 or to == 119: cm &= ~1
        if fr == 112 or to == 112: cm &= ~2
        if fr == 4 or to == 4: cm &= ~12
        if fr == 7 or to == 7: cm &= ~4
        if fr == 0 or to == 0: cm &= ~8
        self.castling &= cm

        self.ep = -1
        if (p & 7) == 1 and abs(to - fr) == 32:
            self.ep = fr + (-16 if us == 0 else 16)

        self.b[to] = (us | promo) if promo else p
        self.b[fr] = 0
        self.turn = them
        if us == 8: self.fullmove += 1
        return undo

    def unmake_move(self, move, undo):
        p, target, castling, ep, halfmove, fr, to, promo = undo
        us = 8 - self.turn
        them = 8 - us
        self.turn = us
        self.castling = castling
        self.ep = ep
        self.halfmove = halfmove
        if us == 8: self.fullmove -= 1

        self.b[fr] = p
        self.b[to] = 0

        if (p & 7) == 1 and to == ep:
            ep_captured_sq = to + (16 if us == 0 else -16)
            self.b[ep_captured_sq] = 9 if us == 0 else 1
        else:
            self.b[to] = target

        if (p & 7) == 6:
            if fr == 116 and to == 118:
                self.b[119] = self.b[117]; self.b[117] = 0
            elif fr == 116 and to == 114:
                self.b[112] = self.b[115]; self.b[115] = 0
            elif fr == 4 and to == 6:
                self.b[7] = self.b[5]; self.b[5] = 0
            elif fr == 4 and to == 2:
                self.b[0] = self.b[3]; self.b[3] = 0

    def legal_moves(self):
        legals = []
        us = self.turn
        for m in self.generate_moves():
            undo = self.make_move(m)
            king_sq = self.find_king(us)
            if king_sq != -1 and not self.attacked(king_sq, 8 - us):
                legals.append(m)
            self.unmake_move(m, undo)
        return legals

def to_uci(move):
    fr, to, promo = move
    s = sq_name(fr) + sq_name(to)
    if promo:
        s += {2:'n', 3:'b', 4:'r', 5:'q'}[promo]
    return s

def from_uci(uci):
    fr = name_sq(uci[:2])
    to = name_sq(uci[2:4])
    promo = 0
    if len(uci) == 5:
        promo = {'n':2, 'b':3, 'r':4, 'q':5}[uci[4]]
    return (fr, to, promo)

def perft(board, depth):
    if depth == 0:
        return 1
    nodes = 0
    for m in board.legal_moves():
        undo = board.make_move(m)
        nodes += perft(board, depth - 1)
        board.unmake_move(m, undo)
    return nodes

def post(path, body):
    req = urllib.request.Request(
        ENV_URL + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")

MAT = [0, 100, 320, 330, 500, 900, 0]

PST_P = (
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
)
PST_N = (
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
)
PST_B = (
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
)
PST_R = (
      0,  0,  0,  0,  0,  0,  0,  0,
      5, 10, 10, 10, 10, 10, 10,  5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
      0,  0,  0,  5,  5,  0,  0,  0,
)
PST_Q = (
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
)
PST_K = (
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
)

PSTS = ((), PST_P, PST_N, PST_B, PST_R, PST_Q, PST_K)

def eval_board(board):
    w = 0
    b = 0
    for r in range(8):
        base = r << 4
        for c in range(8):
            p = board.b[base + c]
            if not p: continue
            pt = p & 7
            us = p & 8
            idx = (r << 3) + c if us == 0 else ((7 - r) << 3) + c
            val = MAT[pt] + PSTS[pt][idx]
            if us == 0: w += val
            else: b += val
    return (w - b) if board.turn == 0 else (b - w)

def move_score(board, m):
    fr, to, promo = m
    p = board.b[fr]
    pt = p & 7
    target = board.b[to]
    victim = target & 7 if target else (1 if pt == 1 and (fr & 7) != (to & 7) else 0)
    score = 0
    if victim:
        score = 10000 + 10 * MAT[victim] - MAT[pt] // 10
    elif promo:
        score = 5000 + MAT[promo]
    return score

NODES = 0
START_TIME = 0.0

class SearchStop(Exception): pass

def search(board, depth, alpha, beta, ply):
    global NODES
    NODES += 1
    if (NODES & 2047) == 0:
        if NODES >= 600000 or (time.monotonic() - START_TIME > 9.0):
            raise SearchStop()

    if depth <= 0:
        return eval_board(board)
    if board.halfmove >= 100:
        return 0

    moves = board.legal_moves()
    if not moves:
        us = board.turn
        king_sq = board.find_king(us)
        if king_sq != -1 and board.attacked(king_sq, 8 - us):
            return -100000 + ply
        return 0

    moves.sort(key=lambda m: move_score(board, m), reverse=True)

    best_val = -200000
    for m in moves:
        undo = board.make_move(m)
        val = -search(board, depth - 1, -beta, -alpha, ply + 1)
        board.unmake_move(m, undo)
        if val > best_val:
            best_val = val
        if val > alpha:
            alpha = val
        if alpha >= beta:
            break
    return best_val

def choose(fen, legal):
    global NODES, START_TIME
    board = Board(fen)
    legals = board.legal_moves()
    if not legals:
        return legal[0] if legal else None
    if len(legals) == 1:
        return to_uci(legals[0])

    uci_legals = [to_uci(m) for m in legals]
    valid_legal = [m for m in legal if m in uci_legals]
    if not valid_legal:
        valid_legal = legal

    NODES = 0
    START_TIME = time.monotonic()
    node_budget = 600000
    time_limit = 9.0

    best_move = legals[0]
    best_score = -200000

    depth = 1
    while NODES < node_budget:
        if time.monotonic() - START_TIME > time_limit:
            break

        alpha = -200000
        beta = 200000

        scored_moves = [(m, move_score(board, m)) for m in legals]
        scored_moves.sort(key=lambda x: x[1], reverse=True)
        ordered_moves = [m for m, s in scored_moves]

        local_best_move = ordered_moves[0]
        local_best_score = -200000

        iteration_completed = True
        try:
            for m in ordered_moves:
                undo = board.make_move(m)
                val = -search(board, depth - 1, -beta, -alpha, 1)
                board.unmake_move(m, undo)

                if val > local_best_score:
                    local_best_score = val
                    local_best_move = m
                if val > alpha:
                    alpha = val
        except SearchStop:
            iteration_completed = False

        if not iteration_completed or NODES >= node_budget:
            break

        best_move = local_best_move
        best_score = local_best_score

        if abs(best_score) > 90000:
            break

        depth += 1

    chosen_uci = to_uci(best_move)
    if chosen_uci in legal:
        return chosen_uci
    if valid_legal:
        return valid_legal[0]
    return legal[0] if legal else None

if __name__ == "__main__":
    while True:
        g = post("/game", {})
        if g["status"] == "done":
            break
        while g["status"] == "your_move":
            g = post("/move", {"game": g["game"], "move": choose(g["fen"], g["legal_moves"])})
        print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
    print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)
