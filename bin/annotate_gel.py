#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2016 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
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
# pylint: disable=C0103


from __future__ import print_function, absolute_import
import os
import sys
from pprint import pprint
import logging
logger = logging.getLogger(__name__)

# Make sure to use os.path.dirname(__file__) not just "." (current working directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

print(sys.path)
from gelutils.argutils import parseargs, make_parser, mergedicts
from gelutils.utils import init_logging
from gelutils.gelannotator_gui import main


if __name__ == '__main__':

    default_args = {
        'openwebbrowser': True,
        'filename_substitution': ['-[SYBR Gold]', ''],
    }
    # There are two approaches to merging default args (or user preferences) and command line overrides.
    # (a) Forward the default args to parseargs and it will use default args for defaults.
    # (b) Parse command line args as normal, making sure all unspecified options defaults to None,
    #     and merge afterwards with mergedicts.
    argns = parseargs(prog='gui', )
    cmdlineargs = argns.__dict__
    print("Parsed command line args:")
    pprint(cmdlineargs)
    # Stupid windows doesn't expand command line args...

    # Update default cmdline args:
    # mergedicts(dictA, dictB) # dictB takes preference over dictA except for None-values.
    config = mergedicts(default_args, cmdlineargs)
    print("Merged config:")
    pprint(config)


    # set_workdir(args) Not needed, done by app during set_gelfilepath
    # If you need to have debug log output for arg parsing, put this above parseargs:
    print("before init_logging...")
    # Initializing logging doesn't cause immediate halt, nor does logging a debug msg.
    # Yet, if I do init_logging, my exe will hang.
    # Manual logging rather than basicConfig - issue persists...
    logging_disabled = config.pop('disable_logging', False)
    if not logging_disabled:
        init_logging(config)
    # TODO: Move init_logging to main()
    print("after init_logging...")
    logger.debug("hejsa")
    print("after first debug log msg...")
    main(config)

    # TODO: Add gelfile as an actual entry in the yaml config, where defaulting to None/'auto' will give the current file name
