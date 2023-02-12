"""
monobit.magic - file type recognition

(c) 2019--2023 Rob Hagemans
licence: https://opensource.org/licenses/MIT
"""

import logging
from pathlib import Path

from .streams import get_name


# number of bytes to read to check if something looks like text
_TEXT_SAMPLE_SIZE = 256
# bytes not expected in (modern) text files
_NON_TEXT_BYTES = (
    # C0 controls except HT, LF, CR
    tuple(range(9)) + (11, 12,) + tuple(range(14, 32))
    # also check for F8-FF which shouldn't occur in utf-8 text
    + tuple(range(0xf8, 0x100))
    # we don't currently parse text formats that need the latin-1 range:
    # - yaff is utf-8 excluding controls
    # - bdf, bmfont are printable ascii [0x20--0x7e] plus 0x0a, 0x0d
    # - hex, draw have undefined range, but we can assume ascii or utf-8
)


class FileFormatError(Exception):
    """Incorrect file format."""


def normalise_suffix(suffix):
    """Bring suffix to lowercase without dot."""
    if suffix.startswith('.'):
        suffix = suffix[1:]
    return suffix.lower()

def get_suffix(file):
    """Get normalised suffix for file or path."""
    if isinstance(file, (str, Path)):
        suffix = Path(file).suffix
    else:
        suffix = Path(get_name(file)).suffix
    return normalise_suffix(suffix)

def maybe_text(instream):
    """
    Check if a binary input stream looks a bit like it might hold utf-8 text.
    Currently just checks for unexpected bytes in a short sample.
    """
    if instream.mode == 'w':
        # output binary streams *could* hold text
        # (this is not about the file type, but about the content)
        return True
    try:
        sample = instream.peek(_TEXT_SAMPLE_SIZE)
    except EnvironmentError:
        return None
    if set(sample) & set(_NON_TEXT_BYTES):
        logging.debug(
            'Found unexpected bytes: identifying unknown input stream as binary.'
        )
        return False
    try:
        sample.decode('utf-8')
    except UnicodeDecodeError as err:
        # need to ensure we ignore errors due to clipping inside a utf-8 sequence
        if err.reason != 'unexpected end of data':
            logging.debug(
                'Found non-UTF8: identifying unknown input stream as binary.'
            )
            return False
    logging.debug('Tentatively identifying unknown input stream as text.')
    return True


class MagicRegistry:
    """Registry of file types and their magic sequences."""

    def __init__(self):
        """Set up registry."""
        self._magic = []
        self._suffixes = {}
        self._names = {}

    def register(self, *suffixes, name='', magic=()):
        """Decorator to register converter for file type."""
        def decorator(converter):
            if not name:
                raise ValueError('No registration name given')
            if name in self._names:
                raise ValueError('Registration name `{name} already in use')
            self._names[name] = converter
            for suffix in suffixes:
                suffix = normalise_suffix(suffix)
                if suffix in self._suffixes:
                    self._suffixes[suffix].append(converter)
                else:
                    self._suffixes[suffix] = [converter]
            for sequence in magic:
                self._magic.append((Magic(sequence), converter))
            # sort the magic registry long to short to manage conflicts
            self._magic = list(sorted(
                    self._magic,
                    key=lambda _i:len(_i[0]), reverse=True
                )
            )
            # use first suffix given as standard
            if suffixes:
                converter.format = normalise_suffix(suffixes[0])
            return converter
        return decorator

    def identify(self, file):
        """Identify a type from magic sequence on input file."""
        if not file:
            return ()
        matches = []
        # can't read magic on write-only file
        if not isinstance(file, (str, Path)):
            for magic, converter in self._magic:
                if magic.fits(file):
                    logging.debug(
                        'Stream matches signature for format `%s`.',
                        converter.name
                    )
                    matches.append(converter)
        suffix = get_suffix(file)
        converters = self._suffixes.get(suffix, ())
        # don't repeat matches
        converters = [_c for _c in converters if _c not in matches]
        for converter in converters:
            logging.debug(
                'Filename matches pattern for format `%s`.',
                converter.name
            )
        matches.extend(converters)
        return tuple(matches)


class Magic:
    """Define and match against bytes mask."""

    def __init__(self, value, offset=0):
        """Initialise bytes mask from bytes or Magic object."""
        if isinstance(value, Magic):
            self._mask = tuple(
                (_item[0] + offset, _item[1])
                for _item in  value._mask
            )
        elif not isinstance(value, bytes):
            raise TypeError(
                'Initialiser must be bytes or Magic,'
                f' not {type(value).__name__}'
            )
        else:
            self._mask = ((offset, value),)

    def __len__(self):
        """Mask length."""
        return max(_item[0] + len(_item[1]) for _item in self._mask)

    def __add__(self, other):
        """Concatenate masks."""
        other = Magic(other, offset=len(self))
        new = Magic(self)
        new._mask += other._mask
        return new

    def __radd__(self, other):
        """Concatenate masks."""
        other = Magic(other)
        return other + self

    def matches(self, target):
        """Target bytes match the mask."""
        if len(target) < len(self):
            logging.debug(f'Target of insufficient length: {target}')
            return False
        for offset, value in self._mask:
            if target[offset:offset+len(value)] != value:
                return False
        return True

    def fits(self, instream):
        """Binary stream matches the signature."""
        if instream.mode == 'w':
            return False
        return self.matches(instream.peek(len(self)))

    @classmethod
    def offset(cls, offset=0):
        """Represent offset in concatenated mask."""
        return cls(value=b'', offset=offset)
