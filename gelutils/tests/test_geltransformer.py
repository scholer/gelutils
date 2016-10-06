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

Use standard python assert statement to assert statements:
assert value == expected_value

"""

import pytest
import logging

# Tests are run from main directory
from geltransformer import get_pmt_string, has_pmt_string, find_dynamicrange, processimage, get_gel, convert

logger = logging.getLogger(__name__)


# @pytest.mark.skipif(True, reason="Not ready yet")
def test_has_pmt():
    has = ('rs323_agarose_scaffoldprep_550v_cropped_annotated.png',
           '550V.gel', 'Agarose_550 V.gel', 'Mygel 100 V.gel')
    hasnot = ('rs323_agarose_scaffoldprep_550_cVropped_annotated.png',
              '30V.gel', '5 00V.gel', 'Agarose 500sV.gel')
    for fn in has:
        assert has_pmt_string(fn) is not None
    for fn in hasnot:
        assert has_pmt_string(fn) is None
