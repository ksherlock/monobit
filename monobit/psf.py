"""
monobit.psf - read and write .psf font files

(c) 2019 Rob Hagemans
licence: https://opensource.org/licenses/MIT
"""

import struct
from types import SimpleNamespace

from .base import Glyph, Font, Typeface, ceildiv, struct_to_dict, dict_to_struct
from .raw import load_aligned, save_aligned


# PSF formats:
# https://www.win.tue.nl/~aeb/linux/kbd/font-formats-1.html

# PSF1 header
_PSF1_MAGIC = b'\x36\x04'
_PSF1_HEADER_FMT = '<BB'
_PSF1_HEADER_KEYS = ('mode', 'charsize')

# mode field
_PSF1_MODE512 = 0x01
_PSF1_MODEHASTAB = 0x02
#_PSF1_MODEHASSEQ = 0x04
#_PSF1_MAXMODE = 0x05

_PSF1_SEPARATOR = b'\xFF\xFF'
_PSF1_STARTSEQ =  b'\xFF\xFE'

# PSF2 header
_PSF2_MAGIC = b'\x72\xb5\x4a\x86'
_PSF2_HEADER_FMT = '<7L'
_PSF2_HEADER_KEYS = (
    'version', 'headersize', 'flags', 'length', 'charsize', 'height', 'width'
)

# flags field
_PSF2_HAS_UNICODE_TABLE = 0x01

# max version recognized so far
#_PSF2_MAXVERSION = 0

#/* UTF8 separators */
_PSF2_SEPARATOR = b'\xFF'
_PSF2_STARTSEQ = b'\xFE'


@Typeface.loads('psf', encoding=None)
def load(instream):
    """Load font from raw binary."""
    magic = instream.read(2)
    if magic == _PSF1_MAGIC:
        header_size = struct.calcsize(_PSF1_HEADER_FMT)
        psf_props = SimpleNamespace(**struct_to_dict(
            _PSF1_HEADER_FMT, _PSF1_HEADER_KEYS, instream.read(header_size)
        ))
        psf_props.width, psf_props.height = 8, psf_props.charsize
        psf_props.headersize = header_size + len(_PSF1_MAGIC)
        psf_props.length = 512 if (psf_props.mode & _PSF1_MODE512) else 256
        psf_props.has_unicode_table = bool(psf_props.mode & _PSF1_MODEHASTAB)
        separator = _PSF1_SEPARATOR
        startseq = _PSF1_STARTSEQ
        encoding = 'utf-16le'
    elif magic + instream.read(2) == _PSF2_MAGIC:
        header_size = struct.calcsize(_PSF2_HEADER_FMT)
        psf_props = SimpleNamespace(**struct_to_dict(
            _PSF2_HEADER_FMT, _PSF2_HEADER_KEYS, instream.read(struct.calcsize(_PSF2_HEADER_FMT))
        ))
        charsize = psf_props.height * ceildiv(psf_props.width, 8)
        if psf_props.charsize != charsize:
            logging.warning('Ingnoring inconsistent char size in PSF header.')
            psf_props.charsize = charsize
        psf_props.has_unicode_table = bool(psf_props.flags & _PSF2_HAS_UNICODE_TABLE)
        # ignore any padding after header
        padding = psf_props.headersize - (header_size + len(_PSF2_MAGIC))
        instream.read(padding)
        separator = _PSF2_SEPARATOR
        startseq = _PSF2_STARTSEQ
        encoding = 'utf-8'
    cells = load_aligned(instream, (psf_props.width, psf_props.height), psf_props.length)
    table = _read_unicode_table(instream, separator, startseq, encoding)
    # convert unicode table to labels
    # FIXME: deal with empty labels; include ordinal value as additional label
    glyphs = {
        ','.join(
            'u+{:04x}'.format(ord(_uc))
            for _uc in _seq
        ): _glyph
        for _seq, _glyph in zip(table, cells)
    }
    return Typeface([Font(glyphs)])

def _read_unicode_table(instream, separator, startseq, encoding):
    """Read the Unicode table in a PSF2 file."""
    raw_table = instream.read()
    entries = raw_table.split(separator)[:-1]
    table = []
    for point, entry in enumerate(entries):
        split = entry.split(startseq)
        code_points = [_seq.decode(encoding) for _seq in split]
        # first entry is separate code points, following entries (if any) are sequences
        table.append([_c for _c in code_points[0]] + code_points[1:])
    return table



@Typeface.saves('psf', encoding=None)
def save(typeface, outstream):
    """Save font to raw byte-aligned binary (DOS font)."""
    if len(typeface._fonts) > 1:
        raise ValueError('Saving multiple fonts to .psf not possible')
    font = typeface._fonts[0]
    psf_props = {
        'width': font.max_width,
        'height': font.max_height,
        'charsize': font.max_height * ceildiv(font.max_width, 8),
        'version': 0,
        'flags': 0, #_PSF2_HAS_UNICODE_TABLE,
        'length': font.max_key + 1,
    }
    outstream.write(_PSF2_MAGIC)
    outstream.write(dict_to_struct(psf_props, _PSF2_HEADER_FMT, _PSF2_HEADER_KEYS))
    save_aligned(outstream, font)
    ... # unicode table
    return typeface
