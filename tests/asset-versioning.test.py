"""Content-versioned local scripts; all mutation checks use temporary copies."""
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ('data/catalog.js', 'data/collection-history.js', 'app.js')
spec = importlib.util.spec_from_file_location('generate_static', ROOT / 'scripts/generate_static.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class Scripts(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.scripts = []
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('src'):
            self.scripts.append(dict(attrs))


def versions(root):
    scripts = Scripts((root / 'index.html').read_text()).scripts
    assert [urlsplit(s['src']).path for s in scripts] == list(ASSETS)
    result = {}
    for script in scripts:
        src = script['src']
        url = urlsplit(src)
        assert not url.scheme and not url.netloc and not url.fragment
        assert 'defer' in script and 'async' not in script
        digest = sha256((root / url.path).read_bytes()).hexdigest()[:16]
        assert src == url.path + '?v=' + digest
        assert parse_qs(url.query) == {'v': [digest]}
        # A query is not part of the local filename when loaded via file://.
        resolved = urlsplit(urljoin((root / 'index.html').as_uri(), src))
        assert resolved.scheme == 'file'
        assert Path(unquote(resolved.path)) == root / url.path
        result[url.path] = digest
    return result


def snapshot(root):
    return {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


class AssetVersioning(unittest.TestCase):
    def temporary_tree(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name) / 'site'
        # Copy only build inputs/outputs, without Git, private sources or caches.
        target.mkdir()
        for name in ('data', 'fonts', 'scripts'):
            shutil.copytree(ROOT / name, target / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('app.js', 'index.html', 'sitemap.xml'):
            shutil.copyfile(ROOT / name, target / name)
        return target

    def build(self, root, succeeds=True):
        result = subprocess.run([sys.executable, 'scripts/workspace.py', 'build'],
                                cwd=root, capture_output=True, text=True)
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def test_checked_in_versions_match_actual_bytes_and_file_paths(self):
        versions(ROOT)

    def test_two_builds_are_byte_identical(self):
        root = self.temporary_tree()
        before = snapshot(root)
        self.build(root)
        self.assertEqual(snapshot(root), before)
        self.build(root)
        self.assertEqual(snapshot(root), before)

    def test_each_changed_asset_updates_only_its_own_version(self):
        for asset in ASSETS:
            with self.subTest(asset=asset):
                root = self.temporary_tree()
                before = versions(root)
                if asset == 'app.js':
                    with (root / asset).open('a') as out:
                        out.write('\n// Temporary version regression fixture.\n')
                else:
                    source = root / asset.replace('.js', '.json')
                    data = json.loads(source.read_text())
                    if asset == 'data/catalog.js':
                        data[0]['name'] += ' (version fixture)'
                    else:
                        data['versionFixture'] = True
                    source.write_text(json.dumps(data, ensure_ascii=False))
                self.build(root)
                after = versions(root)
                self.assertEqual([name for name in ASSETS if before[name] != after[name]], [asset])

    def test_missing_or_duplicate_reference_fails_without_writing_outputs(self):
        for asset in ASSETS:
            for duplicate in (False, True):
                with self.subTest(asset=asset, duplicate=duplicate):
                    root = self.temporary_tree()
                    index = root / 'index.html'
                    document = index.read_text()
                    tag = re.search(r'<script defer src="' + re.escape(asset) + r'\?v=[a-f0-9]+"></script>', document)[0]
                    index.write_text(document.replace(tag, tag + tag if duplicate else '', 1))
                    before = snapshot(root)
                    result = self.build(root, succeeds=False)
                    self.assertIn(f'Expected exactly one managed script src for {asset}; found {2 if duplicate else 0}', result.stderr)
                    self.assertEqual(snapshot(root), before)

    def test_existing_versions_are_upgraded_without_other_html_changes(self):
        assets = {name: (ROOT / name).read_bytes() for name in ASSETS}
        document = '<!-- <script src="data/catalog.js"></script> -->\n'
        document += '<link rel="stylesheet" href="styles.css?v=keep">\n'
        document += '<script defer src="unmanaged.js?v=keep"></script>\n'
        document += ''.join(f"<SCRIPT defer SRC = '{name}?v=old'></SCRIPT>\n" for name in ASSETS)
        expected = document
        for name in ASSETS:
            expected = expected.replace(f"{name}?v=old", name + '?v=' + sha256(assets[name]).hexdigest()[:16])
        self.assertEqual(generator.version_scripts(document, assets), expected)
        self.assertEqual(generator.version_scripts(expected, assets), expected)

    def test_historical_builder_audit_rejects_unknown_generator_changes(self):
        root = self.temporary_tree()
        (root / 'tests').mkdir()
        helper = root / 'tests/approved_mrobe_mr100.py'
        shutil.copyfile(ROOT / 'tests/approved_mrobe_mr100.py', helper)
        spec = importlib.util.spec_from_file_location('historical_version_fixture', helper)
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        self.assertEqual(audit.before_mrobe_file_sha('scripts/generate_static.py'),
                         '7d4ebcc6e622d103cdbf2b7b54ff08df1aa98fb200f0e5d3a11c6ea6a57dc6a4')
        with (root / 'scripts/generate_static.py').open('a') as out:
            out.write('\n# Unreviewed change must not pass the historical audit.\n')
        with self.assertRaises(AssertionError):
            audit.before_mrobe_file_sha('scripts/generate_static.py')

    def test_unversioned_sources_are_upgraded(self):
        assets = {name: (ROOT / name).read_bytes() for name in ASSETS}
        document = ''.join(f'<script defer src="{name}"></script>' for name in ASSETS)
        actual = generator.version_scripts(document, assets)
        expected = ''.join(f'<script defer src="{name}?v={sha256(assets[name]).hexdigest()[:16]}"></script>' for name in ASSETS)
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
