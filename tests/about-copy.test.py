"""Keep the approved collection principles and project origin in sync."""
from html.parser import HTMLParser
from pathlib import Path
from approved_about_copy import README_ADDITION, INDEX_ADDITION

ROOT = Path(__file__).resolve().parents[1]
readme = (ROOT / 'README.md').read_text()
index = (ROOT / 'index.html').read_text()
assert readme.count(README_ADDITION) == 1
assert index.count(INDEX_ADDITION) == 1
about = index.split('<dialog id="about-dialog"', 1)[1].split('</dialog>', 1)[0]
assert INDEX_ADDITION in about
for heading in ['收录原则', '项目缘起', '浏览', '来源与使用', '补充线索']:
    assert about.count('<h3>' + heading + '</h3>') == 1

class CopyText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    def handle_data(self, text):
        if text.strip():
            self.text.append(text.strip())

parser = CopyText()
parser.feed(INDEX_ADDITION)
lines = [line.removeprefix('## ').removeprefix('- ') for line in README_ADDITION.splitlines() if line]
assert parser.text == lines, 'README and site copy differ'
assert INDEX_ADDITION.count('<li>') == 4
assert INDEX_ADDITION.count('<p>') == 2
print('About copy: approved principles and origin match exactly in README and website; prior explanation sections preserved.')
