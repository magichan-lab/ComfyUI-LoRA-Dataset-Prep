"""Build a portable visual review page for a prepared dataset."""

from html import escape
from pathlib import Path
from urllib.parse import quote


def write_review_index(output_folder: Path, source_files, records):
    """List every source image, including resumed and failed items, in source order."""
    results = {record['file']: record for record in records}
    cards = []
    counts = {'ready': 0, 'failed': 0, 'missing': 0}

    for source in source_files:
        image = output_folder / f'{source.stem}.png'
        caption_file = output_folder / f'{source.stem}.txt'
        result = results.get(source.name)
        failure = result and result['status'] != 'ok'
        label = escape(source.name)

        if failure:
            counts['failed'] += 1
            detail = f'<p class="problem">{escape(result["status"])}</p>'
            badge = '処理失敗'
            picture = ''
        elif not image.is_file() or not caption_file.is_file():
            counts['missing'] += 1
            detail = '<p class="problem">画像とキャプションのペアがありません。</p>'
            badge = '未完成'
            picture = ''
        else:
            try:
                caption = caption_file.read_text(encoding='utf-8').strip()
            except (OSError, UnicodeError) as exc:
                counts['failed'] += 1
                detail = f'<p class="problem">キャプションを読み込めません: {escape(str(exc))}</p>'
                badge = '確認不可'
                picture = ''
            else:
                counts['ready'] += 1
                badge = '作成済み' if result else '既存'
                image_url = quote(image.name, safe='')
                picture = f'<a href="{image_url}"><img src="{image_url}" alt="{label}" loading="lazy"></a>'
                detail = f'<p class="caption">{escape(caption)}</p>'

        cards.append(
            f'<article class="card"><div class="image">{picture}</div>'
            f'<div class="body"><div class="heading"><h2>{label}</h2><span>{badge}</span></div>{detail}</div></article>'
        )

    page = f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LoRA データセット確認用一覧</title>
<style>
  :root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
  body {{ max-width: 1500px; margin: 0 auto; padding: 24px; background: Canvas; color: CanvasText; }}
  h1 {{ margin-bottom: 8px; }}
  .summary {{ margin: 0 0 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; }}
  .card {{ border: 1px solid GrayText; border-radius: 8px; overflow: hidden; }}
  .image {{ height: 280px; display: grid; place-items: center; background: color-mix(in srgb, CanvasText 8%, Canvas); }}
  .image a {{ width: 100%; height: 100%; display: grid; place-items: center; }}
  .image img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
  .body {{ padding: 12px 14px; overflow-wrap: anywhere; }}
  .heading {{ display: flex; align-items: start; justify-content: space-between; gap: 8px; }}
  h2 {{ margin: 0; font-size: 1rem; }}
  .heading span {{ white-space: nowrap; font-size: .8rem; }}
  .caption {{ white-space: pre-wrap; line-height: 1.5; }}
  .problem {{ color: #c24536; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<h1>LoRA データセット確認用一覧</h1>
<p class="summary">全 {len(source_files)} 件 · 確認可能 {counts['ready']} 件 · 処理失敗・読み取り失敗 {counts['failed']} 件 · 未完成 {counts['missing']} 件</p>
<main class="grid">{''.join(cards)}</main>
</body>
</html>
'''
    target = output_folder / 'review_index.html'
    temporary = output_folder / 'review_index.partial.html'
    temporary.write_text(page, encoding='utf-8')
    temporary.replace(target)
    return target
