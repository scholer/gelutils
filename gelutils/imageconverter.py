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

Module for converting images.


How to convert svg to png?

Use cairo / cairosvg / rsvg:
* http://stackoverflow.com/questions/6589358/convert-svg-to-png-in-python
* http://cairosvg.org/
* pypi.python.org/pypi/CairoSVG
* http://cairographics.org/pyrsvg/
* Is not in standard python, requires custom package.

Using PIL?
* Nope
* http://stackoverflow.com/questions/3600164/read-svg-file-with-python-pil
* Need to use cairo.

So...
* Installed cairosvg
* Installed Pycairo     (http://cairographics.org/pycairo/)
* Looking at cairocffi, https://pythonhosted.org/cairocffi/overview.html
* Installed GTK+ http://gtk-win.sourceforge.net/home/index.php/Main/Downloads
** Alternatives:
*** http://gladewin32.sourceforge.net/
*** http://www.gtk.org/download/
* Nothing.
* http://stackoverflow.com/questions/8704407/how-do-you-install-pycairo-cairo-for-python-on-windows
* http://www.lfd.uci.edu/~gohlke/pythonlibs/#pygtk
* Installers unable to find my anaconda installation...

"""

import os
#import PIL
from geltransformer import get_gel

def geltopng(filepath, linearize=True, dynamicrange=None, crop=None, rotate=None):
    """
    Opens a .GEL file, linearize the data, adjust the range, crops, rotates,
    and saves as .png
    """
    #gelbasename, gelext = os.path.split(filepath)
    img = get_gel(filepath, linearize=linearize)
    return img




