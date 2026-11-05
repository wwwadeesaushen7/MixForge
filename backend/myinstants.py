"""Official anonymous Myinstants API; local caching and bounded public downloads."""
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,quote,urlencode,unquote
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
import json,re,time,threading

HOSTS={'www.myinstants.com','myinstants.com'}
MAX_AUDIO=12*1024*1024
_cache={}; _calls=deque(); _lock=threading.Lock()


def validate_url(url,asset=False):
    try: p=urlsplit(url)
    except ValueError: raise ValueError('Paste a valid HTTPS Myinstants link.')
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in [None,443]:
        raise ValueError('Only public HTTPS links on myinstants.com are supported.')
    path=unquote(p.path)
    if asset and not re.fullmatch(r'/media/sounds/[^/\\]+\.mp3',path,re.I):
        raise ValueError('Choose a public Myinstants MP3 download link.')
    if any(part in ['.','..'] for part in path.split('/')): raise ValueError('Invalid Myinstants path.')
    return urlunsplit(('https','www.myinstants.com',p.path,p.query,''))

class SameSiteRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        validate_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch_bytes(url,limit,asset=False):
    url=validate_url(url,asset)
    request=Request(url,headers={'User-Agent':'MixForgeStudio/1.1 (local audio workstation)','Accept':'audio/mpeg' if asset else 'application/json'})
    try:
        with build_opener(SameSiteRedirects()).open(request,timeout=20) as response:
            validate_url(response.geturl(),asset)
            if int(response.headers.get('Content-Length','0'))>limit: raise ValueError('Myinstants sound is too large. Maximum download: 12 MB.')
            data=response.read(limit+1)
            if len(data)>limit: raise ValueError('Myinstants response is too large.')
            return data
    except HTTPError as e:
        if e.code==429: raise ValueError('Myinstants request limit reached. Wait a minute and try again.')
        raise ValueError(f'Myinstants returned HTTP {e.code}. Use Download MP3 on their website, then Upload sound here.')
    except (URLError,TimeoutError,OSError):
        raise ValueError('Could not reach Myinstants. Try again, or download the MP3 in your browser and upload it here.')

def api_json(path):
    url='https://www.myinstants.com/api/v1/instants/'+path
    now=time.monotonic()
    with _lock:
        if url in _cache and now-_cache[url][0]<300: return _cache[url][1]
        while _calls and now-_calls[0]>61: _calls.popleft()
        if len(_calls)>=10: raise ValueError('Myinstants allows 10 anonymous API calls per minute. Wait a minute or use a cached result.')
        _calls.append(now)
    try: result=json.loads(fetch_bytes(url,512*1024))
    except (json.JSONDecodeError,UnicodeDecodeError): raise ValueError('Myinstants did not return its expected API response. Download and upload the MP3 instead.')
    if not isinstance(result,dict): raise ValueError('Unexpected Myinstants API response.')
    with _lock:
        _cache[url]=(now,result)
        if len(_cache)>100: _cache.pop(next(iter(_cache)))
    return result

def search(query,page=1):
    query=query.strip()
    if not 1<=len(query)<=80: raise ValueError('Enter a sound name up to 80 characters.')
    result=api_json('?'+urlencode({'name':query,'page':page}))
    sounds=[]
    for item in result.get('results',[])[:12]:
        try:
            sound=validate_url(str(item['sound']),True); slug=str(item['slug'])
            if not re.fullmatch(r'[\w-]{1,200}',slug): continue
            sounds.append({'name':str(item.get('name',slug))[:120],'url':sound,'page_url':'https://www.myinstants.com/en/instant/'+quote(slug)+'/'})
        except (ValueError,KeyError,TypeError): continue
    return {'results':sounds,'count':int(result.get('count',len(sounds))),'next':bool(result.get('next')),'page':page}

def resolve(url):
    url=validate_url(url); p=urlsplit(url)
    if p.path.lower().startswith('/media/sounds/'):
        return {'url':validate_url(url,True),'name':Path(unquote(p.path)).name,'page_url':url}
    match=re.fullmatch(r'/(?:[a-z]{2}/)?instant/([\w-]{1,200})/?',unquote(p.path)) or re.fullmatch(r'/api/v1/instants/([\w-]{1,200})/?',unquote(p.path))
    if not match: raise ValueError('Paste a Myinstants sound page link or direct MP3 link.')
    slug=match.group(1); result=api_json(quote(slug,safe='')+'/')
    if not result.get('sound'): raise ValueError('No downloadable sound was returned by Myinstants.')
    return {'url':validate_url(str(result['sound']),True),'name':str(result.get('name',slug))[:120]+'.mp3','page_url':'https://www.myinstants.com/en/instant/'+quote(slug,safe='')+'/'}
