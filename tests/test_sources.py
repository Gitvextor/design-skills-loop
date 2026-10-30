from pathlib import Path
import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sources', ROOT / 'scripts/sources.py')
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)


class SourceTests(unittest.TestCase):
    def fixture(self, root, extra=None):
        archive = root / 'source.zip'
        with zipfile.ZipFile(archive, 'w') as bundle:
            bundle.writestr('repo-sha/skill/SKILL.md', 'Original source')
            bundle.writestr('repo-sha/LICENSE', 'Original license')
            bundle.writestr('repo-sha/unrelated.txt', 'Not selected')
            if extra:
                for name, data in extra.items():
                    bundle.writestr(name, data)
        source = {'id': 'sample', 'commit': 'a' * 40,
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'entry': 'skill/SKILL.md', 'license_file': 'LICENSE',
                  'include': ['skill/', 'LICENSE']}
        return archive, source

    def test_prepares_selected_sources_and_preserves_license(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, source = self.fixture(root)
            target = sources.extract_source(archive, source, root / 'deps')
            self.assertEqual((target / 'LICENSE').read_text(), 'Original license')
            self.assertFalse((target / 'unrelated.txt').exists())
            sources.verify_source(target, source)

    def test_bad_hash_does_not_extract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, source = self.fixture(root)
            source['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'Checksum'):
                sources.extract_source(archive, source, root / 'deps')
            self.assertFalse((root / 'deps').exists())

    def test_rejects_parent_traversal_without_writing_outside(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, source = self.fixture(root, {'repo-sha/../../escape.txt': 'bad'})
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                sources.extract_source(archive, source, root / 'deps')
            self.assertFalse((root / 'escape.txt').exists())
            self.assertFalse((root / 'deps/sample').exists())

    def test_rejects_mutated_dependency_and_preserves_existing_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, source = self.fixture(root)
            target = sources.extract_source(archive, source, root / 'deps')
            (target / 'skill/SKILL.md').write_text('Modified')
            with self.assertRaisesRegex(ValueError, 'Modified'):
                sources.verify_source(target, source)
            with self.assertRaises(FileExistsError):
                sources.extract_source(archive, source, root / 'deps')
            self.assertEqual((target / 'skill/SKILL.md').read_text(), 'Modified')

    def test_missing_license_fails_before_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, source = self.fixture(root)
            source['license_file'] = 'MISSING-LICENSE'
            with self.assertRaisesRegex(ValueError, 'Missing required'):
                sources.extract_source(archive, source, root / 'deps')
            self.assertFalse((root / 'deps/sample').exists())

    def test_locked_sources_match_configured_unique_sequence(self):
        manifest = sources.read_sources(ROOT)
        self.assertEqual(len(manifest), 7)
        config = json.loads((ROOT / 'loop.config.json').read_text(encoding='utf8'))
        self.assertEqual(config['max_iterations'], 6)
        self.assertEqual([s['id'] for s in manifest], config['sequence'])


if __name__ == '__main__':
    unittest.main()
