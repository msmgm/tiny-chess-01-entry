# tiny-chess-01 engine (MIT, see LICENSE) - Stage (a): 0x88 move generator
import json
import os
import sys
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

def choose(fen, legal):
    board = Board(fen)
    legals = board.legal_moves()
    uci_legals = [to_uci(m) for m in legals]
    board_dict = {}
    for i, row in enumerate(fen.split()[0].split("/")):
        file = 0
        for c in row:
            if c.isdigit(): file += int(c)
            else:
                board_dict["abcdefgh"[file] + str(8 - i)] = c
                file += 1

    def rank(move):
        mover = board_dict[move[:2]].lower()
        victim = board_dict.get(move[2:4])
        if victim is None and mover == "p" and move[0] != move[2]:
            victim = "p"
        taken = VALUE[victim.lower()] if victim else 0
        promo = VALUE[move[4]] if len(move) == 5 else 0
        return (-taken, -promo, VALUE[mover], move)

    valid_legal = [m for m in legal if m in uci_legals]
    if not valid_legal:
        valid_legal = legal
    return min(valid_legal, key=rank) if valid_legal else legal[0]

if __name__ == "__main__":
    while True:
        g = post("/game", {})
        if g["status"] == "done":
            break
        while g["status"] == "your_move":
            g = post("/move", {"game": g["game"], "move": choose(g["fen"], g["legal_moves"])})
        print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
    print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)
