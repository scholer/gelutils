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
# pylint: disable=W0142

"""
Test module for gelannotator.py

Usage:
* To invoke all tests from command line in the root directory:
>>> python -m pytest

"""

from __future__ import print_function, absolute_import
import pytest
import logging
from argparse import Namespace

from gelutils.utils import mergeargs

logger = logging.getLogger(__name__)


def test_mergeargs():
    """
    Testing
    >>> mergeargs(argsns, argsdict=None, exclude_none=True, precedence='argsdict')

    """
    testdict = {'my': 'god', 'word': 'down', 'nonetestdict': None,
                'nonetesta': None, 'nonetestb': 'b', 'nonetestc': None}
    testns = Namespace()
    testns.hej = 'der'        # key only in testns
    testns.word = 'up'        # key with not-None value in both
    testns.nonetestns = None  # key with None value only in testns
    testns.nonetesta = 'a'    # key with not-None value in testns and None value in testdict
    testns.nonetestb = None   # key with None value in testns and not-None value in testdict
    testns.nonetestc = None   # key with None value in both testns and testdict
    # test1:
    test1 = mergeargs(testns)
    assert test1 == testns.__dict__
    # test, with defaults: testdict take precedence for non-None values.
    test2 = mergeargs(testns, testdict)
    assert all(k in test2 for k in list(testdict.keys())+list(testns.__dict__.keys()))
    assert test2['hej'] == 'der'
    assert test2['my'] == 'god'
    assert test2['word'] == 'down'
    assert test2['nonetestns'] is None
    assert test2['nonetestdict'] is None
    assert test2['nonetesta'] == 'a'
    assert test2['nonetestb'] == 'b'
    assert test2['nonetestc'] is None
    # test, with precedence = 'argsns':
    test2 = mergeargs(testns, testdict, precedence='argsns')
    assert all(k in test2 for k in list(testdict.keys())+list(testns.__dict__.keys()))
    assert test2['hej'] == 'der'            # constant
    assert test2['my'] == 'god'             # constant
    assert test2['word'] == 'up'            # variable
    assert test2['nonetestns'] is None      # constant
    assert test2['nonetestdict'] is None    # constant
    assert test2['nonetesta'] == 'a'        # constant
    assert test2['nonetestb'] == 'b'        # constant
    assert test2['nonetestc'] is None       # variable
    # test, with excludeNone=False: argsdict[nonetesta]=None will override argsns.nonetesta
    test2 = mergeargs(testns, testdict, exclude_none=False)
    assert all(k in test2 for k in list(testdict.keys())+list(testns.__dict__.keys()))
    assert test2['hej'] == 'der'            # constant
    assert test2['my'] == 'god'             # constant
    assert test2['word'] == 'down'            # variable
    assert test2['nonetestns'] is None      # constant
    assert test2['nonetestdict'] is None    # constant
    assert test2['nonetesta'] is None        # constant
    assert test2['nonetestb'] == 'b'        # constant
    assert test2['nonetestc'] is None       # variable
    # test, with precedence = 'argsns' and excludeNone=False: argsns.nonetestb will override argsdict[nonetestb]=None
    test2 = mergeargs(testns, testdict, precedence='argsns', exclude_none=False)
    assert all(k in test2 for k in list(testdict.keys())+list(testns.__dict__.keys()))
    assert test2['hej'] == 'der'            # constant
    assert test2['my'] == 'god'             # constant
    assert test2['word'] == 'up'            # variable, depending on precedence
    assert test2['nonetestns'] is None      # constant
    assert test2['nonetestdict'] is None    # constant
    assert test2['nonetesta'] == 'a'        # variable, depending on excludeNone and then precedence
    assert test2['nonetestb'] is None        # variable, depending on excludeNone and then precedence
    assert test2['nonetestc'] is None       # constant
