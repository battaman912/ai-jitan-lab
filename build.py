"""Approval-gated static publisher; Python standard library only."""
import argparse, datetime as dt, html, json, pathlib, re, shutil, sys
from urllib.parse import urlparse
ROOT=pathlib.Path(__file__).resolve().parent

def build(now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    out=ROOT/'site'; out.mkdir(exist_ok=True)
    for old in out.glob('*.html'): old.unlink()
    (out/'.nojekyll').touch()
    published=[]
    e=lambda v:html.escape(str(v),quote=True)
    if (ROOT/'STOP').exists():
        print('STOP switch active: no articles generated')
    else:
        for file in sorted((ROOT/'content').glob('*.json')):
            item=json.loads(file.read_text(encoding='utf-8'))
            if item.get('verified') is not True or item.get('approved') is not True:
                print('SKIP unapproved:',file.name);continue
            if item.get('rights_checked') is not True:
                print('SKIP rights unchecked:',file.name);continue
            stamp=dt.datetime.fromisoformat(item['publish_at'])
            if stamp.tzinfo is None: raise ValueError('Timezone required: '+file.name)
            if stamp.astimezone(dt.timezone.utc)>now:
                print('SKIP future:',file.name);continue
            slug=item['slug']
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug): raise ValueError('Unsafe slug')
            if any(x['slug']==slug for x in published): raise ValueError('Duplicate slug')
            affiliate_key=item.get('affiliate_key','')
            affiliate=cfg.get('affiliate_links',{}).get(affiliate_key,'') if affiliate_key else ''
            if affiliate_key and not affiliate:
                print('SKIP missing approved affiliate link:',file.name);continue
            if affiliate:
                parsed=urlparse(affiliate)
                if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password: raise ValueError('Invalid affiliate URL')
            e=lambda v:html.escape(str(v),quote=True)
            paragraphs=''.join('<p>'+e(p)+'</p>' for p in item['body'].split('\n\n') if p.strip())
            ad=f'<p class="ad">{e(cfg["disclosure"])}</p>' if affiliate else ''
            link=f'<p><a rel="sponsored nofollow noopener noreferrer" href="{e(affiliate)}">紹介サービスの詳細を見る（広告）</a></p>' if affiliate else ''
            page=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{e(item['summary'])}"><title>{e(item['title'])} | {e(cfg['site_name'])}</title><link rel="stylesheet" href="style.css"></head><body><header><a href="index.html">{e(cfg['site_name'])}</a></header><main>{ad}<article><h1>{e(item['title'])}</h1><p class="lead">{e(item['summary'])}</p>{paragraphs}{link}</article></main><footer><a href="about.html">運営者情報・広告について</a></footer></body></html>'''
            (out/(slug+'.html')).write_text(page,encoding='utf-8')
            published.append(item)
    links=''.join(f'<li><a href="{html.escape(i["slug"])}.html">{html.escape(i["title"])}</a><p>{html.escape(i["summary"])}</p></li>' for i in published)
    site=e(cfg['site_name'])
    (out/'index.html').write_text(f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{site}</title><link rel="stylesheet" href="style.css"><main><h1>{site}</h1><p>AIと仕事効率化を実際に検証して紹介するメディアです。</p><ul>{links}</ul><a href="about.html">運営者情報・広告について</a></main></html>',encoding='utf-8')
    (out/'about.html').write_text(f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>運営者情報 | {site}</title><link rel="stylesheet" href="style.css"><main><h1>運営者情報・広告について</h1><p>運営者情報・連絡先・プライバシーポリシーは公開前に実情報を記載してください。</p><p>このサイトはアフィリエイト広告を利用する場合があります。広告リンクのある記事には広告表示を行います。</p><a href="index.html">トップへ</a></main></html>',encoding='utf-8')
    (out/'style.css').write_text('body{font-family:system-ui,sans-serif;color:#172335;background:#f7fafc;line-height:1.85;margin:0}main,header,footer{max-width:780px;margin:auto;padding:22px}main{background:white;min-height:65vh}a{color:#1657a4}h1{line-height:1.4}.lead{font-size:1.15rem}.ad{padding:10px;background:#fff2cc}li{margin:18px 0}article{overflow-wrap:anywhere}',encoding='utf-8')
    print('Built',len(published),'approved articles; local output only')
    return published
if __name__=='__main__': build()
