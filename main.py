# tiny-chess-01 0x88 movegen rewrite
import sys
b=[0]*128;t=0;c=0;e=-1;h=0;U=[]
P={'P':1,'N':2,'B':3,'R':4,'Q':5,'K':6,'p':9,'n':10,'b':11,'r':12,'q':13,'k':14}
def setup(fen):
    global b,t,c,e,h
    b=[0]*128;U.clear()
    p=fen.split()
    for r,row in enumerate(p[0].split('/')):
        col=0
        for ch in row:
            if ch.isdigit(): col+=int(ch)
            else: b[(r<<4)+col]=P[ch]; col+=1
    t=0 if p[1]=='w' else 8
    c=sum(v for ch,v in (('K',1),('Q',2),('k',4),('q',8)) if len(p)>2 and ch in p[2])
    e=((8-int(p[3][1]))<<4)+(ord(p[3][0])-97) if len(p)>3 and p[3]!='-' else -1
    h=int(p[4]) if len(p)>4 else 0
def sq(s):return chr(97+(s&7))+str(8-(s>>4))
def to_uci(m):
    fr=m&127;to=(m>>7)&127;pr=(m>>14)&7
    return sq(fr)+sq(to)+({2:'n',3:'b',4:'r',5:'q'}.get(pr,''))
def from_uci(s):
    fr=((8-int(s[1]))<<4)+(ord(s[0])-97);to=((8-int(s[3]))<<4)+(ord(s[2])-97)
    pr={'n':2,'b':3,'r':4,'q':5}.get(s[4],0) if len(s)>4 else 0
    return fr|(to<<7)|(pr<<14)
def atk(s,by):
    p1=1|by;n2=2|by;k6=6|by
    if any(not((t:=s+d)&0x88)and b[t]==p1 for d in ((17,15)if by==0 else(-17,-15))):return 1
    if any(not((t:=s+d)&0x88)and b[t]==n2 for d in (-18,-33,-31,-14,14,31,33,18)):return 1
    if any(not((t:=s+d)&0x88)and b[t]==k6 for d in (-17,-16,-15,-1,1,15,16,17)):return 1
    bq=(3|by,5|by);rq=(4|by,5|by)
    for d in (-17,-15,15,17):
        t=s+d
        while not(t&0x88):
            p=b[t]
            if p:
                if p in bq:return 1
                break
            t+=d
    for d in (-1,-16,16,1):
        t=s+d
        while not(t&0x88):
            p=b[t]
            if p:
                if p in rq:return 1
                break
            t+=d
    return 0
def gen():
    mvs=[];us=t;them=8-us;fwd=-16 if us==0 else 16;sr=6 if us==0 else 1;pr=0 if us==0 else 7
    cd=(-17,-15) if us==0 else (15,17)
    for sq in range(128):
        if sq&0x88 or not(p:=b[sq]) or (p&8)!=us: continue
        pt=p&7
        if pt==1:
            to=sq+fwd
            if not(to&0x88) and not b[to]:
                if (to>>4)==pr:
                    for promo in (5,4,3,2): mvs.append(sq|(to<<7)|(promo<<14))
                else:
                    mvs.append(sq|(to<<7))
                    to2=to+fwd
                    if (sq>>4)==sr and not(to2&0x88) and not b[to2]: mvs.append(sq|(to2<<7))
            for d in cd:
                to=sq+d
                if not(to&0x88) and (((tgt:=b[to]) and (tgt&8)==them) or to==e):
                    if (to>>4)==pr:
                        for promo in (5,4,3,2): mvs.append(sq|(to<<7)|(promo<<14))
                    else:
                        mvs.append(sq|(to<<7))
        elif pt in (2,6):
            for d in ((-18,-33,-31,-14,14,31,33,18) if pt==2 else (-17,-16,-15,-1,1,15,16,17)):
                if not((to:=sq+d)&0x88) and (not(tgt:=b[to]) or (tgt&8)==them):
                    mvs.append(sq|(to<<7))
            if pt==6:
                if us==0:
                    if (c&1) and not b[117] and not b[118] and not atk(116,8) and not atk(117,8) and not atk(118,8): mvs.append(116|(118<<7))
                    if (c&2) and not b[115] and not b[114] and not b[113] and not atk(116,8) and not atk(115,8) and not atk(114,8): mvs.append(116|(114<<7))
                else:
                    if (c&4) and not b[5] and not b[6] and not atk(4,0) and not atk(5,0) and not atk(6,0): mvs.append(4|(6<<7))
                    if (c&8) and not b[3] and not b[2] and not b[1] and not atk(4,0) and not atk(3,0) and not atk(2,0): mvs.append(4|(2<<7))
        else:
            for d in (((-17,-15,15,17) if pt in (3,5) else())+((-1,-16,16,1) if pt in (4,5) else())):
                to=sq+d
                while not(to&0x88):
                    if not(tgt:=b[to]): mvs.append(sq|(to<<7))
                    else:
                        if (tgt&8)==them: mvs.append(sq|(to<<7))
                        break
                    to+=d
    return mvs
def mk(m):
    global t,c,e,h
    fr=m&127;to=(m>>7)&127;pr=m>>14;p=b[fr];tgt=b[to];us=t;them=8-us;oc=c;oe=e;oh=h
    U.append((p,tgt,oc,oe,oh,fr,to,pr))
    if (p&7)==1 and to==e:
        es=to+(16 if us==0 else -16)
        tgt=b[es];b[es]=0
    if (p&7)==6:
        if fr==116 and to==118: b[117],b[119]=b[119],0
        elif fr==116 and to==114: b[115],b[112]=b[112],0
        elif fr==4 and to==6: b[5],b[7]=b[7],0
        elif fr==4 and to==2: b[3],b[0]=b[0],0
    cm=15
    if fr==116 or to==116: cm&=~3
    if fr==119 or to==119: cm&=~1
    if fr==112 or to==112: cm&=~2
    if fr==4 or to==4: cm&=~12
    if fr==7 or to==7: cm&=~4
    if fr==0 or to==0: cm&=~8
    c&=cm;e=-1
    if (p&7)==1 and abs(to-fr)==32: e=fr+(-16 if us==0 else 16)
    np_=(us|pr) if pr else p
    b[to]=np_;b[fr]=0;t=them;h=0 if (p&7)==1 or tgt else h+1
    return U[-1]
def un():
    global t,c,e,h
    p,tgt,oc,oe,oh,fr,to,pr=U.pop()
    us=8-t;t=us;c=oc;e=oe;h=oh
    np_=b[to];b[fr]=p
    if (p&7)==1 and to==oe:
        es=to+(16 if us==0 else -16)
        b[to]=0;b[es]=9 if us==0 else 1
    else: b[to]=tgt
    if (p&7)==6:
        if fr==116 and to==118: b[119],b[117]=b[117],0
        elif fr==116 and to==114: b[112],b[115]=b[115],0
        elif fr==4 and to==6: b[7],b[5]=b[5],0
        elif fr==4 and to==2: b[0],b[3]=b[3],0
def fk(c):
    for i in range(128):
        if not(i&0x88) and b[i]==(6|c): return i
def legal():
    l=[];us=t;them=8-us
    for m in gen():
        mk(m)
        if not atk(fk(us),them): l.append(m)
        un()
    return l
def perft(d):
    if d==0: return 1
    n=0
    for m in legal():
        mk(m)
        n+=perft(d-1)
        un()
    return n
# RW
