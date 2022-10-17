#!/usr/bin/env python3
"""
Apply operation to bitmap font
(c) 2019--2022 Rob Hagemans, licence: https://opensource.org/licenses/MIT
"""

import sys
import logging
from types import SimpleNamespace as Namespace
from pathlib import Path

import monobit
from monobit.scripting import main, parse_subcommands, print_option_help


operations = {
    'load': monobit.load,
    'save': monobit.save,
    'to': monobit.save,
    **monobit.operations
}

global_options = {
    'help': (bool, 'Print a help message and exit.'),
    'version': (bool, 'Show monobit version and exit.'),
    'debug': (bool, 'Enable debugging output.'),
}

usage = (
    f'usage: {Path(__file__).name} '
    + '[INFILE] [LOAD-OPTIONS] '
    + ' '.join(f'[--{_op}]' for _op in global_options)
    + ' [COMMAND [OPTION...]] ...'
    + ' [to [OUTFILE] [SAVE_OPTIONS]]'
)


HELP_TAB = 25

def print_help(usage, operations, global_options):
    print(usage)
    print()
    print('Options')
    print('=======')
    print()
    for name, (vartype, doc) in global_options.items():
        print_option_help(name, vartype, doc, HELP_TAB, add_unsetter=False)

    print()
    print('Commands and their options')
    print('==========================')
    print()
    for op, func in operations.items():
        if op == 'to':
            continue
        print(f'{op} '.ljust(HELP_TAB-1, '-') + f' {func.script_args.doc}')
        for name, vartype in func.script_args._script_args.items():
            doc = func.script_args._script_docs.get(name, '').strip()
            print_option_help(name, vartype, doc, HELP_TAB)
        print()
        if op == 'load' and op in sys.argv[1:]:
            infile = sys.argv[sys.argv.index('load')+1]
            func = monobit.loaders.get_for_location(infile) #format=load_args.format
            for name, vartype in func.script_args._script_args.items():
                doc = func.script_args._script_docs.get(name, '').strip()
                print_option_help(name, vartype, doc, HELP_TAB)
            print()


command_args, global_args = parse_subcommands(operations, global_options=global_options)


debug = 'debug' in global_args.kwargs
if debug:
    loglevel = logging.DEBUG
else:
    loglevel = logging.WARNING
logging.basicConfig(level=loglevel, format='%(levelname)s: %(message)s')


with main(debug):

    # only global kwargs or nothing preceding a load command
    if len(command_args) > 1 and (
            command_args[0].command == command_args[1].command == 'load'
            and not command_args[0].args and not command_args[0].kwargs
        ):
        logging.debug('Dropping empty first command followed by `load`')
        command_args.pop(0)

    if 'help' in global_args.kwargs:
        print_help(usage, operations, global_options)

    elif 'version' in global_args.kwargs:
        print(f'monobit v{monobit.__version__}')

    else:
        fonts = []
        for args in command_args:
            operation = operations[args.command]
            if operation == monobit.load:
                fonts += operation(*args.args, **args.kwargs)
            elif operation == monobit.save:
                operation(fonts, *args.args, **args.kwargs)
            else:
                fonts = tuple(
                    operation(_font, *args.args, **args.kwargs)
                    for _font in fonts
                )

