#!/usr/bin/env python
# -*- coding: utf-8 -*-
#    Copyright 2014 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
# pylint: disable=C0103

"""

Module with various utility functions.
Most of these originate from RsEnvironment module.


"""

import os
import sys
from six import string_types
import codecs
from itertools import chain
import json
import yaml
import logging
import logging.config
logger = logging.getLogger(__name__)


# To override default open method to provide UTF support:
if sys.version_info.major == 2:
    # Note: codecs.open, and Python 2 open builtin, doesn't support all kwargs that python3 open does, e.g. newline.
    def open_utf(fp, mode='r', encoding='utf-8'):
        return codecs.open(fp, mode, encoding=encoding)
else:
    # For python3 use builtin open which natively supports utf-8 and encoding keyword:
    # Note: python3.open() uses locale.getpreferredencoding(False) to determine default encoding!
    open_utf = open


def ensure_numeric(inval, scalefactor=None, sf_lim=2, converter=None):
    """ensure that a given value is numeric.

    Takes a string value or iterable with string values and converts them to absolute values.
    Args:
        :inval:     Input to convert to a numeric value. String or iterable.
        :scalefactor: Scale inval by this factor
        :sf_lim:    Only scale if inval is less than this value (or contains '%').
                    Default sf_lim=2.
        :converter: Apply this function before returning.
                    Default is int(float(val)) IF scalefactor is an integer,
                    ELSE float(val)
    Specialities:
        Both inval and scalefactor can be lists.
        inval can even be a "list-like string":  "0.146, 0.16, 177.8%"  -> [0.146, 0.16, '177.8%']
        If scalefactor is a sequence, it is applied with zip(inval, scalefactor).
    Usage:
        >>> ensure_numeric('33%')
        0.33    (float)
        >>> ensure_numeric('33%', 100)
        33      (int)
        >>> ensure_numeric('1.115', 100, converter=float)
        111.5   (float)
        >>> ensure_numeric('5.12', 5.0, sf_lim=10)
        25.6    (float)
        >>> ensure_numeric(0.33, 100)
        33      (int)
        >>> ensure_numeric(5.12, 5, sf_lim=10)
        51    (int)
        >>> ensure_numeric("0.146, 0.16, 177.8%", [100, 200, 300.0]) # scalefactor as a sequence
        [15, 32, 533.4]   # mixed types
    """
    if converter is None:
        if not (isinstance(scalefactor, (list, tuple)) or hasattr(scalefactor, '__iter__')):
            # Do not infer converter if scalefactor is a sequence:
            converter = (lambda x: int(round(x))) if isinstance(scalefactor, int) else float
    if isinstance(inval, (float, int)):
        outval = scalefactor*inval if scalefactor and inval < sf_lim else inval
        return converter(outval) if converter else outval
    if isinstance(inval, string_types):
        if ', ' in inval:
            # Maybe the user provided inval as a string of values: "left, top, right, lower"
            inval = [item.strip() for item in inval.split(', ')]
            return ensure_numeric(inval, scalefactor, sf_lim, converter)
        outval = float(inval.strip('%'))/100 if '%' in inval else float(inval)
        # Apply scalefactor:
        if scalefactor and (outval < sf_lim or '%' in inval):
            outval = scalefactor*outval
        return converter(outval) if converter else outval
    else:
        # We might have a list/tuple:
        try:
            if isinstance(scalefactor, (list, tuple)) or hasattr(scalefactor, '__iter__'):
                return [ensure_numeric(item, sf, sf_lim, converter) for item, sf in zip(inval, scalefactor)]
            else:
                return [ensure_numeric(item, scalefactor, sf_lim, converter) for item in inval]
        except TypeError:
            logger.warning("Value '%s' not (float, int) and not string_type and not iterable, returning as-is.", inval)
            return inval


def getfilepath(gelfilepath, otherfilepath):
    logger.warning("Using deprechated getfilepath method!")
    return getabsfilepath(gelfilepath, otherfilepath)


def getabsfilepath(gelfilepath, otherfilepath):
    """Try to ensure that otherfilepath is a proper file path.

    Usecases:
    If otherfilepath is 'mygel.png' or 'pngs/mygel.png',
    normal file operation will prefix this with os.getcwd() to get the absolute path.
    However, if os.getcwd() is not equal to os.path.dirname(gelfilepath),
    then otherfilepath is wrong -- it is always assumed relative to gelfilepath.

    getabsfilepath and getrelfilepath are complementary:
    * Assume given filepaths (e.g. in args) are relative to the gelfile.
    * Use getabsfilepath to get the actual filepath.
    * Work with the actual path when doing disk operations.
    * Use getrelfilepath before returning a filepath to the user (or save it to args).

    Expected behavior:

    (a) Only alter otherfilepath if it is relative:
    >>> getabsfilepath('/path/to/mygel.gel', '/another/path/to/mygel.png')
    '/another/path/to/mygel.png'
    >>> getabsfilepath('relative/path/to/mygel.gel', '/another/path/to/mygel.png')
    '/another/path/to/mygel.png'

    (b)
    >>> getabsfilepath('/path/to/mygel.gel', 'mygel.png')
    '/path/to/mygel.png'

    >>> getabsfilepath('/path/to/mygel.gel', 'pngs/mygel.png')
    '/path/to/pngs/mygel.png'

    >>> getabsfilepath('relative/path/to/mygel.gel', '../mygel.png')
    'relative/path/mygel.png'

    """
    if os.path.isabs(otherfilepath) or not gelfilepath:
        # otherfilepath has a directory or is an absolute path
        # unless it is stored in the fs root, this will be the same)
        return otherfilepath
    gelfiledir = os.path.dirname(gelfilepath)
    if gelfiledir:
        # The gelfile does have a directory. Unless you have the following:
        # <cwd>/gels/gelfile.gel
        # <cwd>/annotation.txt
        # Then what you want for 'annotation.txt' is probably 'gels/annotation.txt'
        return os.path.join(gelfiledir, otherfilepath)
    return os.path.normpath(otherfilepath)


def getrelfilepath(gelfilepath, otherfilepath):
    """Get otherfilepath relative to gelfilepath.

    Usecases:
    - Linking to png file in svg rather than embedding data.
    - Returning easy-to-read values to the GUI.

    Expected:
    >>> getrelfilepath('mygel.gel', 'mygel.png')
    'mygel.png'
    >>> getrelfilepath('/tests/testdata/mygel.gel', '/tests/testdata/mygel.png')
    'mygel.png'
    >>> getrelfilepath('/tests/testdata/mygel.gel', '/tests/testdata/pngs/mygel.png')
    'pngs/mygel.png'
    >>> getrelfilepath('/home/myuser/mygel.gel', 'mygel.png')
    'mygel.png'
    >>> getrelfilepath('/home/myuser/mygel.gel', 'pngs/mygel.png')      [for cwd = '/home/myuser']
    'pngs/mygel.png'
    >>> getrelfilepath('/home/myuser/mygel.gel', 'pngs/mygel.png')      [for cwd = '/home/anotheruser']
    '/home/anotheruser/pngs/mygel.png'
    >>> getrelfilepath('/home/myuser/mygel.gel', '/home/myuser/pngs/mygel.png')
    'pngs/mygel.png'
    >>> getrelfilepath('/home/myuser/mygel.gel', '/home/myuser/pngs/mygel.png')
    'pngs/mygel.png'
    """
    # first ensure that both files are absolute. You could also do a lot of "if otherfilepath is not absolute, then...",
    # but this is easier:
    # absgelfilepath, absotherfilepath = [os.path.abspath(p) for p in (gelfilepath, otherfilepath)]
    # common = os.path.commonprefix(absgelfilepath, absotherfilepath)
    # This might be really awkward if len(common)
    # relpath = absotherfilepath[len(common)+1]
    # os.path.relpath can do what I want:
    geldirpath = os.path.dirname(gelfilepath)
    return os.path.relpath(otherfilepath, start=geldirpath)


def printdict(d):
    """Returns a string of d with sorted keys."""
    try:
        return "{" + ", ".join("{}: {}".format(repr(k), repr(v)) for k, v in sorted(d.items())) + "}"
    except AttributeError:
        return d


def get_loglevel_as_integer(loglevel, defaultlevel=None):
    """Get a proper loglevel integer.

    Used to ensure that a value is a valid loglevel integer.
    * If loglevel is already an integer, or a string representation of an interger, this integer is returned.
    * If loglevel is a registrered level NAME (e.g. DEBUG, INFO, WARNING, ERROR), then
        the correspoinding integer value is returned.
    * If anything fails, falls back to defaultlevel (if provided), or else logging.WARNING.
    """
    if defaultlevel is None:
        defaultlevel = logging.WARNING
    if loglevel is None:
        return defaultlevel
    try:
        loglevel = int(loglevel)
    except ValueError:
        loglevel = getattr(logging, loglevel.upper(), defaultlevel)
    except AttributeError:
        # no loglevel argument defined by argparse
        print("WARNING: Could not interpret loglevel '%s'" % loglevel)
        loglevel = defaultlevel
    return loglevel


def init_logging(config=None, prefix="gelutils"):
    """Initialize logging.

    Set up standard logging system based on values provided by argsns, namely:
    - loglevel
    - logtofile
    - testing

    """

    if config is None:
        config = {}
    elif not isinstance(config, dict):
        # Assume it is a NameSpace object returned by argparse.ArgumentParser.parse_args()
        config = config.__dict__

    dictconfig_fn = config.get("logging_config_dict_file")
    dictconfig = config.get("logging_config_dict")
    if dictconfig_fn or dictconfig:
        if dictconfig_fn:
            fnbase, fnext = os.path.splitext(dictconfig_fn)
            if fnext.lower() == ".yaml":
                print("Configuring logging system using dict config from yaml-formatted file:", dictconfig_fn)
                with open(dictconfig_fn) as fp:
                    dictconfig = yaml.load(fp)
            else:
                print("Configuring logging system using dict config from json-formatted file:", dictconfig_fn)
                with open(dictconfig_fn) as fp:
                    dictconfig = json.load(fp)
        else:
            print("Configuring logging system using dict from logging_control settings file.")
        logging.config.dictConfig(dictconfig)
        logger.info("Logging system initialized using dict-config "
                    + ("from file %s." % dictconfig_fn if dictconfig_fn else "from config-provided dict."))

    else:
        loglevel = get_loglevel_as_integer(config.pop('loglevel', None))
        logtofile = config.pop('logtofile', None)
        if logtofile:
            logtofile = os.path.expanduser(logtofile)

        # Examples of different log formats:
        # logfmt = "%(levelname)s: %(filename)s:%(lineno)s %(funcName)s() > %(message)s"
        # logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
        # loguserfmt = format of log displayed to the user; logfilefmt = format of log messages written to logfile.
        logconsolefmt = "%(asctime)s %(levelname)-15s %(name)20s:%(lineno)-4s%(funcName)20s() %(message)s"
        logfilefmt = '%(asctime)s %(levelname)-6s - %(name)s:%(lineno)s - %(funcName)s() - %(message)s'
        logdatefmt = "%Y%m%d-%H:%M:%S"  # "%Y%m%d-%Hh%Mm%Ss"
        logtimefmt = "%H:%M:%S"  # Output to user in console
        logformat = config.pop('logformat', logfilefmt if logtofile else logconsolefmt)
        logdatefmt = config.pop('logdatefmt', logdatefmt if logtofile else logtimefmt)
        logging.basicConfig(level=loglevel,
                            format=logformat,
                            datefmt=logdatefmt,
                            filename=logtofile)
        logger.info("Logging system initialized with loglevel %s, logfile filename=%s", loglevel, logtofile)


def gen_wikilist_entries(lines, listchar='*#-+', commentmidchar=None, includeempty=False):
    """Generate lane annotations from a string assuming list-like input format.

    This is sort of the inverse of gen_trimmed_lines, it returns
    all lines that starts with either '#' or '*',
    corresponding to a enumerated or bullet list in wiki format.
    commentmidchar, if specified, will remove anything to the right of this string, e.g.
    >>> gen_wikilist_entries(("sample (volume)",), firstchar='*#-+', commentmidchar="(")
    ["sample"]
    The 'includeempty' arg is not available: A line must start with 'listchar' to even be included.
    If you want 'empty' lines when using 'wikilist' lineinput, just add "empty" lines with '#' as the first char.
    """
    # if not includeempty:
    #     # Remove empty lines. Actually, this is not needed; empty lines cannot have the '#'
    #     # (listchar) at line[0] which is required to be included.
    lines = gen_stripped_nonempty_lines(lines)
    lines = (line[1:].strip().split(listchar)[0] for line in lines if line[0] in listchar)
    return lines


def gen_trimmed_lines(lines, commentchar='#', commentmidchar=None, includeempty=False):
    """Generate "nice" lane annotations, trimmed, stripped and without comments.

    Returns:
        list of non-empty, non-comment lines.

    Args:
        lines: The lines to trim, list of strings.
        commentchar: (default='#') defines a character that is used to denote a comment in a line:
            # This is a note.
        commentmidchar: can be used to define a 'mid-line' comment, e.g. in this case:
            data = value # Here is a 'midline comment' about data or value.
            commentmidchar defaults to the same as commentchar.
        includeempty: whether to include empty lines. Default (False) is to remove empty lines.

    Set commentchar to False (not None) to disable "midline comments".
    """
    if commentmidchar is None:
        commentmidchar = commentchar
    noncommentlines = gen_noncomments_lines(lines, firstchar=commentchar, midchar=commentchar)
    if includeempty:
        return noncommentlines
    return gen_stripped_nonempty_lines(noncommentlines)


def gen_stripped_nonempty_lines(lines):
    """Remove empty lines.

    Returns a generator of stripped, nonempty lines in <lines>.
    Args:
        lines : an iterator of string-like objects.
    """
    stripped = (line.strip() for line in lines)
    nonempty = (line for line in stripped if line)
    return nonempty


def gen_noncomments_lines(lines, firstchar='#', midchar=None):
    """Remove lines that are just comments.

    Returns a generator of lines that does not begin with firstchar.
    If midchar is provided, that is used to remove the part of the line to the right of that.
    """
    noncomment = (line for line in lines if line[0] != firstchar)
    if midchar:
        noncomment = (line.split(midchar, 1)[0] for line in noncomment)
    return noncomment


def trimmed_lines_from_file(filepath, args=None):
    """Read file and return a list with each line.

    Reads all non-comment parts of non-empty lines from file <filepath>,
    and returns these as a list, closing the file after loading the lines.
    See textdata_util.gen_trimmed_lines docs for info on commenchar and commentmidchar.
    Wow, I just realized
    """
    if args is None:
        args = {}
    with open(filepath) as fd:
        # Auto detect line input style:
        if args.get('lines_inputstyle') in (None, 'auto'):
            lines = [line for line in [line.strip() for line in fd] if line]
            fd.seek(0)
            if all(line[0] in "*#" for line in lines):
                args['lines_inputstyle'] = 'wikilist'
        args.setdefault('lines_commentmidchar', None)  # Same for all...
        if args.get('lines_inputstyle', None) in ('wikilist', 'wiki', 'list'):
            # Add arguments to args for convenience to the user:
            set_if_none(args, 'lines_listchar', '*#-+')
            trimmed_lines = gen_wikilist_entries(fd, args['lines_listchar'], args['lines_commentmidchar'])
        else:
            set_if_none(args, 'lines_commentchar', '#')  # Explicitly added to args to make it easier to change.
            includeempty = args.setdefault('lines_includeempty', False)
            trimmed_lines = gen_trimmed_lines(fd, args.get('lines_commentchar', '#'),
                                              args.get('lines_commentmidchar'), includeempty=includeempty)
        lines = list(trimmed_lines)
    return lines


def set_if_none(targetdict, key, value):
    """Update an entry in targetdict if either targetdict[key] is None or key not in targetdict."""
    if targetdict.get(key) is None:
        targetdict[key] = value


def update_none_values(targetdict, updatedict):
    """With all items in updatedict update targetdict ONLY IF targetdict[key] is None or key not in targetdict."""
    for k, v in updatedict.items():
        set_if_none(targetdict, k, v)


def update_defaults(target, *other_dicts):
    """Populate the first given dict in-place with default values from the other given dict(s).
    Values in earlier dicts take precedence over latter dicts.
    This is exactly the same as update_none_values, except it supports multiple other_dicts.

    Args:
        target: The dict to update.
        *other_dicts: One or more dicts with values to update target with.

    Examples:
        >>> A = {'a': 1, 'b': 2, 'c': 3}
        >>> update_setdefault(A, {'a': -1, 'd': -4}, {'a': 'X', 'd': 'Y', 'e': 'Z'})
        >>> print(A)  # {'a': 1, 'b': 2, 'c': 3, 'd': -4, 'e': 'Z'}

    """
    for d in other_dicts:
        for k, v in d.items():
            if k not in target or target[k] is None:
                target[k] = v


def mergedicts(*dicts):
    """Merge dictionaries.

    Merge all given dictionaries.
    The returned dict will have all keys from all dictionaries in dicts.
    The latter items in dicts take precedence of earlier, except if the value is None.
    None-values have the lowest precedence and is always overwritten if another dict has
    the same key/entry with a value different from None.

    Examples:
        >>> mergedicts({3:1, {3:2})
        {3:2}
        However only non-None items take precedence:
        >>> mergedicts({4:1}, {4:None})
        {4:1}
        However, the returned dict *will* have all keys from all dicts, even if they are None:
        >>> mergedicts({6:None, 7:None}, {6:None, 8:None})
        {6:None, 7:None, 8:None}
        In total:
        >>> mergedicts({1:1, 3:1, 4:1, 5:None, 6:None, 7:None}, {2:2, 3:2, 4:None, 5:2, 6:None, 8:None})
        {1:1, 2:2, 3:2, 4:1, 5:2, 6:None, 7:None, 8:None}
    """
    # Make dict with all keys from all keys, set to None:
    ret = dict.fromkeys(set(chain(*(d.keys() for d in dicts))))
    for d in dicts:
        ret.update({k: v for k, v in d.items() if v is not None})
    return ret


def mergeargs(argsns, argsdict=None, exclude_none=True, precedence='argsdict'):
    """Merge argns and argsdict into a single dict.

    Merges arguments from <argsdict> and <argsns> (argparse Namespace or similar object).
    The returned dict is guaranteed to have all keys from both argsns and argsdict,
    even if they are None and <exclude_none> is True.
    <exclude_none> only refers to whether elements with value of None still takes
    preference when the dicts are merged.
    * argns can be either an object or a dict.
    * argsdict, if specified must be a dict or None.
    * If argsdict is not specified, an empty dict is used. The result is then simply
        argsns.__dict__.copy().
    * If exclude_none is set to True (default), only non-None values from argsns is loaded to argsdict.
    * <precedence> can be either 'argsns' or 'argsdict'. If 'argsdict' is specified (default),
        entries in the argsdict take precedence over entries in argsns.
        If specifying 'argsns', entries in argsns will override entries in argsdict.
    Be careful if you specify default values for argparse and set presedence='argsns' !

    Typical usage is a function that that takes both an argsns argument and has **kwargs:
        def mock(a, b=None, argsns=None, **kwargs)
            kwargs = argsnstodict(argsns, kwargs)

    Note that when 'drippling down' kwargs:
    * a function should only specify keys that it does not pass on and which it does not intend to
        get from argsns.
    * If a function needs to use a variable but also pass this on, it should use it as a kwargs item.
    * Does that make sense?
    """
    if argsdict is None:
        argsdict = {}
    if argsns is None:
        nsdict = {}
    else:
        try:
            nsdict = argsns.__dict__
        except AttributeError:
            nsdict = argsns
    ret = dict.fromkeys(set(argsdict.keys()) | set(nsdict.keys()))
    # Specify which order to merge depending on which dict takes precedence (should be the last)
    mergeorder = (nsdict, argsdict) if precedence == 'argsdict' else (argsdict, nsdict)
    if exclude_none:
        return mergedicts(*mergeorder)
    for d in mergeorder:
        ret.update({k: v for k, v in d.items() if v is not None} if exclude_none else d)
    return ret
