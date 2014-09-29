#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2014 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
##
##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with this program.  If not, see <http://www.gnu.org/licenses/>.
# pylint: disable=W0142,C0103

"""

Module with various utility functions.
Most of these originate from RsEnvironment module.


"""


def gen_trimmed_lines(lines, commentchar='#', commentmidchar=None):
    """
    Returns non-empty, non-comment lines.
    commentchar (default='#') defines a character that is used to denote a comment in a line:
        # This is a note.
    commentmidchar can be used to define a 'mid-line' comment.
        data = value # Here is a 'midline comment' about data or value.
    commentmidchar defaults to the same as commentchar.
    Set commentchar to False (not None) to disable "midline comments".
    """
    if commentmidchar is None:
        commentmidchar = commentchar
    return gen_stripped_nonempty_lines(gen_noncomments_lines(lines,
                                 firstchar=commentchar, midchar=commentchar))


def gen_stripped_nonempty_lines(lines):
    """
    Returns a generator of stripped, nonempty lines in <lines>.
    Args:
        lines : an iterator of string-like objects.
    """
    stripped = (line.strip() for line in lines)
    nonempty = (line for line in stripped if line)
    return nonempty

def gen_noncomments_lines(lines, firstchar='#', midchar=None):
    """
    Returns a generator of lines that does not begin with firstchar.
    If midchar is provided, that is used to remove the part of the line to the right of that.
    """
    noncomment = (line for line in lines if line[0] != firstchar)
    if midchar:
        noncomment = (line.split(midchar, 1)[0] for line in noncomment)
    return noncomment



def trimmed_lines_from_file(filepath, commentchar='#', commentmidchar=None):
    """
    Reads all non-comment parts of non-empty lines from file <filepath>,
    and returns these as a list, closing the file after loading the lines.
    See textdata_util.gen_trimmed_lines doc for info on commenchar and commentmidchar.
    """
    with open(filepath) as fd:
        trimmed_lines = list(gen_trimmed_lines(fd, commentchar, commentmidchar))
    return trimmed_lines
