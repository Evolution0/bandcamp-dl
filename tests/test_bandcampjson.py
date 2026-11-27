import json

import bs4

from bandcamp_dl.bandcampjson import BandcampJSON


def page(pagedata='{"a": 1}', ld_json='{"b": 2}', tralbum='{"c": 3}', extra_scripts=""):
    parts = [f'<div id="pagedata" data-blob=\'{pagedata}\'></div>',
             f'<script type="application/ld+json">{ld_json}</script>',
             f'<script data-tralbum=\'{tralbum}\'>{tralbum}</script>',
             extra_scripts]
    return bs4.BeautifulSoup(f"<html><body>{''.join(parts)}</body></html>", "html.parser")


def test_an_album_page_yields_pagedata_ld_json_and_tralbum():
    body = page()

    entries = BandcampJSON(body).generate()

    merged = {}
    for entry in entries:
        merged.update(json.loads(entry))
    assert merged == {"a": 1, "b": 2, "c": 3}


def test_stray_scripts_do_not_break_extraction():
    body = page(extra_scripts='<script>var x = 1;</script>')

    merged = {}
    for entry in BandcampJSON(body).generate():
        merged.update(json.loads(entry))

    assert merged == {"a": 1, "b": 2, "c": 3}


def test_javascript_object_notation_becomes_valid_json():
    parser = BandcampJSON(page())

    assert json.loads(parser.js_to_json("{a: 1, b: [1, 2], /* comment */ c: 'x'}")) == {
        "a": 1, "b": [1, 2], "c": "x"}
