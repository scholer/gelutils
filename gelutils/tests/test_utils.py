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
# pylint: disable=W0142

"""
Test module for gelannotator.py

Usage:
* To invoke all tests from command line in the root directory:
>>> python -m pytest

Use standard python assert statement to assert statements:
assert value == expected_value

"""

import pytest
import logging
logger = logging.getLogger(__name__)

from utils import ensure_numeric

def test_ensure_numeric():


    res = ensure_numeric('33%')
    assert res == 0.33
    assert isinstance(res, float)

    res = ensure_numeric('33%', 100)
    assert res == 33
    assert isinstance(res, int)

    res = ensure_numeric('1.115', 100, converter=float)
    assert res == 111.5
    assert isinstance(res, float)

    res = ensure_numeric('5.12', 5.0, sf_lim=10)
    assert res == 25.6
    assert isinstance(res, float)

    res = ensure_numeric(0.33, 100)
    assert res == 33
    assert isinstance(res, int)

    res = ensure_numeric(5.12, 5, sf_lim=10)
    assert 26 == res # int(round(5.12*5)), 5.12*5=25.6
    assert isinstance(res, int)

    res = ensure_numeric([0.146, '0.16', '177.8%'], 100)
    assert res == [15, 16, 178] # int(round(5.12*5)), 5.12*5=25.6
    assert all(isinstance(i, int) for i in res)

    # Maybe the user provided inval as a string of values: "left, top, right, lower"
    res = ensure_numeric("0.146, 0.16, 177.8%", 100)
    assert res == [15, 16, 178]
    assert all(isinstance(i, int) for i in res)

    # What if scale factor is an iterable:
    res = ensure_numeric("0.146, 0.16, 177.8%", [100, 200, 300.0])
    assert res == [15, 2*16, 533.4]



@pytest.mark.skipif(True, reason="Not ready yet")
def test_argsnstodict():
    pass
