"""Generate three unapproved draft JSON files via OpenAI Responses API."""
import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
ROOT = Path(__file__).resolve().parent
TOPICS = [
    'AIで週次タスクを整理する手順',
    'AIでメールの下書きを作り人が確認する方法',
    'AIで会議メモを整理する際の注意点',
    'AIでSNS投稿の企画を立てる方法',
    'AIで表計算の作業手順を考える方法',
    'AIで仕事のチェックリストを作る方法',
    'AIで資料構成を考える方法',
]

def create_drafts(day=None, request=None):
    day = day or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('OPENAI_API_KEY is missing; no drafts created')
    model = os.environ.get('OPENAI_MODEL', 'gpt-5-mini')
    folder = ROOT / 'drafts'
    folder.mkdir(exist_ok=True)
    for n in range(3):
        filename = folder / f'{day.isoformat()}-{n+1}.json'
        if filename.exists():
            print('Already exists:', filename.name)
            continue
        topic = TOPICS[(day.toordinal() * 3 + n) % len(TOPICS)]
        prompt = (f'テーマ「{topic}」について日本語の実用記事を作成。JSONオブジェクトのみ出力。'
                  'キーは title,summary,body。bodyは段落を空行で区切ったプレーンテキスト。'
                  '実際に検証したと偽らない。料金・最新機能・数値・出典・体験談を捏造しない。'
                  '確認できない事項は要確認と明記。広告リンクやHTMLを含めない。'
                  '読者が自分で試せる手順と限界を説明。')
        payload = json.dumps({'model': model, 'input': prompt, 'store': False}).encode()
        req = Request('https://api.openai.com/v1/responses', data=payload,
                      headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
            try:
            opener = request or urlopen
            with opener(req, timeout=90) as response:
                result = json.load(response)
        except HTTPError as e:
            error_body = e.read().decode(
                'utf-8', errors='replace'
            )
            raise RuntimeError(
                f'OpenAI API error: HTTP {e.code}\n'
                f'{error_body}'
            ) from None
        text = '\n'.join(c.get('text', '') for output in result.get('output', [])
                         if output.get('type') == 'message' for c in output.get('content', [])
                         if c.get('type') == 'output_text').strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        article = json.loads(text)
        if not all(isinstance(article.get(k), str) and article[k].strip() for k in ('title', 'summary', 'body')):
            raise ValueError('AI returned invalid article; nothing saved for this item')
        draft = {k: article[k] for k in ('title', 'summary', 'body')}
        draft.update(slug=f'ai-work-{day:%Y%m%d}-{n+1}', verified=False,
                     approved=False, rights_checked=False, affiliate_key='',
                     publish_at=f'{day.isoformat()}T09:00:00+09:00')
        filename.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Draft created:', filename.name)
