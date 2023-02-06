"""
monobit.storage - load and save fonts

(c) 2019--2023 Rob Hagemans
licence: https://opensource.org/licenses/MIT
"""

import sys
import logging
from pathlib import Path
from contextlib import contextmanager

from .constants import VERSION, CONVERTER_NAME
from .font import Font
from .pack import Pack
from .streams import Stream, StreamBase, KeepOpen
from .magic import MagicRegistry, FileFormatError, maybe_text
from .scripting import scriptable, ScriptArgs, ARG_PREFIX
from .basetypes import Any


DEFAULT_TEXT_FORMAT = 'yaff'
DEFAULT_BINARY_FORMAT = 'raw'


@contextmanager
def open_location(file, mode, overwrite=False):
    """Parse file specification, open stream."""
    # enclosing container is stream.where
    if mode not in ('r', 'w'):
        raise ValueError(f"Unsupported mode '{mode}'.")
    if not file:
        raise ValueError(f'No location provided.')
    if isinstance(file, str):
        file = Path(file)
    # interpret incomplete arguments
    if isinstance(file, Path):
        if file.is_dir():
            # TODO: load all in directory
            raise NotImplementedError
        else:
            container = Directory(file.parent)
            stream = container.open(file.name, mode=mode)
            with stream:
                yield stream
    else:
        if isinstance(file, StreamBase):
            stream = file
        else:
            stream = Stream(KeepOpen(file), mode=mode)
        # we didn't open the file, so we don't own it
        # we neeed KeepOpen for when the yielded object goes out of scope in the caller
        yield stream


##############################################################################
# loading

@scriptable(unknown_args='passthrough', record=False)
def load(infile:Any='', *, format:str='', **kwargs):
    """
    Read font(s) from file.

    infile: input file (default: stdin)
    format: input format (default: infer from magic number or filename)
    """
    infile = infile or sys.stdin
    with open_location(infile, 'r') as stream:
        return load_stream(stream, format, **kwargs)


def load_stream(instream, format='', **kwargs):
    """Load fonts from open stream."""
    # identify file type
    fitting_loaders = loaders.get_for(instream, format=format)
    if not fitting_loaders:
        raise FileFormatError(f'Cannot load from format `{format}`')
    for loader in fitting_loaders:
        instream.seek(0)
        logging.info('Loading `%s` as %s', instream.name, loader.name)
        try:
            where = instream.where
            fonts = loader(instream, where, **kwargs)
        except FileFormatError as e:
            logging.debug(e)
            continue
        if not fonts:
            logging.debug('No fonts found in file.')
            continue
        # convert font or pack to pack
        pack = Pack(fonts)
        # set conversion properties
        filename = Path(instream.name).name
        # if the source filename contains surrogate-escaped non-utf8 bytes
        # preserve the byte values as backslash escapes
        try:
            filename.encode('utf-8')
        except UnicodeError:
            filename = (
                filename.encode('utf-8', 'surrogateescape')
                .decode('ascii', 'backslashreplace')
            )
        return Pack(
            _font.modify(
                converter=CONVERTER_NAME,
                source_format=_font.source_format or loader.name,
                source_name=_font.source_name or filename
            )
            for _font in pack
        )
    raise FileFormatError('No fonts found in file')


##############################################################################
# saving



@scriptable(unknown_args='passthrough', record=False, pack_operation=True)
def save(
        pack_or_font,
        outfile:Any='', *,
        format:str='', overwrite:bool=False,
        **kwargs
    ):
    """
    Write font(s) to file.

    outfile: output file (default: stdout)
    format: font file format
    overwrite: if outfile is a filename, allow overwriting existing file
    """
    pack = Pack(pack_or_font)
    outfile = outfile or sys.stdout
    if outfile == sys.stdout:
        # errors can occur if the strings we write contain surrogates
        # these may come from filesystem names using 'surrogateescape'
        sys.stdout.reconfigure(errors='replace')
    with open_location(outfile, 'w', overwrite=overwrite) as stream:
        save_stream(pack, stream, format, **kwargs)
    return pack_or_font

def save_stream(pack, outstream, format='', **kwargs):
    """Save fonts to an open stream."""
    matching_savers = savers.get_for(outstream, format=format)
    if not matching_savers:
        raise ValueError(f'Format specification `{format}` not recognised')
    if len(matching_savers) > 1:
        raise ValueError(
            f"Format for filename '{outstream.name}' is ambiguous: "
            f'specify -format with one of the values '
            f'({", ".join(_s.name for _s in matching_savers)})'
        )
    saver, *_ = matching_savers
    where = outstream.where
    logging.info('Saving `%s` as %s.', outstream.name, saver.name)
    saver(pack, outstream, where, **kwargs)


##############################################################################
# loader/saver registry

class ConverterRegistry(MagicRegistry):
    """Loader/Saver registry."""

    def __init__(self, func_name):
        """Set up registry and function name."""
        super().__init__()
        self._func_name = func_name

    def get_for_location(self, file, format=''):
        """Get loader/saver for font file location."""
        if not file:
            return self.get_for(format=format)
        with open_location(file) as stream:
            return self.get_for(file, format=format)

    def get_for(self, file=None, format=''):
        """
        Get loader/saver function for this format.
        infile must be a Stream or empty
        """
        converter = ()
        if not format:
            converter = self.identify(file)
        if not converter:
            if format:
                try:
                    converter = (self._names[format],)
                except KeyError:
                    converter = self._suffixes.get(format,  ())
            elif (
                    not file
                    or not file.name or file.name == '<stdout>'
                    or (file.mode == 'r' and maybe_text(file))
                ):
                logging.debug(
                    'Fallback to default `%s` format', DEFAULT_TEXT_FORMAT
                )
                converter = (self._names[DEFAULT_TEXT_FORMAT],)
            elif file.mode == 'r':
                converter = (self._names[DEFAULT_BINARY_FORMAT],)
                logging.debug(
                    'Fallback to default `%s` format', DEFAULT_BINARY_FORMAT
                )
            else:
                if format:
                    msg = f'Format `{format}` not recognised'
                else:
                    msg = 'Could not determine format'
                    if file:
                        msg += f' from file name `{file.name}`'
                    msg += '. Please provide a -format option'
                raise ValueError(msg)
        return converter

    def register(self, *formats, magic=(), name='', linked=None):
        """
        Decorator to register font loader/saver.

        *formats: extensions covered by registered function
        magic: magic sequences covered by the converter (no effect for savers)
        name: name of the format
        linked: loader/saver linked to saver/loader
        """
        register_magic = super().register

        def _decorator(original_func):
            # set script arguments
            funcname = self._func_name
            if name:
                funcname += f' {ARG_PREFIX}format={name}'
            _func = scriptable(
                original_func,
                # use the standard name, not that of the registered function
                name=funcname,
                # don't record history of loading from default format
                record=(DEFAULT_TEXT_FORMAT not in formats),
            )
            # register converter
            if linked:
                linked.linked = _func
                _func.name = name or linked.name
                _func.formats = formats or linked.formats
                _func.magic = magic or linked.magic
            else:
                _func.name = name
                _func.linked = linked
                _func.formats = formats
                _func.magic = magic
            # register magic sequences
            register_magic(*_func.formats, magic=_func.magic, name=_func.name)(_func)
            return _func

        return _decorator


loaders = ConverterRegistry('load')
savers = ConverterRegistry('save')

###############################################################################

import os
import itertools


class Container:
    """Base class for container types."""

    def __init__(self, mode='r', name=''):
        self.mode = mode[:1]
        self.name = name
        self.refcount = 0
        self.closed = False

    def __iter__(self):
        """List contents."""
        raise NotImplementedError

    def __enter__(self):
        # we don't support nesting the same archive
        assert self.refcount == 0
        self.refcount += 1
        logging.debug('Entering archive %r', self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type == BrokenPipeError:
            return True
        logging.debug('Exiting archive %r', self)
        self.close()

    def close(self):
        """Close the archive."""
        self.closed = True

    def open(self, name, mode):
        """Open a binary stream in the container."""
        raise NotImplementedError

    def unused_name(self, stem, suffix):
        """Generate unique name for container file."""
        for i in itertools.count():
            if i:
                filename = '{}.{}.{}'.format(stem, i, suffix)
            else:
                filename = '{}.{}'.format(stem, suffix)
            if filename not in self:
                return filename


def load_all(container, **kwargs):
    """Open container and load all fonts found in it into one pack."""
    format = ''
    logging.info('Reading all from `%s`.', container.name)
    packs = Pack()
    names = list(container)
    for name in container:
        logging.debug('Trying `%s` on `%s`.', name, container.name)
        stream = container.open(name, 'r')
        with stream:
            try:
                pack = load_stream(
                    stream, format=format, **kwargs
                )
            except FileFormatError as exc:
                logging.debug('Could not load `%s`: %s', name, exc)
            else:
                packs += Pack(pack)
    return packs

def save_all(pack, container, **kwargs):
    """Save fonts to a container."""
    suffixes = Path(container.name).suffixes
    if len(suffixes) > 1:
        format = suffixes[-2][1:]
    else:
        format = ''
    logging.info('Writing all to `%s`.', container.name)
    for font in pack:
        # generate unique filename
        name = font.name.replace(' ', '_')
        filename = container.unused_name(name, format)
        stream = container.open(filename, 'w')
        try:
            with stream:
                save_stream(Pack(font), stream, format=format, **kwargs)
        except BrokenPipeError:
            pass
        except FileFormatError as e:
            logging.error('Could not save `%s`: %s', filename, e)


###############################################################################

class Directory(Container):
    """Treat directory tree as a container."""

    def __init__(self, path, mode='r', *, overwrite=False):
        """Create directory wrapper."""
        # if empty path, this refers to the whole filesystem
        if not path:
            path = ''
        elif isinstance(path, Directory):
            self._path = path._path
        else:
            self._path = Path(path)
        # mode really should just be 'r' or 'w'
        mode = mode[:1]
        if mode == 'w':
            logging.debug('Creating directory `%s`', self._path)
            # exist_ok raises FileExistsError only if the *target* already
            # exists, not the parents
            self._path.mkdir(parents=True, exist_ok=overwrite)
        super().__init__(mode, str(self._path))

    def open(self, name, mode):
        """Open a stream in the container."""
        # mode in 'r', 'w'
        mode = mode[:1]
        pathname = Path(name)
        if mode == 'w':
            path = pathname.parent
            logging.debug('Creating directory `%s`', self._path / path)
            (self._path / path).mkdir(parents=True, exist_ok=True)
        logging.debug("Opening file `%s` for mode '%s'.", name, mode)
        file = open(self._path / pathname, mode + 'b')
        # provide name relative to directory container
        stream = Stream(
            file, mode=mode,
            name=str(pathname), overwrite=True,
            where=self,
        )
        return stream

    def __iter__(self):
        """List contents."""
        # don't walk the whole filesystem - no path is no contents
        if not self._path:
            return ()
        return (
            str((Path(_r) / _f).relative_to(self._path))
            for _r, _, _files in os.walk(self._path)
            for _f in _files
        )

    def __contains__(self, name):
        """File exists in container."""
        return (self._path / name).exists()
