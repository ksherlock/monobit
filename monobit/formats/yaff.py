"""
monobit.yaff - monobit-yaff and Unifont HexDraw formats

(c) 2019--2022 Rob Hagemans
licence: https://opensource.org/licenses/MIT
"""

import logging
import string
from dataclasses import dataclass, field
from itertools import count, zip_longest
from collections import deque

from ..storage import loaders, savers
from ..encoding import charmaps
from ..streams import FileFormatError
from ..font import Font
from ..glyph import Glyph
from ..labels import strip_matching
from ..struct import Props


##############################################################################
# interface


@loaders.register('yaff', 'yaffs', magic=(b'---',), name='yaff')
def load_yaff(instream, where=None):
    """Load font from a monobit .yaff file."""
    return _load_yaff(instream.text)

@savers.register(linked=load_yaff)
def save_yaff(fonts, outstream, where=None):
    """Write fonts to a monobit .yaff file."""
    YaffWriter().save(fonts, outstream.text)


##############################################################################
# format parameters

BOUNDARY_MARKER = '---'


class YaffParams:
    """Parameters for .yaff format."""

    # first/second pass constants
    separator = ':'
    comment = '#'
    # output only
    tab = '    '
    # tuple of individual chars, need to be separate for startswith
    whitespace = tuple(' \t')

    # third-pass constants
    ink = '@'
    paper = '.'
    empty = '-'


##############################################################################
##############################################################################
# read file


def _load_yaff(text_stream):
    """Parse a yaff/yaffs file."""
    reader = YaffReader()
    fonts = []
    for line in text_stream:
        if line.strip() == BOUNDARY_MARKER:
            fonts.append(reader.get_font())
            reader = YaffReader()
        else:
            reader.step(line)
    fonts.append(reader.get_font())
    return fonts


@dataclass
class YaffElement:
    keys: list = field(default_factory=list)
    value: list = field(default_factory=list)
    comment: list = field(default_factory=list)
    indent: int = 0


class YaffReader:
    """Parser for text-based font file."""

    def __init__(self):
        """Set up text reader."""
        # current element appending to
        self._current = YaffElement()
        # elements done
        self._elements = deque()

    # first pass: lines to elements

    def _yield_element(self):
        """Close and append current element and start a new one."""
        if self._current.keys or self._current.value or self._current.comment:
            self._elements.append(self._current)
        self._current = YaffElement()

    def step(self, line):
        """Parse a single line."""
        # strip trailing whitespace
        contents = line.rstrip()
        if not contents:
            # ignore empty lines except while already parsing comments
            if (
                    self._current.comment
                    and not self._current.value
                    and not self._current.keys
                ):
                self._current.comment.append('')
        else:
            startchar = contents[:1]
            if startchar == YaffParams.comment:
                if self._current.keys or self._current.value:
                    # new comment starts new element
                    self._yield_element()
                self._current.comment.append(contents[1:])
            elif startchar not in YaffParams.whitespace:
                if contents[-1:] == YaffParams.separator:
                    if self._current.value:
                        # new key when we have a value starts a new element
                        self._yield_element()
                    self._current.keys.append(contents[:-1])
                else:
                    # this must be a property key, not a glyph label
                    # so starts a new element
                    if self._current.value or self._current.keys:
                        self._yield_element()
                    # new key, separate at the first :
                    # prop keys must be alphanum so no need to worry about quoting
                    key, sep, value = contents.partition(YaffParams.separator)
                    # yield key and value
                    # yaff does not allow multiline values starting on the key line
                    self._current.keys.append(key.rstrip())
                    self._current.value.append(value.lstrip())
                    self._yield_element()
            else:
                # first line in value
                if not self._current.value:
                    self._current.indent = len(contents) - len(contents.lstrip())
                # continue building value
                # do not strip all whitespace as we need it for multiline glyph props
                # but strip the first line's indent
                self._current.value.append(contents[self._current.indent:])


    # second pass: elements to clusters

    def get_clusters(self):
        """Convert elements to clusters and return."""
        self._yield_element()
        # run second pass and append
        clusters = self._elements
        # separate out global top comment
        if clusters and clusters[0]:
            top = clusters[0]
            comments = top.comment
            # find last empty line which separates global from prop comment
            try:
                index = len(comments) - comments[::-1].index('')
            except ValueError:
                index = len(comments) + 1
            if len(comments) > 1:
                global_comment = YaffElement(comment=comments[:index])
                top.comment = comments[index+1:]
                clusters.appendleft(global_comment)
        return clusters


    # third pass: interpret clusters

    def get_font(self):
        """Get clusters from reader and convert to Font."""
        clusters = self.get_clusters()
        # recursive call
        glyphs, props, comments = convert_clusters(clusters)
        if not glyphs:
            raise FileFormatError('No glyphs found in yaff file.')
        return Font(glyphs, comment=comments, **props)


def convert_clusters(clusters):
    """Convert cluster."""
    props = {}
    comments = {}
    glyphs = []
    for cluster in clusters:
        if not cluster.keys:
            # global comment
            comments[''] = normalise_comment(cluster.comment)
        elif _line_is_glyph(cluster.value[0]):
            # if first line in the value has only glyph symbols, it's a glyph
            glyphs.append(_convert_glyph(cluster))
        else:
            key, value, comment = convert_property(cluster)
            if value:
                props[key] = value
            # property comments
            if comment:
                comments[key] = comment
    return glyphs, props, comments

def convert_property(cluster):
    """Convert property cluster."""
    # there should not be multiple keys for a property
    key = cluster.keys.pop(0)
    if cluster.keys:
        logging.warning('ignored excess keys: %s', cluster.keys)
    # Props object converts only non-leading underscores
    # so we need to make sure we turn those into dashes
    key = key.replace('_', '-')
    value = '\n'.join(strip_matching(_line, '"') for _line in cluster.value)
    comment = normalise_comment(cluster.comment)
    return key, value, comment

def _line_is_glyph(value):
    """Text line is a glyph."""
    return value and (
        (value == YaffParams.empty)
        or not(set(value) - set((YaffParams.ink, YaffParams.paper, ' ', '\t', '\n')))
    )

def _convert_glyph(cluster):
    """Parse single glyph."""
    keys = cluster.keys
    lines = cluster.value
    comment = normalise_comment(cluster.comment)
    # find first property row
    # note empty lines have already been dropped by reader
    is_prop = tuple(YaffParams.separator in _line for _line in lines)
    try:
        first_prop = is_prop.index(True)
    except ValueError:
        first_prop = len(lines)
    glyph_lines = lines[:first_prop]
    prop_lines = lines[first_prop:]
    if glyph_lines == (YaffParams.empty,):
        glyph_lines = ()
    # new text reader on glyph property lines
    reader = YaffReader()
    for line in prop_lines:
        reader.step(line)
    # ignore in-glyph comments
    props = dict(
        convert_property(cluster)[:2]
        for cluster in reader.get_clusters()
        if cluster.keys
    )
    # labels
    glyph = Glyph(
        glyph_lines, _0=YaffParams.paper, _1=YaffParams.ink,
        labels=keys, comment=comment, **props
    )
    return glyph


def normalise_comment(lines):
    """Remove common single leading space"""
    if all(_line.startswith(' ') for _line in lines if _line):
        return '\n'.join(_line[1:] for _line in lines)
    return '\n'.join(lines)



##############################################################################
##############################################################################
# write file

class YaffWriter(YaffParams):

    def save(self, fonts, outstream):
        """Write fonts to a plaintext stream as yaff."""
        for number, font in enumerate(fonts):
            if len(fonts) > 1:
                outstream.write(BOUNDARY_MARKER + '\n')
            logging.debug('Writing %s to section #%d', font.name, number)
            # write global comment
            if font.get_comment():
                outstream.write(
                    format_comment(font.get_comment(), YaffParams.comment)
                    + '\n\n'
                )
            # we always output name, font-size and spacing
            # plus anything that is different from the default
            props = {
                'name': font.name,
                'spacing': font.spacing,
            }
            if font.spacing in ('character-cell', 'multi-cell'):
                props['cell_size'] = font.cell_size
            else:
                props['bounding_box'] = font.bounding_box
            props.update(font.properties)
            if props:
                # write recognised yaff properties first, in defined order
                for key, value in props.items():
                    self._write_property(outstream, key, value, font.get_comment(key))
                outstream.write('\n')
            for glyph in font.glyphs:
                self._write_glyph(outstream, glyph)

    def _write_glyph(self, outstream, glyph, label=None):
        """Write out a single glyph in text format."""
        # glyph comments
        if glyph.comment:
            outstream.write(
                '\n' + format_comment(glyph.comment, YaffParams.comment) + '\n'
            )
        if label:
            labels = [label]
        else:
            labels = glyph.get_labels()
        if not labels:
            logging.debug('No labels for glyph: %s', glyph)
            outstream.write(f'{YaffParams.separator}\n')
        for _label in labels:
            outstream.write(f'{str(_label)}{YaffParams.separator}\n')
        # glyph matrix
        # empty glyphs are stored as 0x0, not 0xm or nx0
        if not glyph.width or not glyph.height:
            glyphtxt = f'{YaffParams.tab}{YaffParams.empty}\n'
        else:
            glyphtxt = glyph.as_text(
                start=YaffParams.tab,
                ink=YaffParams.ink, paper=YaffParams.paper,
                end='\n'
            )
        outstream.write(glyphtxt)
        if glyph.properties:
            outstream.write(f'\n')
        for key, value in glyph.properties.items():
            self._write_property(outstream, key, value, None, indent=YaffParams.tab)
        if glyph.properties:
            outstream.write('\n')
        outstream.write('\n')

    def _write_property(self, outstream, key, value, comments, indent=''):
        """Write out a property."""
        if value is None:
            return
        # this may use custom string converter (e.g codepoint labels)
        value = str(value)
        # write property comment
        if comments:
            outstream.write(
                f'\n{indent}{format_comment(comments, YaffParams.comment)}\n'
            )
        if not key.startswith('_'):
            key = key.replace('_', '-')
        # write key-value pair
        if '\n' not in value:
            outstream.write(f'{indent}{key}: {self._quote_if_needed(value)}\n')
        else:
            outstream.write(
                f'{indent}{key}:\n{indent}{YaffParams.tab}' + '{}\n'.format(
                    f'\n{indent}{YaffParams.tab}'.join(
                        self._quote_if_needed(_line)
                        for _line in value.splitlines()
                    )
                )
            )

    def _quote_if_needed(self, value):
        """See if string value needs double quotes."""
        value = str(value)
        if (
                (value.startswith('"') and value.endswith('"'))
                # leading or trailing space
                or value[:1].isspace() or value[-1:].isspace()
                # anything that could be mistaken for a glyph
                or all(
                    _c in (YaffParams.ink, YaffParams.paper, YaffParams.empty)
                    for _c in value
                )
            ):
            return f'"{value}"'
        return value


def format_comment(comments, comment_char):
    """Format a multiline comment."""
    return '\n'.join(
        f'{comment_char} {_line}'
        for _line in comments.splitlines()
    )
