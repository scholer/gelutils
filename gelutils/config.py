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

"""
Default constants and configuration.

"""

import os
import yaml

gel_exts = (".gel", ".tiff", ".tif")
img_exts = (".png", ".jpg", ".tiff", ".tif")
cfg_exts = (".yaml", ".yml", ".gaml")
default_yaml_ext = ".gaml"
DEFAULT_CONFIG_FILEPATHS = (
    'gelannotator.yaml',  # file in current directory
    '~/.gelannotator.yaml',
    '~/.config/gelannotator.yaml',
    '~/.config/gelannotator/default_config.yaml',
    '~/.config/gelannotator/gelannotator.yaml',
    '~/.config/gelannotator/.gelannotator.yaml',
    '~/appdata/gelannotator/gelannotator.yaml',
    '~/.appdata/gelannotator/gelannotator.yaml',
)


def filename_is_yaml(fn):
    base, ext = os.path.splitext(fn)
    return ext in cfg_exts


def yaml_get(filepath, default=None):
    """ Load yaml from filepath. Return default if file could not be loaded. """
    try:
        with open(filepath) as fd:
            data = yaml.safe_load(fd)
            logger.debug("yaml file loaded: %s", filepath)
    except IOError:
        logger.debug("Could not find/load yaml file %s", filepath)
        data = default
    return data


