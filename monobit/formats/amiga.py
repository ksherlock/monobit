"""
monobit.amiga - Amiga font format

(c) 2019--2021 Rob Hagemans
licence: https://opensource.org/licenses/MIT
"""

import os
import struct
import logging

from ..binary import bytes_to_bits
from ..struct import friendlystruct, Props
from ..storage import loaders, savers
from ..streams import FileFormatError
from ..font import Font, Coord
from ..glyph import Glyph


@loaders.register('font', magic=(b'\x0f\0', b'\x0f\2'), name='Amiga Font Contents')
def load_amiga_fc(f, where):
    """Load font from Amiga disk font contents (.FONT) file."""
    fch = _FONT_CONTENTS_HEADER.read_from(f)
    if fch.fch_FileID == 0x0f00:
        logging.debug('Amiga FCH using FontContents')
    elif fch.fch_FileID == 0x0f02:
        logging.debug('Amiga FCH using TFontContents')
    else:
        raise FileFormatError('Not an Amiga Font Contents file.')
    contentsarray = _FONT_CONTENTS.array(fch.fch_NumEntries).read_from(f)
    pack = []
    for fc in contentsarray:
        # we'll get ysize, style and flags from the file itself, we just need a path.
        # latin-1 seems to be the standard for amiga strings,
        # see e.g. https://wiki.amigaos.net/wiki/FTXT_IFF_Formatted_Text#Data_Chunk_CHRS
        name = fc.fc_FileName.decode('latin-1')
        # amiga fs is case insensitive, so we need to loop over listdir and match
        for filename in where:
            if filename.lower() == name.lower():
                pack.append(_load_amiga(where.open(filename, 'r'), where))
    return pack


@loaders.register('amiga', magic=(b'\0\0\x03\xf3',), name='Amiga Font')
def load_amiga(f, where=None):
    """Load font from Amiga disk font file."""
    return _load_amiga(f, where)



###################################################################################################
# AmigaOS font format
#
# developer docs: Graphics Library and Text
# https://wiki.amigaos.net/wiki/Graphics_Library_and_Text
# http://amigadev.elowar.com/read/ADCD_2.1/Libraries_Manual_guide/node03D2.html
#
# references on binary file format
# http://amiga-dev.wikidot.com/file-format:hunk
# https://archive.org/details/AmigaDOS_Technical_Reference_Manual_1985_Commodore/page/n13/mode/2up (p.14)


# amiga header constants
_MAXFONTPATH = 256
_MAXFONTNAME = 32

# hunk ids
# http://amiga-dev.wikidot.com/file-format:hunk
_HUNK_HEADER = 0x3f3
_HUNK_CODE = 0x3e9
_HUNK_RELOC32 = 0x3ec
_HUNK_END = 0x3f2

# tf_Flags values
# font is in rom
_FPF_ROMFONT = 0x01
# font is from diskfont.library
_FPF_DISKFONT = 0x02
# This font is designed to be printed from from right to left
_FPF_REVPATH = 0x04
# This font was designed for a Hires screen (640x200 NTSC, non-interlaced)
_FPF_TALLDOT = 0x08
# This font was designed for a Lores Interlaced screen (320x400 NTSC)
_FPF_WIDEDOT = 0x10
# character sizes can vary from nominal
_FPF_PROPORTIONAL = 0x20
# size explicitly designed, not constructed
_FPF_DESIGNED = 0x40
# the font has been removed
_FPF_REMOVED = 0x80

# tf_Style values
# underlined (under baseline)
_FSF_UNDERLINED	= 0x01
# bold face text (ORed w/ shifted)
_FSF_BOLD = 0x02
# italic (slanted 1:2 right)
_FSF_ITALIC	= 0x04
# extended face (wider than normal)
_FSF_EXTENDED = 0x08
# this uses ColorTextFont structure
_FSF_COLORFONT = 0x40
# the TextAttr is really a TTextAttr
_FSF_TAGGED = 0x80

# Amiga hunk file header
# http://amiga-dev.wikidot.com/file-format:hunk#toc6
_HUNK_FILE_HEADER_0 = friendlystruct(
    '>',
    hunk_id='uint32',
)
# followed by null-null-terminated string table
# followed by
_HUNK_FILE_HEADER_1 = friendlystruct(
    '>',
    table_size='uint32',
    first_hunk='uint32',
    last_hunk='uint32',
)
# followed by hunk_sizes = uint32 * (last_hunk-first_hunk+1)

# disk font header
_AMIGA_HEADER = friendlystruct(
    '>',
    # struct DiskFontHeader
    # http://amigadev.elowar.com/read/ADCD_2.1/Libraries_Manual_guide/node05F9.html#line61
    dfh_NextSegment='I',
    dfh_ReturnCode='I',
    # struct Node
    # http://amigadev.elowar.com/read/ADCD_2.1/Libraries_Manual_guide/node02EF.html
    dfh_ln_Succ='I',
    dfh_ln_Pred='I',
    dfh_ln_Type='B',
    dfh_ln_Pri='b',
    dfh_ln_Name='I',
    dfh_FileID='H',
    dfh_Revision='H',
    dfh_Segment='i',
    dfh_Name=friendlystruct.char * _MAXFONTNAME,
    # struct Message at start of struct TextFont
    # struct Message http://amigadev.elowar.com/read/ADCD_2.1/Libraries_Manual_guide/node02EF.html
    tf_ln_Succ='I',
    tf_ln_Pred='I',
    tf_ln_Type='B',
    tf_ln_Pri='b',
    tf_ln_Name='I',
    tf_mn_ReplyPort='I',
    tf_mn_Length='H',
    # struct TextFont http://amigadev.elowar.com/read/ADCD_2.1/Libraries_Manual_guide/node03DE.html
    tf_YSize='H',
    tf_Style='B',
    tf_Flags='B',
    tf_XSize='H',
    tf_Baseline='H',
    tf_BoldSmear='H',
    tf_Accessors='H',
    tf_LoChar='B',
    tf_HiChar='B',
    tf_CharData='I',
    tf_Modulo='H',
    tf_CharLoc='I',
    tf_CharSpace='I',
    tf_CharKern='I',
)

# struct FontContentsHeader
# .font directory file
# https://wiki.amigaos.net/wiki/Graphics_Library_and_Text#Composition_of_a_Bitmap_Font_on_Disk
_FONT_CONTENTS_HEADER = friendlystruct(
    '>',
    fch_FileID='uword',
    fch_NumEntries='uword',
    # followed by array of FontContents or TFontContents
)

# struct FontContents
_FONT_CONTENTS = friendlystruct(
    '>',
    fc_FileName=friendlystruct.char * _MAXFONTPATH,
    fc_YSize='uword',
    fc_Style='ubyte',
    fc_Flags='ubyte',
)

# struct TFontContents
# not used - we ignore the extra tags stored at the back of the tfc_FileName field
_T_FONT_CONTENTS = friendlystruct(
    '>',
    tfc_FileName=friendlystruct.char * (_MAXFONTPATH-2),
    tfc_TagCount='uword',
    tfc_YSize='uword',
    tfc_Style='ubyte',
    tfc_Flags='ubyte',
)


###################################################################################################
# read Amiga font


def _load_amiga(f, where):
    """Load font from Amiga disk font file."""
    # read & ignore header
    _read_header(f)
    hfh0 = _HUNK_FILE_HEADER_0.read_from(f)
    if hfh0.hunk_id != _HUNK_CODE:
        raise FileFormatError('Not an Amiga font data file: no code hunk found (id %04x)' % hfh0.hunk_id)
    props, glyphs, kerning, spacing = _read_font_hunk(f)
    return _convert_amiga_font(props, glyphs, kerning, spacing)

def _read_library_names(f):
    library_names = []
    while True:
        num_longs = friendlystruct.uint32.from_buffer_copy(f.read(4))
        if not num_longs:
            return library_names
        string = f.read(num_longs * 4)
        # http://amiga-dev.wikidot.com/file-format:hunk#toc6
        # - partitions the read string at null terminator and breaks on empty
        # https://archive.org/details/AmigaDOS_Technical_Reference_Manual_1985_Commodore/page/n27/mode/2up
        # - suggests this can't happen, length uint32 must be zero
        # - also parse_header() at https://github.com/cnvogelg/amitools/blob/master/amitools/binfmt/hunk/HunkReader.py
        library_names.append(string)

def _read_header(f):
    """Read file header."""
    # read header id
    hfh0 = _HUNK_FILE_HEADER_0.read_from(f)
    if hfh0.hunk_id != _HUNK_HEADER:
        raise FileFormatError('Not an Amiga font data file: magic constant {hfh0.hunk_id:X} != 0x3F3')
    library_names = _read_library_names(f)
    hfh1 = _HUNK_FILE_HEADER_1.read_from(f)
    # list of memory sizes of hunks in this file (in number of ULONGs)
    # this seems to exclude overhead, so not useful to determine disk sizes
    num_sizes = hfh1.last_hunk - hfh1.first_hunk + 1
    hunk_sizes = (friendlystruct.uint32 * num_sizes).from_buffer_copy(f.read(4 * num_sizes))
    return library_names, hfh1, hunk_sizes

def _read_font_hunk(f):
    """Parse the font data blob."""
    #loc = f.tell() + 4
    amiga_props = _AMIGA_HEADER.read_from(f)
    logging.info('Amiga properties:')
    for name, value in vars(amiga_props).items():
        logging.info('    %s: %s', name, value)
    # the reference point for locations in the hunk is just after the ReturnCode
    loc = - _AMIGA_HEADER.size + 4
    # remainder is the font strike
    data = f.read()
    # read character data
    glyphs, kerning, spacing = _read_strike(
        data, amiga_props.tf_XSize, amiga_props.tf_YSize,
        amiga_props.tf_Flags & _FPF_PROPORTIONAL,
        amiga_props.tf_Modulo, amiga_props.tf_LoChar, amiga_props.tf_HiChar,
        amiga_props.tf_CharData + loc, amiga_props.tf_CharLoc + loc,
        None if not amiga_props.tf_CharSpace else amiga_props.tf_CharSpace + loc,
        None if not amiga_props.tf_CharKern else amiga_props.tf_CharKern + loc
    )
    return amiga_props, glyphs, kerning, spacing


def _read_strike(
        data, xsize, ysize, proportional, modulo, lochar, hichar,
        pos_chardata, pos_charloc, pos_charspace, pos_charkern
    ):
    """Read and interpret the font strike and related tables."""
    rows = [
        bytes_to_bits(data[pos_chardata + _item*modulo : pos_chardata + (_item+1)*+modulo])
        for _item in range(ysize)
    ]
    # location data
    nchars = hichar - lochar + 1 + 1 # one additional glyph at end for undefined chars
    loc_struct = friendlystruct('>', offset='H', width='H')
    locs = [
        loc_struct.from_bytes(data, pos_charloc+_i*loc_struct.size)
        for _i in range(nchars)
    ]
    font = [
        [_row[_loc.offset: _loc.offset+_loc.width] for _row in rows]
        for _loc in locs
    ]
    # spacing data, can be negative
    if proportional:
        spc_struct = friendlystruct('>', space='h')
        spacing = [
            spc_struct.from_bytes(data, pos_charspace+_i*spc_struct.size).space
            for _i in range(nchars)
        ]
        # check spacing
        for i, sp in enumerate(spacing):
            if sp < 0:
                logging.warning('negative spacing of %d in %dth character' % (sp, i,))
            if abs(sp) > xsize*2:
                logging.error('very high values in spacing table')
                spacing = (xsize,) * len(font)
                break
    else:
        spacing = (xsize,) * len(font)
    if pos_charkern is not None:
        # amiga "kerning" is a horizontal offset; can be pos (to right) or neg
        kern_struct = friendlystruct('>', kern='h')
        kerning = [
            kern_struct.from_bytes(data, pos_charkern+_i*kern_struct.size).kern
            for _i in range(nchars)
        ]
        for i, sp in enumerate(kerning):
            if abs(sp) > xsize*2:
                logging.error('very high values in kerning table')
                kerning = (0,) * len(font)
                break
    else:
        kerning = (0,) * len(font)
    # extract glyphs
    glyphs = [Glyph(_char, codepoint=_ord) for _ord, _char in enumerate(font, start=lochar)]
    return glyphs, kerning, spacing


###################################################################################################
# convert from Amiga to monobit

def _convert_amiga_font(amiga_props, glyphs, kerning, spacing):
    """Convert Amiga properties and glyphs to monobit Font."""
    glyphs, offset_x = _normalise_glyphs(glyphs, kerning, spacing)
    props = _parse_amiga_props(amiga_props, offset_x)
    logging.info('yaff properties:')
    for line in str(props).splitlines():
        logging.info('    ' + line)
    return Font(glyphs, properties=vars(props))


def _normalise_glyphs(glyphs, kerning, spacing):
    """Deal with negative kerning by turning it into a global negative offset."""
    offset_x = min(kerning)
    kerning = [_kern - offset_x for _kern in kerning]
    # apply kerning and spacing
    glyphs = [
        _glyph.expand(left=_kern, right=max(0, _space-_glyph.width))
        for _glyph, _space, _kern in zip(glyphs, spacing, kerning)
    ]
    # default glyph has no codepoint
    glyphs[-1] = glyphs[-1].set_annotations(codepoint=(), tags=('default',))
    return glyphs, offset_x


def _parse_amiga_props(amiga_props, offset_x):
    """Convert AmigaFont properties into yaff properties."""
    if amiga_props.tf_Style & _FSF_COLORFONT:
        raise FileFormatError('Amiga ColorFont not supported')
    props = Props()
    props.amiga = Props()
    # preserve tags stored in name field after \0
    name, *tags = amiga_props.dfh_Name.decode('latin-1').split('\0')
    if name:
        props.name = name.strip()
    if tags:
        props.amiga.dfh_Name = f'"{name}"' + ' '.join(tags)
    props.revision = amiga_props.dfh_Revision
    props.offset = Coord(offset_x, -(amiga_props.tf_YSize - amiga_props.tf_Baseline))
    # tf_Style
    props.weight = 'bold' if amiga_props.tf_Style & _FSF_BOLD else 'medium'
    props.slant = 'italic' if amiga_props.tf_Style & _FSF_ITALIC else 'roman'
    props.setwidth = 'expanded' if amiga_props.tf_Style & _FSF_EXTENDED else 'medium'
    if amiga_props.tf_Style & _FSF_UNDERLINED:
        props.decoration = 'underline'
    # tf_Flags
    props.spacing = (
        'proportional' if amiga_props.tf_Flags & _FPF_PROPORTIONAL else 'monospace'
    )
    if amiga_props.tf_Flags & _FPF_REVPATH:
        props.direction = 'right-to-left'
        logging.warning('right-to-left fonts are not correctly implemented yet')
    if amiga_props.tf_Flags & _FPF_TALLDOT and not amiga_props.tf_Flags & _FPF_WIDEDOT:
        # TALLDOT: This font was designed for a Hires screen (640x200 NTSC, non-interlaced)
        props.dpi = '96 48'
    elif amiga_props.tf_Flags & _FPF_WIDEDOT and not amiga_props.tf_Flags & _FPF_TALLDOT:
        # WIDEDOT: This font was designed for a Lores Interlaced screen (320x400 NTSC)
        props.dpi = '48 96'
    else:
        props.dpi = 96
    props.encoding = 'iso8859-1'
    props.default_char = 'default'
    # preserve unparsed properties
    # tf_BoldSmear; /* smear to affect a bold enhancement */
    # use the most common value 1 as a default
    if amiga_props.tf_BoldSmear != 1:
        props.amiga.tf_BoldSmear = amiga_props.tf_BoldSmear
    if 'name' in props:
        props.family = props.name.split('/')[0].split(' ')[0]
    return props
