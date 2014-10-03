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

import os
import logging

def getfilepath(gelfilepath, otherfilepath):
    """ Ensures that otherfilepath is a proper file path. """
    if os.path.isabs(otherfilepath):
        return otherfilepath
    gelfiledir = os.path.dirname(gelfilepath)
    return os.path.join(gelfiledir, otherfilepath)



def init_logging(argsns=None, prefix="gelutils"):
    """
    Set up standard Labfluence logging system based on values provided by argsns, namely:
    - loglevel
    - logtofile
    - testing

    """

    # Examples of different log formats:
    #logfmt = "%(levelname)s: %(filename)s:%(lineno)s %(funcName)s() > %(message)s"
    #logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    # loguserfmt = format of log displayed to the user; logfilefmt = format of log messages written to logfile.
    loguserfmt = "%(asctime)s %(levelname)-5s %(name)20s:%(lineno)-4s%(funcName)20s() %(message)s"
    #logfilefmt = '%(asctime)s %(levelname)-6s - %(name)s:%(lineno)s - %(funcName)s() - %(message)s'
    logdatefmt = "%Y%m%d-%H:%M:%S" # "%Y%m%d-%Hh%Mm%Ss"
    logtimefmt = "%H:%M:%S" # Output to user in console
    #logfiledir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logs')
    #if not os.path.exists(logfiledir):
    #    os.mkdir(logfiledir)
    #if argsns.logtofile:
    #    logfilepath = argsns.logtofile
    #else:
    #    logfilenameformat = '{}_testing.log' if getattr(argsns, 'testing', False) else '{}_debug.log'
    #    logfilename = logfilenameformat.format(prefix)
    #    logfilepath = os.path.join(logfiledir, logfilename)
    #logging.root.setLevel(logging.DEBUG)
    #logstreamhandler = logging.StreamHandler()
    #logging.root.addHandler(logstreamhandler)
    #logstreamformatter = logging.Formatter(loguserfmt, logtimefmt)
    #logstreamhandler.setFormatter(logstreamformatter)
    logging.basicConfig(level=logging.DEBUG, format=loguserfmt, datefmt=logtimefmt)    # filename='example.log',



def gen_wikilist_entries(lines, listchar='*#-+', commentmidchar=None):
    """
    This is sort of the inverse of gen_trimmed_lines, it returns
    all lines that starts with either '#' or '*',
    corresponding to a enumerated or bullet list in wiki format.
    commentmidchar, if specified, will remove anything to the right of this string, e.g.
    >>> gen_wikilist_entries(("sample (volume)",), firstchar='*#-+', commentmidchar="(")
    ["sample"]
    """
    lines = gen_stripped_nonempty_lines(lines)
    lines = (line[1:].strip().split(listchar)[0] for line in lines if line[0] in listchar)
    return lines




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



def trimmed_lines_from_file(filepath, args=None):
    """
    Reads all non-comment parts of non-empty lines from file <filepath>,
    and returns these as a list, closing the file after loading the lines.
    See textdata_util.gen_trimmed_lines doc for info on commenchar and commentmidchar.
    Wow, I just realized
    """
    if args is None:
        args = {}
    with open(filepath) as fd:
        if args.get('linetrim', None) == 'wikilist':
            # Add arguments to args for convenience to the user:
            args.setdefault('listchar', '*#-+')
            args.setdefault('commentmidchar', None)
            trimmed_lines = gen_wikilist_entries(fd, args['listchar'], args['commentmidchar'])
        else:
            args.setdefault('commentchar', '#')
            args.setdefault('commentmidchar', None)
            trimmed_lines = gen_trimmed_lines(fd, args.get('commentchar', None), args.get('commentmidchar', None))
        lines = list(trimmed_lines)
    return lines
