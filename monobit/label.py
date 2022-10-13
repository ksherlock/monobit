"""
monobit.label - yaff representation of labels

(c) 2020--2022 Rob Hagemans
licence: https://opensource.org/licenses/MIT
"""

import string
from binascii import hexlify

from .binary import ceildiv, int_to_bytes
from .scripting import any_int


def strip_matching(from_str, char, allow_no_match=True):
    """Strip a char from either side of the string if it occurs on both."""
    if not char:
        return from_str
    clen = len(char)
    if len(from_str) >= 2*clen and from_str.startswith(char) and from_str.endswith(char):
        return from_str[clen:-clen]
    elif not allow_no_match:
        raise ValueError(f'No matching delimiters `{char}` found in string `{from_str}`.')
    return from_str


def label(value=''):
    """Convert to codepoint/unicode/tag label as appropriate."""
    if isinstance(value, Label):
        return value
    if not isinstance(value, str):
        # only Codepoint can have non-str argument
        return codepoint(value)
    try:
        return codepoint(value)
    except ValueError:
        pass
    # check for unicode identifier
    try:
        return Char.from_str(value)
    except ValueError:
        pass
    return Tag.from_str(value)


class Label:
    """Label base class."""

    def __init__(self, value=None):
        """Label base class should not be instantiated."""
        raise NotImplementedError('Cannot create untyped label.')

    @classmethod
    def from_str(cls, value):
        """Create label from string representation."""
        return cls(value)

    @property
    def value(self):
        """Value of the codepoint in base type."""
        # pylint: disable=no-member
        return self._value

    def __hash__(self):
        """Allow use as dictionary key."""
        # make sure tag and Char don't collide
        return hash((type(self), self.value))

    def __eq__(self, other):
        return type(self) == type(other) and self.value == other.value

    def __bool__(self):
        return bool(self.value)

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __repr__(self):
        """Represent label."""
        return f"{type(self).__name__}({repr(self.value)})"


class Tag(Label):
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

    def __str__(self):
        """Convert tag to str."""
        # quote otherwise ambiguous/illegal tags
        if (
                '+' in self._value
                or not (self._value[:1].isalpha() or self._value[:1] in '_-."')
                or (self._value.startswith('"') and self._value.endswith('"'))
                or (self._value.startswith("'") and self._value.endswith("'"))
                # one-character tags - we want to consider representing ascii chars this way
                or len(self._value) == 1
            ):
            return f'"{self._value}"'
        return self._value


#FIXME: we're always assuming codepage byte width 1
def codepoint(value=None):
    """Convert to codepoint label if possible."""
    if value is None:
        return b''
    if isinstance(value, bytes):
        return value
    if isinstance(value, int):
        return int_to_bytes(value)
    if isinstance(value, str):
        # handle composite labels
        # codepoint sequences (MBCS) "0xf5,0x02" etc.
        value = value.split(',')
    # deal with other iterables, e.g. bytes
    try:
        return b''.join(int_to_bytes(any_int(_i)) for _i in value)
    except (TypeError, OverflowError):
        raise ValueError(
            f'Cannot convert value {repr(value)} of type {type(value)} to codepoint label.'
        ) from None


def codepoint_to_str(value):
    """Convert codepoint label to str."""
    return '0x' + hexlify(value).decode('ascii')



class Char(Label):
    """Unicode label."""

    def __init__(self, value=''):
        """Convert char or char sequence to unicode label."""
        if isinstance(value, Char):
            self._value = value.value
            return
        if value is None:
            value = ''
        if isinstance(value, str):
            # Char('x') just holds 'x'
            # strip matching single quotes - if the character label should be literally '', use ''''.
            value = strip_matching(value, "'")
        else:
            # iterable of strings?
            try:
                value = ''.join(value)
            except TypeError:
                raise self._value_error(value) from None
        self._value = value

    def __repr__(self):
        """Represent character label."""
        return f"{type(self).__name__}({ascii(self._value)})"

    def __str__(self):
        """Convert to unicode label str."""
        return ', '.join(
            f'u+{ord(_uc):04x}'
            for _uc in self._value
        )

    @classmethod
    def from_str(cls, value):
        """Convert u+XXXX string to unicode label. May be empty, representing no glyph."""
        if not isinstance(value, str):
            raise cls._value_error(value)
        # codepoint sequences
        elements = value.split(',')
        try:
            chars = [cls._convert_element(_elem) for _elem in elements if _elem]
        except ValueError:
            raise cls._value_error(value) from None
        # convert sequence of chars to str
        return cls(chars)

    @staticmethod
    def _convert_element(element):
        """Convert unicode label element to char if possible."""
        # string delimited by single quotes denotes a character/grapheme sequence
        try:
            element = strip_matching(element, "'", allow_no_match=False)
        except ValueError:
            pass
        else:
            return element
        element = element.lower()
        if not element.startswith('u+'):
            raise ValueError(element)
        # convert to sequence of chars
        # this will raise ValueError if not possible
        cp_ord = int(element.strip()[2:], 16)
        return chr(cp_ord)

    @staticmethod
    def _value_error(value):
        """Create a ValueError."""
        return ValueError(
            f'Cannot convert value {repr(value)} of type {type(value)} to unicode label.'
        )
