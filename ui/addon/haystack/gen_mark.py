import math, random, sys, os
random.seed(int(sys.argv[1]) if len(sys.argv)>1 else 11)
CX, APEX, BASE, RX = 32, 5, 58, 25
def rim(t):                       # outline point for t in [0,1], base-left over the apex to base-right
    a = math.pi*(1-t); s = math.sin(a)
    return CX + RX*math.cos(a) + 1.5*math.sin(3*a), BASE - (BASE-APEX)*(s**0.5)
def inside(x,y):
    if y>BASE or y<APEX: return False
    # horizontal half-width at this height, from the bell: s^0.6 = (BASE-y)/(BASE-APEX)
    s = ((BASE-y)/(BASE-APEX))**(1/0.5)
    if s>1: return False
    hw = RX*math.sqrt(max(0,1-s*s))
    return abs(x-CX) <= hw
pts=[rim(i/100) for i in range(101)]
sil="M%.1f %.1f "%pts[0]+" ".join("L%.1f %.1f"%p for p in pts[1:])+" C50 60.5 14 60.5 %.1f %.1f Z"%pts[0]
tones=["#F6DB80","#EBC45C","#DBAE45","#C8962F","#B07E24","#F9E6A0"]
def straw(x,y,ang,ln,w,c,o,curve=True):
    ex,ey = x+math.cos(ang)*ln, y+math.sin(ang)*ln
    if curve:
        n = ang+math.pi/2; b=random.uniform(-1.6,1.6)
        cx,cy = (x+ex)/2+math.cos(n)*b, (y+ey)/2+math.sin(n)*b
        d="M%.1f %.1fQ%.1f %.1f %.1f %.1f"%(x,y,cx,cy,ex,ey)
    else: d="M%.1f %.1f %.1f %.1f"%(x,y,ex,ey)
    return f'<path d="{d}" stroke="{c}" stroke-width="{w:.2f}" stroke-linecap="round" opacity="{o:.2f}"/>'
body=[]
# dense body straws, lying along the slope (radial from a point above the apex), lighter top-left, darker bottom-right
for i in range(int(os.environ.get("BODY",170))):
    while True:
        x=random.uniform(4,62); y=random.uniform(APEX-1,BASE)
        if inside(x,y): break
    ang = math.atan2(y-(APEX-10), x-CX) + random.uniform(-0.5,0.5)
    ln = random.uniform(5,12); w=random.uniform(0.9,1.6)
    light = (x-CX)*-0.012 + (BASE-y)/(BASE-APEX)*0.8 + random.uniform(-0.3,0.3)
    c = "#F9E6A0" if light>0.95 else "#F6DB80" if light>0.7 else "#DBAE45" if light>0.4 else "#B07E24" if light>0.15 else "#8F6118"
    body.append(straw(x,y,ang,ln,w,c,random.uniform(0.75,1)))
# rim straws: start just inside the edge and poke outward, irregular angles and lengths, denser on the top half
edge=[]
for i in range(int(os.environ.get("EDGE",70))):
    t=random.random()
    if random.random()<0.5 and not (0.2<t<0.8): continue
    x,y=rim(t); a=math.pi*(1-t)
    nx,ny=math.cos(a),-math.sin(a)**0.5; L=math.hypot(nx,ny); nx/=L; ny/=L
    j=random.uniform(-0.9,0.9); dx,dy=nx*math.cos(j)-ny*math.sin(j), nx*math.sin(j)+ny*math.cos(j)
    ln=random.uniform(2.5,6.5); back=random.uniform(2,5)
    c=random.choice(["#EBC45C","#DBAE45","#C8962F","#F6DB80"])
    edge.append(straw(x-dx*back,y-dy*back,math.atan2(dy,dx),ln+back,random.uniform(0.9,1.4),c,random.uniform(0.85,1),False))
# loose straws at the foot
foot="".join(straw(x,BASE-0.5,a,ln,1.2,c,1,False) for x,a,ln,c in [(8,2.9,6,"#DBAE45"),(12,2.6,5,"#C8962F"),(16,3.3,4,"#EBC45C"),(50,0.3,5,"#DBAE45"),(55,-0.2,6,"#C8962F"),(46,0.6,4,"#EBC45C"),(30,0.1,5,"#B07E24")])
svg=f'''<svg class="hay-mark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
<defs>
<radialGradient id="hay-g" cx="38%" cy="28%" r="80%"><stop offset="0" stop-color="#F2CF6B"/><stop offset=".55" stop-color="#D9AC43"/><stop offset="1" stop-color="#A4741F"/></radialGradient>
<linearGradient id="hay-s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".5" stop-color="#C9D2DD"/><stop offset="1" stop-color="#7F8B9C"/></linearGradient>
</defs>
<g class="hay-body">
<ellipse cx="33" cy="58" rx="29" ry="2.4" fill="#6B4410" opacity=".35"/>
{foot}{"".join(edge)}
<path d="{sil}" fill="url(#hay-g)"/>
{"".join(body)}
</g>
<path d="M29.5 36.5 57 7 34.3 41.1A3 3 0 0 1 29.5 36.5Z" fill="url(#hay-s)" stroke="var(--hay-ink,#3C145F)" stroke-width="1.5" stroke-linejoin="round"/>
<ellipse cx="34.6" cy="35.6" rx="1" ry="2.6" transform="rotate(42 35.4 36)" fill="var(--hay-ink,#3C145F)"/>
<path class="hay-sheen" d="M37 32 54 12" stroke="#fff" stroke-width="1.5" stroke-linecap="round" opacity=".95"/>
<path d="M27 41Q33 38 38 43M29 47Q34 42 39 46M30 35Q33 40 34 45" fill="none" stroke="#B07E24" stroke-width="1.3" stroke-linecap="round"/>
<path class="hay-glint" d="M57 0 58.9 5.6 64.5 7.5 58.9 9.4 57 15 55.1 9.4 49.5 7.5 55.1 5.6Z" fill="#fff" stroke="var(--hay-ink,#3C145F)" stroke-width="1.1" stroke-linejoin="round"/>
<path class="hay-glint2" d="M48 14 48.7 15.8 50.5 16.5 48.7 17.2 48 19 47.3 17.2 45.5 16.5 47.3 15.8Z" fill="#fff" stroke="var(--hay-ink,#3C145F)" stroke-width=".8" stroke-linejoin="round"/>
</svg>'''
open(os.environ.get('OUT','mark.svg'),'w').write(svg)
css='''svg.hay-mark{overflow:visible;filter:drop-shadow(1px 0 0 var(--hay-ink)) drop-shadow(-1px 0 0 var(--hay-ink)) drop-shadow(0 1px 0 var(--hay-ink)) drop-shadow(0 -1px 0 var(--hay-ink)) drop-shadow(0 4px 0 var(--hay-ink))}'''
html=f'''<!doctype html><meta charset=utf-8><style>body{{margin:0;display:grid;grid-template-columns:1fr 1fr;font:16px system-ui}}
div{{padding:24px;display:flex;gap:28px;align-items:center}}.l{{background:#F7F5FA;--hay-ink:rgb(60 20 95)}}.d{{background:#140F1E;--hay-ink:rgb(120 70 180)}}
.big{{width:300px;height:300px}}.mid{{width:120px;height:120px}}.sm{{width:57px;height:57px}}{css}</style>
<div class=l>{svg.replace('class="hay-mark"','class="hay-mark big"')}{svg.replace('class="hay-mark"','class="hay-mark mid"')}{svg.replace('class="hay-mark"','class="hay-mark sm"')}</div>
<div class=d>{svg.replace('class="hay-mark"','class="hay-mark big"')}{svg.replace('class="hay-mark"','class="hay-mark mid"')}{svg.replace('class="hay-mark"','class="hay-mark sm"')}</div>'''
open('preview.html','w').write(html); open('mark.css','w').write(css); print(len(svg))
