# tiny-chess-01 engine (MIT, see LICENSE) - Stage (a): 0x88 move generator
import json
import os
import sys
import time
import urllib.error
import urllib.request

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")

def splitmix64(state):
    state = (state + 0x9e3779b97f4a7c15) & 0xFFFFFFFFFFFFFFFF
    z = state
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9
    z &= 0xFFFFFFFFFFFFFFFF
    z = (z ^ (z >> 27)) * 0x94d049bb133111eb
    z &= 0xFFFFFFFFFFFFFFFF
    return state, z ^ (z >> 31)

_seed = 1070372
def _next_rand():
    global _seed
    _seed, val = splitmix64(_seed)
    return val

Z_PIECE = [[_next_rand() for _ in range(128)] for _ in range(15)]
Z_TURN = _next_rand()
Z_CASTLING = [_next_rand() for _ in range(16)]
Z_EP = [_next_rand() for _ in range(128)]

PIECES = {'P':1, 'N':2, 'B':3, 'R':4, 'Q':5, 'K':6,
          'p':9, 'n':10, 'b':11, 'r':12, 'q':13, 'k':14}

def sq_name(s):
    return chr(97 + (s & 7)) + str(8 - (s >> 4))

def name_sq(n):
    return (8 - int(n[1])) * 16 + (ord(n[0]) - 97)

class Board:
    def __init__(s, f="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"):
        s.b = [0] * 128
        p = f.split()
        for r, row in enumerate(p[0].split('/')):
            c = 0
            for ch in row:
                if ch.isdigit(): c += int(ch)
                else: s.b[(r << 4) + c] = PIECES[ch]; c += 1
        s.turn = 0 if p[1] == 'w' else 8
        s.castling = sum(val for ch, val in (('K', 1), ('Q', 2), ('k', 4), ('q', 8)) if len(p) > 2 and ch in p[2])
        s.ep = name_sq(p[3]) if len(p) > 3 and p[3] != '-' else -1
        s.halfmove = int(p[4]) if len(p) > 4 else 0
        s.fullmove = int(p[5]) if len(p) > 5 else 1
        s.hash = s.compute_zobrist()

    def compute_zobrist(s):
        h = sum(Z_PIECE[p][q] for q in range(128) if not (q & 0x88) and (p := s.b[q]))
        return h ^ (Z_TURN if s.turn == 8 else 0) ^ Z_CASTLING[s.castling] ^ (Z_EP[s.ep] if s.ep != -1 else 0)

    def attacked(s, sq, c):
        if any(not ((t := sq + d) & 0x88) and s.b[t] == 1 | c for d in ((17, 15) if not c else (-17, -15))): return True
        if any(not ((t := sq + d) & 0x88) and s.b[t] == 2 | c for d in (-18, -33, -31, -14, 14, 31, 33, 18)): return True
        if any(not ((t := sq + d) & 0x88) and s.b[t] == 6 | c for d in (-17, -16, -15, -1, 1, 15, 16, 17)): return True
        bq = (3 | c, 5 | c)
        for d in (-17, -15, 15, 17):
            t = sq + d
            while not (t & 0x88):
                if (p := s.b[t]):
                    if p in bq: return True
                    break
                t += d
        rq = (4 | c, 5 | c)
        for d in (-1, -16, 16, 1):
            t = sq + d
            while not (t & 0x88):
                if (p := s.b[t]):
                    if p in rq: return True
                    break
                t += d
        return False

    def find_king(s, c):
        k = 6 | c
        for i in range(128):
            if not (i & 0x88) and s.b[i] == k: return i
        return -1

    def generate_moves(s):
        mvs = []
        us = s.turn
        them = 8 - us
        fwd = -16 if us == 0 else 16
        sr = 6 if us == 0 else 1
        pr = 0 if us == 0 else 7
        cd = (-17, -15) if us == 0 else (15, 17)
        for sq in range(128):
            if sq & 0x88 or not (p := s.b[sq]) or (p & 8) != us: continue
            pt = p & 7
            if pt == 1:
                t = sq + fwd
                if not (t & 0x88) and not s.b[t]:
                    if (t >> 4) == pr:
                        for promo in (5, 4, 3, 2): mvs.append((sq, t, promo))
                    else:
                        mvs.append((sq, t, 0))
                        t2 = t + fwd
                        if (sq >> 4) == sr and not (t2 & 0x88) and not s.b[t2]: mvs.append((sq, t2, 0))
                for d in cd:
                    t = sq + d
                    if not (t & 0x88) and (((tgt := s.b[t]) and (tgt & 8) == them) or t == s.ep):
                        if (t >> 4) == pr:
                            for promo in (5, 4, 3, 2): mvs.append((sq, t, promo))
                        else:
                            mvs.append((sq, t, 0))
            elif pt in (2, 6):
                for d in ((-18, -33, -31, -14, 14, 31, 33, 18) if pt == 2 else (-17, -16, -15, -1, 1, 15, 16, 17)):
                    if not ((t := sq + d) & 0x88) and (not (tgt := s.b[t]) or (tgt & 8) == them):
                        mvs.append((sq, t, 0))
                if pt == 6:
                    if us == 0:
                        if (s.castling & 1) and not s.b[117] and not s.b[118] and not s.attacked(116, 8) and not s.attacked(117, 8) and not s.attacked(118, 8): mvs.append((116, 118, 0))
                        if (s.castling & 2) and not s.b[115] and not s.b[114] and not s.b[113] and not s.attacked(116, 8) and not s.attacked(115, 8) and not s.attacked(114, 8): mvs.append((116, 114, 0))
                    else:
                        if (s.castling & 4) and not s.b[5] and not s.b[6] and not s.attacked(4, 0) and not s.attacked(5, 0) and not s.attacked(6, 0): mvs.append((4, 6, 0))
                        if (s.castling & 8) and not s.b[3] and not s.b[2] and not s.b[1] and not s.attacked(4, 0) and not s.attacked(3, 0) and not s.attacked(2, 0): mvs.append((4, 2, 0))
            else:
                for d in (((-17, -15, 15, 17) if pt in (3, 5) else ()) + ((-1, -16, 16, 1) if pt in (4, 5) else ())):
                    t = sq + d
                    while not (t & 0x88):
                        if not (tgt := s.b[t]): mvs.append((sq, t, 0))
                        else:
                            if (tgt & 8) == them: mvs.append((sq, t, 0))
                            break
                        t += d
        return mvs

    def make_move(s, m):
        fr, to, promo = m
        p = s.b[fr]
        tgt = s.b[to]
        us = s.turn
        them = 8 - us
        oh = s.hash
        undo = (p, tgt, s.castling, s.ep, s.halfmove, fr, to, promo, oh)
        s.hash ^= Z_PIECE[p][fr]
        if tgt: s.hash ^= Z_PIECE[tgt][to]
        if (p & 7) == 1 and to == s.ep:
            es = to + (16 if us == 0 else -16)
            tgt = s.b[es]
            s.b[es] = 0
            s.hash ^= Z_PIECE[9 | them if us == 0 else 1 | them][es]
        oc = s.castling
        if (p & 7) == 6:
            if fr == 116 and to == 118:
                s.b[117], s.b[119] = s.b[119], 0
                s.hash ^= Z_PIECE[4][119] ^ Z_PIECE[4][117]
            elif fr == 116 and to == 114:
                s.b[115], s.b[112] = s.b[112], 0
                s.hash ^= Z_PIECE[4][112] ^ Z_PIECE[4][115]
            elif fr == 4 and to == 6:
                s.b[5], s.b[7] = s.b[7], 0
                s.hash ^= Z_PIECE[12][7] ^ Z_PIECE[12][5]
            elif fr == 4 and to == 2:
                s.b[3], s.b[0] = s.b[0], 0
                s.hash ^= Z_PIECE[12][0] ^ Z_PIECE[12][3]
        cm = 15
        if fr == 116 or to == 116: cm &= ~3
        if fr == 119 or to == 119: cm &= ~1
        if fr == 112 or to == 112: cm &= ~2
        if fr == 4 or to == 4: cm &= ~12
        if fr == 7 or to == 7: cm &= ~4
        if fr == 0 or to == 0: cm &= ~8
        s.castling &= cm
        s.hash ^= Z_CASTLING[oc] ^ Z_CASTLING[s.castling]
        if s.ep != -1: s.hash ^= Z_EP[s.ep]
        s.ep = -1
        if (p & 7) == 1 and abs(to - fr) == 32:
            s.ep = fr + (-16 if us == 0 else 16)
            s.hash ^= Z_EP[s.ep]
        np_ = (us | promo) if promo else p
        s.b[to] = np_
        s.b[fr] = 0
        s.hash ^= Z_PIECE[np_][to]
        s.turn = them
        s.hash ^= Z_TURN
        s.halfmove = 0 if (p & 7) == 1 or tgt else s.halfmove + 1
        if us == 8: s.fullmove += 1
        return undo

    def unmake_move(s, m, undo):
        p, tgt, castling, ep, halfmove, fr, to, promo, oh = undo
        s.hash = oh
        us = 8 - s.turn
        s.turn = us
        s.castling = castling
        s.ep = ep
        s.halfmove = halfmove
        if us == 8: s.fullmove -= 1
        s.b[fr] = p
        s.b[to] = 0
        if (p & 7) == 1 and to == ep:
            es = to + (16 if us == 0 else -16)
            s.b[es] = 9 if us == 0 else 1
        else: s.b[to] = tgt
        if (p & 7) == 6:
            if fr == 116 and to == 118: s.b[119], s.b[117] = s.b[117], 0
            elif fr == 116 and to == 114: s.b[112], s.b[115] = s.b[115], 0
            elif fr == 4 and to == 6: s.b[7], s.b[5] = s.b[5], 0
            elif fr == 4 and to == 2: s.b[0], s.b[3] = s.b[3], 0

    def legal_moves(s):
        l = []
        us = s.turn
        for m in s.generate_moves():
            u = s.make_move(m)
            if (ks := s.find_king(us)) != -1 and not s.attacked(ks, 8 - us): l.append(m)
            s.unmake_move(m, u)
        return l

def to_uci(m):
    fr, to, pr = m
    s = sq_name(fr) + sq_name(to)
    if pr: s += {2:'n', 3:'b', 4:'r', 5:'q'}[pr]
    return s

def perft(b, d):
    if d == 0: return 1
    n = 0
    for m in b.legal_moves():
        u = b.make_move(m)
        n += perft(b, d - 1)
        b.unmake_move(m, u)
    return n

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
PHASE_WEIGHTS = [0, 0, 1, 1, 2, 4, 0]
PSTS_MG = ((), 
    [b - 128 for b in b'\x80\x80\x80\x80\x80\x80\x80\x80\xb2\xb2\xb2\xb2\xb2\xb2\xb2\xb2\x8a\x8a\x94\x9e\x9e\x94\x8a\x8a\x85\x85\x8a\x99\x99\x8a\x85\x85\x80\x80\x80\x94\x94\x80\x80\x80\x85{v\x80\x80v{\x85\x85\x8a\x8all\x8a\x8a\x85\x80\x80\x80\x80\x80\x80\x80\x80'],
    [b - 128 for b in b'NXbbbbXNXl\x80\x80\x80\x80lXb\x80\x8a\x8f\x8f\x8a\x80bb\x80\x8f\x94\x94\x8f\x80bb\x80\x8f\x94\x94\x8f\x80bb\x80\x8a\x8f\x8f\x8a\x80bXl\x80\x85\x85\x80lXNXbbbbXN'],
    [b - 128 for b in b'lvvvvvvlv\x80\x80\x80\x80\x80\x80vv\x80\x85\x8a\x8a\x85\x80vv\x85\x85\x8a\x8a\x85\x85vv\x80\x8a\x8a\x8a\x8a\x80vv\x8a\x8a\x8a\x8a\x8a\x8avv\x85\x80\x80\x80\x80\x85vlvvvvvvl'],
    [b - 128 for b in b'\x80\x80\x80\x80\x80\x80\x80\x80\x85\x8a\x8a\x8a\x8a\x8a\x8a\x85{\x80\x80\x80\x80\x80\x80{{\x80\x80\x80\x80\x80\x80{{\x80\x80\x80\x80\x80\x80{{\x80\x80\x80\x80\x80\x80{{\x80\x80\x80\x80\x80\x80{\x80\x80\x80\x85\x85\x80\x80\x80'],
    [b - 128 for b in b'lvv{{vvlv\x80\x80\x80\x80\x80\x80vv\x80\x85\x85\x85\x85\x80v{\x80\x85\x85\x85\x85\x80{\x80\x80\x85\x85\x85\x85\x80{v\x85\x85\x85\x85\x85\x80vv\x80\x85\x80\x80\x80\x80vlvv{{vvl'],
    [b - 128 for b in b'bXXNNXXbbXXNNXXbbXXNNXXbbXXNNXXblbbXXbblvllllllv\x94\x94\x80\x80\x80\x80\x94\x94\x94\x9e\x8a\x80\x80\x8a\x9e\x94']
)
PSTS_EG = ((),
    [b - 128 for b in b'\x80\x80\x80\x80\x80\x80\x80\x80\xc5\xc5\xc5\xc5\xc5\xc5\xc5\xc5\xae\xae\xae\xae\xae\xae\xae\xae\x97\x97\x97\x97\x97\x97\x97\x97\x80\x80\x80\x80\x80\x80\x80\x80iiiiiiiiRRRRRRRR\x80\x80\x80\x80\x80\x80\x80\x80'],
    [b - 128 for b in b'v{{{{{{v{\x80\x80\x80\x80\x80\x80{{\x80\x85\x85\x85\x85\x80{{\x80\x85\x8a\x8a\x85\x80{{\x80\x85\x8a\x8a\x85\x80{{\x80\x85\x85\x85\x85\x80{{\x80\x80\x80\x80\x80\x80{v{{{{{{v'],
    [b - 128 for b in b'v{{{{{{v{\x80\x80\x80\x80\x80\x80{{\x80\x85\x85\x85\x85\x80{{\x80\x85\x8a\x8a\x85\x80{{\x80\x85\x8a\x8a\x85\x80{{\x80\x85\x85\x85\x85\x80{{\x80\x80\x80\x80\x80\x80{v{{{{{{v'],
    [b - 128 for b in b'\x80\x80\x80\x80\x80\x80\x80\x80\x82\x84\x84\x84\x84\x84\x84\x82~\x80\x80\x80\x80\x80\x80~~\x80\x80\x80\x80\x80\x80~~\x80\x80\x80\x80\x80\x80~~\x80\x80\x80\x80\x80\x80~~\x80\x80\x80\x80\x80\x80~\x80\x80\x80\x82\x82\x80\x80\x80'],
    [b - 128 for b in b'v{{~~{{v{\x80\x80\x80\x80\x80\x80{{\x80\x83\x83\x83\x83\x80{~\x80\x83\x83\x83\x83\x80~\x80\x80\x83\x83\x83\x83\x80~{\x83\x83\x83\x83\x83\x80{{\x80\x83\x80\x80\x80\x80{v{{~~{{v'],
    [b - 128 for b in b'NXbllbXNblv\x80\x80vlbbv\x94\x9e\x9e\x94vbbv\x9e\xa8\xa8\x9evbbv\x9e\xa8\xa8\x9evbbv\x94\x9e\x9e\x94vbblv\x80\x80vlbNXbllbXN']
)

def eval_board(b):
    w1 = w2 = b1 = b2 = ph = 0
    for r in range(8):
        z = r << 4
        for c in range(8):
            if p := b.b[z + c]:
                pt = p & 7
                us = p & 8
                idx = (r << 3) + c if us == 0 else ((7 - r) << 3) + c
                ph += PHASE_WEIGHTS[pt]
                if us == 0:
                    w1 += MAT[pt] + PSTS_MG[pt][idx]
                    w2 += MAT[pt] + PSTS_EG[pt][idx]
                else:
                    b1 += MAT[pt] + PSTS_MG[pt][idx]
                    b2 += MAT[pt] + PSTS_EG[pt][idx]
    ph = 24 if ph > 24 else ph
    w = (w1 * ph + w2 * (24 - ph)) // 24
    x = (b1 * ph + b2 * (24 - ph)) // 24
    return (w - x) if b.turn == 0 else (x - w)

def move_score(b, m):
    fr, to, pr = m
    p = b.b[fr]
    pt = p & 7
    t = b.b[to]
    v = (t & 7) if t else (1 if pt == 1 and (fr & 7) != (to & 7) else 0)
    return (10000 + 10 * MAT[v] - MAT[pt] // 10) if v else (5000 + MAT[pr] if pr else 0)

NODES = 0
START_TIME = 0.0

TT = {}
EXACT, LOWER, UPPER = 0, 1, 2
KILLERS = [[0, 0] for _ in range(128)]
HISTORY = [[0 for _ in range(128)] for _ in range(15)]

class SearchStop(Exception): pass

def qsearch(b, alpha, beta, ply):
    global NODES
    NODES += 1
    if (NODES & 2047) == 0 and (NODES >= 100000 or time.monotonic() - START_TIME > 5.0):
        raise SearchStop()
    if ply > 64: return eval_board(b)
    us = b.turn
    them = 8 - us
    in_check = b.attacked(b.find_king(us), them)
    mvs = b.generate_moves()
    if not mvs: return (-100000 + ply) if in_check else 0
    sp = eval_board(b)
    if in_check:
        bv = -200000
        lc = 0
        sc = sorted([(move_score(b, m), m) for m in mvs], key=lambda x: x[0], reverse=True)
        for score, m in sc:
            u = b.make_move(m)
            if (ks := b.find_king(us)) != -1 and b.attacked(ks, them):
                b.unmake_move(m, u)
                continue
            lc += 1
            val = -qsearch(b, -beta, -alpha, ply + 1)
            b.unmake_move(m, u)
            if val > bv: bv = val
            if val > alpha:
                alpha = val
                if alpha >= beta: break
        return (-100000 + ply) if lc == 0 else bv
    else:
        if sp >= beta: return beta
        if sp > alpha: alpha = sp
        sc = []
        for m in mvs:
            fr, to, pr = m
            p = b.b[fr]
            tgt = b.b[to]
            if (tgt != 0 or ((p & 7) == 1 and to == b.ep)) or pr != 0:
                if not pr:
                    vic = (tgt & 7) if tgt else (1 if (p & 7) == 1 and to == b.ep else 0)
                    if vic and (sp + MAT[vic] + 200 < alpha): continue
                sc.append((move_score(b, m), m))
        sc.sort(key=lambda x: x[0], reverse=True)
        for score, m in sc:
            u = b.make_move(m)
            if (ks := b.find_king(us)) != -1 and b.attacked(ks, them):
                b.unmake_move(m, u)
                continue
            val = -qsearch(b, -beta, -alpha, ply + 1)
            b.unmake_move(m, u)
            if val > alpha:
                alpha = val
                if alpha >= beta: break
        return alpha

def search(b, depth, alpha, beta, ply):
    global NODES
    NODES += 1
    if (NODES & 2047) == 0 and (NODES >= 100000 or time.monotonic() - START_TIME > 5.0):
        raise SearchStop()
    if b.halfmove >= 100: return 0
    if depth <= 0: return qsearch(b, alpha, beta, ply)
    us = b.turn
    them = 8 - us
    in_check = b.attacked(b.find_king(us), them)
    tt_entry = TT.get(b.hash)
    ttm = None
    if tt_entry:
        td, tv, tf, ttm = tt_entry
        if td >= depth:
            if tv > 90000: tv -= ply
            elif tv < -90000: tv += ply
            if tf == EXACT: return tv
            if tf == LOWER and tv >= beta: return tv
            if tf == UPPER and tv <= alpha: return tv
    if depth >= 3 and not in_check and abs(beta) < 90000:
        if any((p := b.b[sq]) and (p & 8) == us and (p & 7) not in (1, 6) for sq in range(128) if not (sq & 0x88)):
            ot, oe, ohf, oh = b.turn, b.ep, b.halfmove, b.hash
            b.turn, b.ep, b.halfmove, b.hash = them, -1, ohf + 1, oh ^ Z_TURN ^ (Z_EP[oe] if oe != -1 else 0)
            val = -search(b, depth - 3, -beta, -beta + 1, ply + 1)
            b.turn, b.ep, b.halfmove, b.hash = ot, oe, ohf, oh
            if val >= beta: return beta
    mvs = b.generate_moves()
    if not mvs: return (-100000 + ply) if in_check else 0
    k1 = KILLERS[ply][0] if ply < 128 else 0
    k2 = KILLERS[ply][1] if ply < 128 else 0
    sc = []
    for m in mvs:
        fr, to, pr = m
        p = b.b[fr]
        pt = p & 7
        tgt = b.b[to]
        vic = (tgt & 7) if tgt else (1 if pt == 1 and (fr & 7) != (to & 7) else 0)
        score = 1000000 if m == ttm else (200000 + (10 * MAT[vic] - MAT[pt] // 10) if vic else (100000 if m == k1 else (90000 if m == k2 else (10000 + HISTORY[p][to] if not tgt and not pr else 5000))))
        sc.append((score, m))
    sc.sort(key=lambda x: x[0], reverse=True)
    bv = -200000
    bm = None
    fm = True
    lc = 0
    ao = alpha
    for score, m in sc:
        fr, to, pr = m
        p = b.b[fr]
        tgt = b.b[to]
        ic = tgt != 0 or ((p & 7) == 1 and to == b.ep)
        u = b.make_move(m)
        if (ks := b.find_king(us)) != -1 and b.attacked(ks, them):
            b.unmake_move(m, u)
            continue
        lc += 1
        ds = depth - 1
        if not fm and depth >= 3 and lc >= 4 and not in_check and not ic and not pr:
            ds = depth - 2
            val = -search(b, ds, -alpha - 1, -alpha, ply + 1)
            if val > alpha: ds = depth - 1
            else:
                b.unmake_move(m, u)
                if val > bv: bv, bm = val, m
                if val > alpha: alpha = val
                continue
        if fm:
            val = -search(b, ds, -beta, -alpha, ply + 1)
            fm = False
        else:
            val = -search(b, ds, -alpha - 1, -alpha, ply + 1)
            if val > alpha and val < beta:
                val = -search(b, depth - 1, -beta, -alpha, ply + 1)
        b.unmake_move(m, u)
        if val > bv: bv, bm = val, m
        if val > alpha:
            alpha = val
            if alpha >= beta:
                if not ic and not pr:
                    if m != KILLERS[ply][0]:
                        KILLERS[ply][1], KILLERS[ply][0] = KILLERS[ply][0], m
                    HISTORY[p][to] += depth * depth
                break
    if lc == 0: return (-100000 + ply) if in_check else 0
    sv = bv + ply if bv > 90000 else (bv - ply if bv < -90000 else bv)
    TT[b.hash] = (depth, sv, UPPER if bv <= ao else (LOWER if bv >= beta else EXACT), bm)
    return bv

def choose(fen, legal):
    global NODES, START_TIME, TT, KILLERS, HISTORY
    b = Board(fen)
    legals = b.legal_moves()
    if not legals: return legal[0] if legal else None
    if len(legals) == 1: return to_uci(legals[0])
    ul = [to_uci(m) for m in legals]
    vl = [m for m in legal if m in ul] or legal
    NODES = 0
    START_TIME = time.monotonic()
    TT.clear()
    for i in range(128): KILLERS[i] = [0, 0]
    for p in range(15):
        for sq in range(128): HISTORY[p][sq] = 0
    bm = legals[0]
    bs = -200000
    depth = 1
    while NODES < 100000 and time.monotonic() - START_TIME < 5.0:
        alpha, beta = -200000, 200000
        ttm = (tt_entry := TT.get(b.hash)) and tt_entry[3]
        sc = []
        for m in legals:
            fr, to, pr = m
            p = b.b[fr]
            pt = p & 7
            tgt = b.b[to]
            vic = (tgt & 7) if tgt else (1 if pt == 1 and (fr & 7) != (to & 7) else 0)
            score = 1000000 if m == ttm else (200000 + (10 * MAT[vic] - MAT[pt] // 10) if vic else 5000)
            sc.append((score, m))
        sc.sort(key=lambda x: x[0], reverse=True)
        om = [m for _, m in sc]
        lbm, lbs = om[0], -200000
        comp = True
        fm = True
        try:
            for m in om:
                u = b.make_move(m)
                ds = depth - 1
                if fm:
                    val = -search(b, ds, -beta, -alpha, 1)
                    fm = False
                else:
                    val = -search(b, ds, -alpha - 1, -alpha, 1)
                    if val > alpha and val < beta:
                        val = -search(b, depth - 1, -beta, -alpha, 1)
                b.unmake_move(m, u)
                if val > lbs: lbs, lbm = val, m
                if val > alpha: alpha = val
        except SearchStop: comp = False
        if not comp or NODES >= 100000: break
        bm, bs = lbm, lbs
        if abs(bs) > 90000: break
        depth += 1
    cu = to_uci(bm)
    return cu if cu in legal else (vl[0] if vl else (legal[0] if legal else None))

if __name__ == "__main__":
    while True:
        g = post("/game", {})
        if g["status"] == "done": break
        while g["status"] == "your_move":
            g = post("/move", {"game": g["game"], "move": choose(g["fen"], g["legal_moves"])})
        print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
    print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)
