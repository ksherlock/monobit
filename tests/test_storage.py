"""
monobit test suite
storage tests
"""

import os
import io
import unittest

import monobit
from .base import BaseTester


class TestCompressed(BaseTester):
    """Test compression formats."""

    def _test_compressed(self, format):
        """Test importing/exporting compressed files."""
        compressed_file = self.temp_path / f'4x6.yaff.{format}'
        monobit.save(self.fixed4x6, compressed_file)
        self.assertTrue(os.path.getsize(compressed_file) > 0)
        font, *_ = monobit.load(compressed_file)
        self.assertEqual(len(font.glyphs), 919)

    def test_gzip(self):
        """Test importing/exporting gzip compressed files."""
        self._test_compressed('gz')

    def test_lzma(self):
        """Test importing/exporting lzma compressed files."""
        self._test_compressed('xz')

    def test_bz2(self):
        """Test importing/exporting bzip2 compressed files."""
        self._test_compressed('bz2')


    def _test_double(self, format):
        """Test doubly compressed files."""
        container_file = self.font_path / f'double.yaff.{format}'
        font, *_ = monobit.load(container_file)
        self.assertEqual(len(font.glyphs), 919)

    def test_gzip2(self):
        """Test importing doubly gzip compressed files."""
        self._test_double('gz')

    def test_lzma(self):
        """Test importing doubly lzma compressed files."""
        self._test_double('xz')

    def test_bz2(self):
        """Test importing doubly bzip2 compressed files."""
        self._test_double('bz2')


class TestContainers(BaseTester):
    """Test container formats."""

    def _test_container(self, format):
        """Test importing/exporting container files."""
        container_file = self.temp_path / f'4x6.yaff.{format}'
        monobit.save(self.fixed4x6, container_file)
        self.assertTrue(os.path.getsize(container_file) > 0)
        font, *_ = monobit.load(container_file)
        self.assertEqual(len(font.glyphs), 919)

    def test_zip(self):
        """Test importing/exporting zip files."""
        self._test_container('zip')

    def test_tar(self):
        """Test importing/exporting tar files."""
        self._test_container('tar')

    def test_tgz(self):
        """Test importing/exporting compressed tar files."""
        self._test_container('tar.gz')

    def test_recursive(self):
        """Test recursively traversing container."""
        container_file = self.font_path / f'fontdir.tar.gz'
        fonts = monobit.load(container_file)
        self.assertEqual(len(fonts), 3)

    def test_recursive_dir(self):
        """Test recursively traversing directory."""
        container_file = self.font_path / 'fontdir'
        fonts = monobit.load(container_file)
        self.assertEqual(len(fonts), 3)

    def test_empty(self):
        """Test empty container."""
        container_file = self.font_path / 'empty.zip'
        fonts = monobit.load(container_file)
        self.assertEqual(len(fonts), 0)


class TestStreams(BaseTester):
    """Test stream i/o."""

    def test_binary_stream(self):
        """Test importing psf files from binary stream."""
        with open(self.font_path / '4x6.psf', 'rb') as f:
            fontbuffer = f.read()
        # we need peek()
        with io.BufferedReader(io.BytesIO(fontbuffer)) as stream:
            font, *_ = monobit.load(stream)
        self.assertEqual(len(font.glyphs), 919)

    def test_text_stream(self):
        """Test importing bdf files from text stream."""
        # we still need an underlying binary buffer, which StringIO doesn't have
        with open(self.font_path / '4x6.bdf', 'rb') as f:
            fontbuffer = f.read()
        with io.TextIOWrapper(io.BufferedReader(io.BytesIO(fontbuffer))) as stream:
            font, *_ = monobit.load(stream)
        self.assertEqual(len(font.glyphs), 919)

    def test_output_stream(self):
        """Test outputting multi-yaff file to text stream."""
        # we still need an underlying binary buffer, which StringIO doesn't have
        fnt_file = self.font_path / '8x16-font.cpi'
        fonts = monobit.load(fnt_file)
        with io.BytesIO() as stream:
            monobit.save(fonts, stream)
            output = stream.getvalue()
            self.assertTrue(len(output) > 80000)
            self.assertTrue(stream.getvalue().startswith(b'---'))


if __name__ == '__main__':
    unittest.main()
