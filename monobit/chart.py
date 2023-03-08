"""
monobit.chart - create font chart

(c) 2019--2023 Rob Hagemans
licence: https://opensource.org/licenses/MIT
"""

from itertools import product

from .renderer import Canvas
from .binary import ceildiv
from .properties import Props
from .basetypes import Coord

def chart(
        font,
        columns=32, margin=(0, 0), padding=(0, 0),
        order='row-major', direction=(1, -1),
    ):
    """Create font chart matrix."""
    glyph_map, width, height = grid_map(
        font, columns, margin, padding, order, direction,
    )
    canvas = Canvas.blank(width, height)
    for entry in glyph_map:
        canvas.blit(entry.glyph, entry.x, entry.y, operator=max)
    return canvas


def grid_map(
        font,
        columns=32, margin=(0, 0), padding=(0, 0),
        order='row-major', direction=(1, -1),
    ):
    """Create glyph map for font chart matrix."""
    font = font.equalise_horizontal()
    padding_x, padding_y = padding
    margin_x, margin_y = margin
    # work out image geometry
    step_x = font.raster_size.x + padding_x
    step_y = font.raster_size.y + padding_y
    rows = ceildiv(len(font.glyphs), columns)
    # output glyph map
    traverse = grid_traverser(columns, rows, order, direction)
    glyph_map = tuple(
        Props(
            glyph=_glyph, sheet=0,
            x=margin_x + col*step_x, y=margin_y + row*step_y,
        )
        for _glyph, (row, col) in zip(font.glyphs, traverse)
    )
    # determine image geometry
    width = columns * step_x + 2 * margin_x - padding_x
    height = rows * step_y + 2 * margin_y - padding_y
    return glyph_map, width, height


def traverse_chart(columns, rows, order, direction):
    """Traverse a glyph chart in the specified order and directions."""
    return tuple(grid_traverser(columns, rows, order, direction))

def grid_traverser(columns, rows, order, direction):
    """Traverse a glyph chart in the specified order and directions."""
    dir_x, dir_y = direction
    if not dir_x or not dir_y:
        raise ValueError('direction values must not be 0.')
    if dir_x > 0:
        x_traverse = range(columns)
    else:
        x_traverse = range(columns-1, -1, -1)
    if dir_y > 0:
        y_traverse = range(rows)
    else:
        y_traverse = range(rows-1, -1, -1)
    if order.startswith('r'):
        return product(y_traverse, x_traverse)
    elif order.startswith('c'):
        return product(x_traverse, y_traverse)
    raise ValueError(f'order should start with one of `r`, `c`, not `{order}`.')
