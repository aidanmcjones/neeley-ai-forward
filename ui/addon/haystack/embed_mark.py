import re, json, urllib.parse
H='/private/tmp/claude-501/-Users-aidanjones/65520c57-4dc1-4183-a831-845e1b7c0d6e/scratchpad/hay'
W='/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/ui/ui/addon/haystack'
full=open(f'{H}/mark.svg').read().strip(); lite=open(f'{H}/mark_lite.svg').read().strip()
def inner(s): return re.sub(r'</svg>$','',re.sub(r'^<svg[^>]*>','',s))
def rid(s,x): return s.replace('id="hay-g"','id="hay-g%s"'%x).replace('url(#hay-g)','url(#hay-g%s)'%x).replace('id="hay-s"','id="hay-s%s"'%x).replace('url(#hay-s)','url(#hay-s%s)'%x)
strip=lambda s: re.sub(r'\s+class="hay-(sheen|glint2?|body)"','',s)
fav='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#4D1979"/><g transform="translate(5 4) scale(.84)">'+strip(rid(inner(lite),'f')).replace('var(--hay-ink,#3C145F)','#2A0E45')+'</g></svg>'
hero='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'+strip(rid(inner(lite),'h')).replace('var(--hay-ink,#3C145F)','#7A4BB5')+'</svg>'
q=lambda s:'data:image/svg+xml,'+urllib.parse.quote(re.sub(r'\n\s*','',s),safe="/:=' ,.()")   # '#' must be %23 in a data URI
fav_uri,hero_uri=q(fav),q(hero)
assert '#' not in fav_uri and '#' not in hero_uri
js=open(f'{W}/haystack.js').read()
js=re.sub(r'var MARK =[\s\S]*?"</svg>";', lambda m:'var MARK = '+json.dumps(full)+';', js, count=1)
js=re.sub(r'var ICON =\s*(?:"data:[^\n]*";|[\s\S]*?\n    \);)', lambda m:'var ICON = '+json.dumps(fav_uri)+';', js, count=1)
assert js.count('var MARK =')==1 and js.count('var ICON =')==1
open(f'{W}/haystack.js','w').write(js)
css=open(f'{W}/haystack.css').read()
m=re.search(r'(button\[data-hero\] > span:first-child::before \{\n  content: "";\n  width: )\d+px;\n  height: \d+px;\n  background: url\("[^"]*"\)',css); assert m
css=css[:m.start()]+m.group(1)+'16px;\n  height: 16px;\n  background: url("'+hero_uri+'")'+css[m.end():]
open(f'{W}/haystack.css','w').write(css)
p='/private/tmp/claude-501/-Users-aidanjones/65520c57-4dc1-4183-a831-845e1b7c0d6e/scratchpad/parker_site/index.html'
s=open(p).read(); s=re.sub(r'<link rel="icon" href="[^"]*" />',lambda m:'<link rel="icon" href="'+fav_uri+'" />',s); open(p,'w').write(s)
open(f'{H}/favicon.svg','w').write(fav)
open(f'{H}/hero_test.html','w').write('<!doctype html><meta charset=utf-8><style>body{background:#eee;padding:20px}i{display:inline-block;width:64px;height:64px;background:url("%s") center/contain no-repeat}</style><i></i><img src="%s" width=16><img src="%s" width=32>'%(hero_uri,hero_uri,fav_uri))
print('js',len(js),'css',len(css),'fav',len(fav_uri),'hero',len(hero_uri),'index',len(s))
