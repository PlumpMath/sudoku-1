# -*- coding: utf-8 -*-
"""
@author: Patrick K. O'Brien

Hosted at https://github.com/pkobrien/sudoku

An object-oriented treatment of Peter Norvig's paper and
function-based code from http://norvig.com/sudoku.html.

And then I added functions back, but with improvements.

And then the classes became all about supporting GUIs, such as
the PyQt QML one at: https://github.com/pkobrien/qml-sudoku
"""

import random

__version__ = '1.0.0'


#==============================================================================
# Module constants (and some helper functions to calculate said constants)
#==============================================================================


DIGITS = {'1', '2', '3', '4', '5', '6', '7', '8', '9'}

VALID_GRID_CHARS = DIGITS.union({'0', '.'})

ROWS = [range(i, i + 9) for i in range(0, 81, 9)]

COLUMNS = [range(i, i + 81, 9) for i in range(9)]

BOXES = [sum([list(range(i + 9*x, i + 9*x + 3)) for x in range(3)], [])
         for i in sum([list(range(z*27, z*27 + 9, 3)) for z in range(3)], [])]


def row_indices(i):
    """Return list of grid index values for squares in the same row as i.

    So if i is 3 its row indices are [0, 1, 2, 3, 4, 5, 6, 7, 8].
    """
    start = i - i % 9
    return list(range(start, start + 9))


def column_indices(i):
    """Return list of grid index values for squares in the same column as i.

    So if i is 3 its column indices are [3, 12, 21, 30, 39, 48, 57, 66, 75].
    """
    start = i % 9
    return list(range(start, start + 81, 9))


def box_indices(i):
    """Return list of grid index values for squares in the same box as i.

    So if i is 3 its box indices are [3, 4, 5, 12, 13, 14, 21, 22, 23].
    """
    start = 27 * (i // 27) + 3 * ((i % 9) // 3)
    return sum([list(range(start + 9*y, start + 9*y + 3)) 
               for y in range(3)], [])


def peer_indices(i):
    """Return set of grid index values for peers of the square at i.

    Every square has 20 peers.
    So if i is 3 its peers are {0, 1, 2, 4, 5, 6, 7, 8, 12, 13, 14,
                                21, 22, 23, 30, 39, 48, 57, 66, 75}.
    """
    return (set.union(set(row_indices(i)),
                      set(column_indices(i)),
                      set(box_indices(i))
                      ) - {i})


def unit_indices(i):
    """Return (row_indices, column_indices, box_indices) for square at i."""
    return row_indices(i), column_indices(i), box_indices(i)


PEERS = [peer_indices(i) for i in range(81)]

UNITS = [unit_indices(i) for i in range(81)]


#==============================================================================
# Public API
#==============================================================================


def display(grid):
    """Print grid in a readable format."""
    print(formatted(grid))


def formatted(grid):
    """Return grid in a readable format."""
    grid = normalize(grid)
    width = 2
    border = '+'.join(['-' * (1 + (width * 3))] * 3)
    lines = []
    rows = [grid[n:n+9] for n in range(0, 81, 9)]
    for n, row in enumerate(rows):
        line = ' ' + ''.join(
            row[n2].center(width) + ('| ' if n2 in (2, 5) else '')
            for n2 in range(9))
        lines.append(line)
        if n in (2, 5):
            lines.append(border)
    return '\n' + '\n'.join(lines) + '\n'


def is_valid(grid):
    """Return true if grid has no duplicate values within a unit.

    Does not guarantee that grid can be solved."""
    grid = normalize(grid)
    units = ROWS + COLUMNS + BOXES
    for unit in units:
        values = [grid[i] for i in unit if grid[i] != '.']
        if len(values) != len(set(values)):
            return False
    return True


def normalize(grid):
    """Return 81 character string of digits (with dots for missing values)."""
    normalized = ''.join([c for c in grid if c in VALID_GRID_CHARS])
    normalized = normalized.replace('0', '.')
    if len(normalized) != 81:
        raise ValueError('Grid is not a proper text representation.')
    return normalized


def random_grid(min_assigned_squares=26, symmetrical=True):
    """Return a random (grid, solution) pair.

    Assign a minimum of 17 to a maximum of 80 squares.
    Assigning less than 26 squares can take a long time."""
    result = False
    while not result:
        # Failed to setup a single-solution grid, so try again.
        result = _random_grid(min_assigned_squares, symmetrical)
    return result


def solve(grid):
    """Generate all possible solutions for a solveable grid."""
    grid = normalize(grid)
    if not is_valid(grid):
        # We can't solve an invalid grid.
        return
    grid_map = _grid_map_propogated(grid)
    if not grid_map:
        # Although the grid was valid, it wasn't well-formed.
        return
    for solved_grid_map in _solve(grid_map):
        yield _to_grid(solved_grid_map)


#==============================================================================
# Private API
#==============================================================================


def _assign(grid_map, i, digit):
    """Assign digit to grid_map[i] and eliminate from peers."""
    digits_to_eliminate = grid_map[i].replace(digit, '')
    if all(_eliminate(grid_map, i, d2) for d2 in digits_to_eliminate):
        return grid_map
    else:
        return False


def _eliminate(grid_map, i, digit):
    """Eliminate digit from possible digits for square at grid_map[i]."""
    possible_digits = grid_map[i]
    if digit not in possible_digits:
        return grid_map
    possible_digits = possible_digits.replace(digit, '')
    grid_map[i] = possible_digits
    if len(possible_digits) == 0:
        # We just eliminated the only possible digit for the square.
        # That means we don't have a well-formed grid.
        return False
    elif len(possible_digits) == 1:
        # This square is now the only square that can have this digit
        # so eliminate this digit from all of the square's peers.
        if not all(_eliminate(grid_map, peer, possible_digits)
                   for peer in PEERS[i]):
            return False
    for unit in UNITS[i]:
        # Check each of the square's units to see if there is now
        # only one place where this digit can be assigned and do it.
        places = [i2 for i2 in unit if digit in grid_map[i2]]
        if len(places) == 0:
            return False
        elif len(places) == 1:
            if not _assign(grid_map, places[0], digit):
                return False
    return grid_map


def _grid_map_all_digits():
    """Return dictionary of {i: string_of_all_digits} pairs."""
    string_of_all_digits = ''.join(DIGITS)
    return {i: string_of_all_digits for i in range(81)}


def _grid_map_propogated(grid):
    """Return dictionary of {i: possible_digits} pairs."""
    grid_map = _grid_map_all_digits()
    for i, digit in enumerate(grid):
        if digit in DIGITS and not _assign(grid_map, i, digit):
            return False
    return grid_map


def _random_grid(min_assigned_squares, symmetrical):
    """Return a random (grid, solution) pair, or False if failed."""
    min_assigned_squares = max(min_assigned_squares, 17)
    min_assigned_squares = min(min_assigned_squares, 80)
    min_unique_digits = 8
    grid_map = _grid_map_all_digits()
    mirror = list(reversed(range(81)))
    assigned_squares = []
    for i in _shuffled(range(81)):
        if i in assigned_squares:
            # Already assigned earlier as a mirror for symmetry.
            continue
        if not _assign(grid_map, i, random.choice(grid_map[i])):
            break
        assigned_squares.append(i)
        if symmetrical:
            # Assign a value to the mirror square as well.
            other_i = mirror[i]
            if other_i != i:
                if not _assign(grid_map, other_i,
                               random.choice(grid_map[other_i])):
                    break
                assigned_squares.append(other_i)
        unique_digits = {grid_map[i] for i in assigned_squares}
        if (len(assigned_squares) >= min_assigned_squares and
                len(unique_digits) >= min_unique_digits):
            # Sudoku requires a grid with one and only one solution.
            count = 0
            for solved_grid_map in _solve(grid_map):
                count += 1
                if count > 1:
                    break
            if not count == 1:
                # No solution or more than one solution.
                break
            unassigned_squares = set(range(81)) - set(assigned_squares)
            grid = _to_grid(grid_map, unassigned_squares)
            solution = _to_grid(solved_grid_map)
            return grid, solution
    # Failed to setup a single-solution grid.
    return False


def _shuffled(iterable):
    """Return shuffled copy of iterable as a list."""
    l = list(iterable)
    random.shuffle(l)
    return l


def _solve(grid_map):
    """Generate all possible solved versions of grid_map using brute force."""
    if not grid_map:
        return
    if all(len(grid_map[i]) == 1 for i in range(81)):
        yield grid_map
        return
    next_i = min((len(grid_map[i]), i) for i in range(81)
                 if len(grid_map[i]) > 1)[1]
    possible_digits = grid_map[next_i]
    for digit in possible_digits:
        for solved_grid_map in _solve(_assign(grid_map.copy(), next_i, digit)):
            yield solved_grid_map


def _to_grid(grid_map, unassigned_squares=[]):
    """Return grid string for a grid_map dictionary.

    Use a dot for an unassigned square, rather than its propogated value."""
    return ''.join(grid_map[i]
                   if len(grid_map[i]) == 1
                   and i not in unassigned_squares else '.'
                   for i in range(81))


#==============================================================================
# And now for something completely different: Python Classes
#==============================================================================


class Puzzle(object):
    """Puzzle class."""

    def __init__(self):
        """Create a Puzzle instance."""
        self.boxes = []
        self.columns = []
        self.rows = []
        self.squares = []
        self.mirror = {}
        self.box_finder = {}
        self._setup()

    def _setup(self):
        """Setup all the puzzle pieces."""
        sizer = range(9)
        triples = [sizer[0:3], sizer[3:6], sizer[6:9]]
        boxing = [(rs, cs) for rs in triples for cs in triples]
        for nb, (rs, cs) in enumerate(boxing):
            self.box_finder.update({(nr, nc): nb for nr in rs for nc in cs})
        for n in sizer:
            num = n + 1
            self.rows.append(Row(num))
            self.columns.append(Column(num))
            self.boxes.append(Box(num))
        num = 0
        for nr in sizer:
            row = self.rows[nr]
            for nc in sizer:
                column = self.columns[nc]
                box = self.boxes[self.box_finder[(nr, nc)]]
                num += 1
                self.squares.append(Square(num, self, row, column, box))
        self.mirror = dict(zip(self.squares, reversed(self.squares)))
        for square in self.squares:
            square._setup_peers()

    @property
    def assigned_digits(self):
        """Return set of digits that have been successfully assigned."""
        return {square.current_value for square in self.squares
                if square.was_assigned}

    @property
    def assigned_squares(self):
        """Return list of squares with assigned values."""
        return [square for square in self.squares if square.was_assigned]

    @property
    def assigned_grid(self):
        """Return the assigned grid as an 81 character string."""
        return ''.join(square.current_value
                       if square.current_value and square.was_assigned else '.'
                       for square in self.squares)

    @property
    def current_grid(self):
        """Return the current grid as an 81 character string."""
        return ''.join(square.current_value
                       if square.current_value else '.'
                       for square in self.squares)

    @property
    def solved_grid(self):
        """Return the solved grid as an 81 character string."""
        return ''.join(square.solved_value
                       if square.solved_value else '.'
                       for square in self.squares)

    @property
    def is_solved(self):
        """Return True if all squares have been solved."""
        return all(square.is_solved for square in self.squares)

    def reset(self):
        """Reset the puzzle back to a clean slate."""
        for square in self.squares:
            square._reset()

    def setup_random_grid(self, min_assigned_squares=40, symmetrical=True):
        """Setup random grid with a min of 26 to a max of 80 squares assigned.

        Processing less than 26 assigned squares can take a long time."""
        self.reset()
        min_assigned_squares = max(min_assigned_squares, 26)
        grid, solution = random_grid(min_assigned_squares, symmetrical)
        for i, square in enumerate(self.squares):
            square.solved_value = solution[i]
            if grid[i] != '.':
                square._assign(grid[i])


class Unit(object):
    """Parent class for Row, Column and Box."""

    def __init__(self, number):
        self.number = number
        self.name = str(number)
        self.squares = []

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.number)


class Row(Unit):
    pass


class Column(Unit):
    pass


class Box(Unit):
    pass


class Signal(object):
    """Notifies connected slots when emit() is called."""

    def __init__(self):
        self._slots = set()

    def emit(self, *args, **kwargs):
        """Call all connected slots."""
        for slot in self._slots:
            slot(*args, **kwargs)

    def connect(self, slot):
        """Add slot to set of connected slots."""
        self._slots.add(slot)

    def disconnect(self, slot):
        """Remove slot from set of connected slots, if it is a member."""
        self._slots.discard(slot)


class Square(object):
    """Square class."""

    def __init__(self, number, puzzle, row, column, box):
        """Create a Square instance."""
        self.number = number
        self.name = str(number)
        self.puzzle = puzzle
        self.row = row
        self.column = column
        self.box = box
        row.squares.append(self)
        column.squares.append(self)
        box.squares.append(self)
        self.peers = set()
        self.possible_digits = DIGITS
        self.current_value = None
        self.solved_value = None
        self.was_assigned = False
        self.possible_digits_changed = Signal()

    def __repr__(self):
        return '<Square %s @ Row:%s Col:%s Digit(s):%s>' % (
            self.name, self.row.number, self.column.number,
            ''.join(self.possible_digits))

    @property
    def is_solved(self):
        """Return True if square has been solved."""
        return (self.current_value == self.solved_value and
                self.solved_value is not None)

    def update(self, digit):
        """Update square with the value of digit."""
        if self.was_assigned:
            raise SquareUpdateError(
                'Cannot update a square whose value was asssigned')
        self._update(digit)

    def _assign(self, digit):
        """Assign digit to square."""
        self._update(digit)
        self.was_assigned = True

    def _assign_random_digit(self):
        """Assign random digit from possible digits for the square."""
        self._assign(random.choice(self.possible_digits))

    def _update(self, digit):
        """Update square with the value of digit."""
        if digit:
            self.current_value = digit
        else:
            self.current_value = None
        self._update_possible_digits()
        for peer in self.peers:
            peer._update_possible_digits()

    def _reset(self):
        """Reset the square back to a clean slate."""
        self.possible_digits = DIGITS
        self.current_value = None
        self.solved_value = None
        self.was_assigned = False

    def _setup_peers(self):
        """Determine the set of squares that are peers of this square."""
        others = self.row.squares + self.column.squares + self.box.squares
        self.peers = set(others) - {self}

    def _update_possible_digits(self):
        """Recalculate the possible digits for this square."""
        if self.current_value:
            self.possible_digits = {self.current_value}
        else:
            peer_digits = {peer.current_value for peer in self.peers}
            self.possible_digits = DIGITS - peer_digits
        self.possible_digits_changed.emit()


class SquareUpdateError(Exception):
    """Cannot update a square whose value was assigned."""
    pass
