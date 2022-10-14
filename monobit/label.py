"""
monobit.label - yaff representation of labels

(c) 2020--2022 Rob Hagemans
licence: https://opensource.org/licenses/MIT
"""

from string import ascii_letters
from binascii import hexlify

from .binary import ceildiv, int_to_bytes
from .scripting import any_int


def is_enclosed(from_str, char):
    """Check if a char occurs on both sides of a string."""
    if not char:
        return True
    return len(from_str) >= 2*len(char) and from_str.startswith(char) and from_str.endswith(char)

def strip_matching(from_str, char, allow_no_match=True):
    """Strip a char from either side of the string if it occurs on both."""
    if not char:
        return from_str
    if is_enclosed(from_str, char):
        clen = len(char)
        return from_str[clen:-clen]
    elif not allow_no_match:
        raise ValueError(f'No matching delimiters `{char}` found in string `{from_str}`.')
    return from_str


def label(value=''):
    """Convert to codepoint/unicode/tag label from Python api or script input."""
    if isinstance(value, Tag):
        return value
    if not isinstance(value, str):
        # only Codepoint can have non-str argument
        return codepoint(value)
    # protect commas, pluses etc. if enclosed
    if is_enclosed(value, '"'):
        return Tag.from_str(value)
    if is_enclosed(value, "'"):
        return char(value)
    try:
        return codepoint(value)
    except ValueError:
        pass
    return char(value)


def label_from_yaff(value):
    """Convert to codepoint/unicode/tag label from yaff file."""
    if not isinstance(value, str):
        raise ValueError(f'label_from_yaff requires a `str` argument, not `{type(value)}`.')
    if not value:
        raise ValueError(f'label_from_yaff requires a non-empty argument.')
    # protect commas, pluses etc. if enclosed
    if is_enclosed(value, '"'):
        return Tag.from_str(value)
    if is_enclosed(value, "'"):
        return char(value)
    # codepoints start with an ascii digit
    try:
        return codepoint(value)
    except ValueError:
        pass
    # length-one -> always a character
    if len(value) == 1:
        return char(value)
    # non-ascii first char -> always a character
    # note that this includes non-printables such as controls but these should not be used.
    if ord(value[0]) >= 0x80:
        return char(value)
    # deal with other options such as single-quoted, u+codepoint and sequences
    try:
        return char_from_yaff(value)
    except ValueError:
        pass
    return Tag.from_str(value)

def label_to_yaff(value):
    """Convert to codepoint/unicode/tag label from yaff file."""
    if isinstance(value, Tag):
        return str(value)
    if isinstance(value, str):
        return char_to_yaff(value)
    if isinstance(value, bytes):
        return codepoint_to_str(value)
    raise ValueError(f'Value `{value}` of type`{type(value)}` is not a label.')


##############################################################################
# tags

class Tag:
    """Tag label."""

    def __init__(self, value=''):
        """Construct tag object."""
        if isinstance(value, Tag):
            self._value = value.value
            return
        if Tag is None:
            tag = ''
        if not isinstance(value, str):
            raise ValueError(
                f'Cannot convert value {repr(value)} of type {type(value)} to tag.'
            )
        # remove leading and trailing whitespace
        value = value.strip()
        # strip matching double quotes - this allows to set a label starting with a digit by quoting it
        value = strip_matching(value, '"')
        self._value = value

    def __repr__(self):
        """Represent label."""
        return f"{type(self).__name__}({repr(self._value)})"

    def __str__(self):
        """Convert tag to str."""
        # quote otherwise ambiguous/illegal tags
        if (
                len(self._value) < 2
                or ord(self._value[0]) >= 0x80
                or '+' in self._value
                or not (self._value[0] in ascii_letters)
                or (self._value.startswith('"') and self._value.endswith('"'))
                or (self._value.startswith("'") and self._value.endswith("'"))
            ):
            return f'"{self._value}"'
        return self._value

    def __hash__(self):
        """Allow use as dictionary key."""
        # make sure tag and Char don't collide
        return hash((type(self), self._value))

    def __eq__(self, other):
        return type(self) == type(other) and self._value == other.value

    def __bool__(self):
        return bool(self._value)

    def __len__(self):
        return len(self._value)

    def __iter__(self):
        return iter(self._value)

    @classmethod
    def from_str(cls, value):
        """Create label from string representation."""
        return cls(value)

    @property
    def value(self):
        """Value of the codepoint in base type."""
        # pylint: disable=no-member
        return self._value


##############################################################################
# codepoints


#FIXME: we're always assuming codepage byte width 1
def codepoint(value=None):
    """Convert to codepoint label if possible."""
    if value is None:
        return b''
    if isinstance(value, bytes):
        return strip_codepoint(value)
    if isinstance(value, int):
        return strip_codepoint(int_to_bytes(value))
    if isinstance(value, str):
        # handle composite labels
        # codepoint sequences (MBCS) "0xf5,0x02" etc.
        value = value.split(',')
    # deal with other iterables, e.g. bytes
    try:
        value = b''.join(int_to_bytes(any_int(_i)) for _i in value)
    except (TypeError, OverflowError):
        raise ValueError(
            f'Cannot convert value {repr(value)} of type {type(value)} to codepoint label.'
        ) from None
    return strip_codepoint(value)

def strip_codepoint(value):
    if len(value) > 1:
        value = value.lstrip(b'\0')
    return value


def codepoint_to_str(value):
    """Convert codepoint label to str."""
    return '0x' + hexlify(value).decode('ascii')


##############################################################################
# character labels

def char(value=''):
    """Convert char or char sequence to char label."""
    if value is None:
        return ''
    #FIXME: this will keep stripping if we pass through char() multiple times
    # char() should be idempotent - we need a marker for that, subclass str?
    if isinstance(value, str):
        # strip matching single quotes - if the character label should be literally '', use ''''.
        return strip_matching(value, "'")
    raise ValueError(
        f'Cannot convert value {repr(value)} of type {type(value)} to character label.'
    )


def char_to_yaff(value):
    """Convert to unicode label str for yaff."""
    return ', '.join(
        f'u+{ord(_uc):04x}'
        for _uc in value
    )

def char_from_yaff(value):
    """Convert u+XXXX string to unicode label. May be empty, representing no glyph."""
    # protect commas, pluses etc. if enclosed
    if is_enclosed(value, "'"):
        return char(value)
    # unicode sequences
    try:
        elements = value.split(',')
        return ''.join(_convert_char_element(_elem) for _elem in elements if _elem)
    except (AttributeError, ValueError):
        raise ValueError(
            f'Cannot convert value {repr(value)} of type {type(value)} to character label.'
        ) from None

def _convert_char_element(element):
    """Convert character label element to char if possible."""
    # string delimited by single quotes denotes a character or sequence
    try:
        element = strip_matching(element, "'", allow_no_match=False)
    except ValueError:
        pass
    else:
        return element
    # not a delimited char
    element = element.lower()
    if not element.startswith('u+'):
        raise ValueError(element)
    # convert to sequence of chars
    # this will raise ValueError if not possible
    cp_ord = int(element.strip()[2:], 16)
    return chr(cp_ord)

