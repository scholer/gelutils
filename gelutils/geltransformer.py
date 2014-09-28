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

Module for transforming gel images: converting, mapping, cropping, etc.


= READING .GEL FILES: ==

To open with PIL:
from PIL.TiffImagePlugin import OPEN_INFO

See tags with:
>>> sorted(tifimg.tag.items())
Use http://www.awaresystems.be/imaging/tiff/tifftags/search.html to identify tiff tags.
Interesting tags are:
 (33445, (2,)), # MD FileTag. Specifies the pixel data format encoding in the Molecular Dynamics GEL file format. http://www.awaresystems.be/imaging/tiff/tifftags/mdfiletag.html
 (33446, ((1, 21025),)), # MD ScalePixel. Specifies a scale factor in the Molecular Dynamics GEL file format. http://www.awaresystems.be/imaging/tiff/tifftags/mdscalepixel.html
 (33447, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 45854)),
 (33448, 'CB'),
 (33449, <Scan Info>)

MD FileTag values:
    2   => Square-root data format
    128 => Linear data format
MD ScalePixel is the scale factor used to linearize "compressed" Typhoon data to regular TIFF data.

scale_factor = tifimg.tag.getscalar(33446) # or tifimg.tag.tags[33446][0]
scale_factor_denominator = scale_factor_def[1]

More info: http://www.awaresystems.be/imaging/tiff/tifftags/docs/gel.html
# grayscale_value = Square(stored_value)*scale
# grayscale_value = scale_factor*stored_value**2
# I think is should be like this:
# grayscale_value = float(stored_value**2*scale_factor[0])/scale_factor[1]



"""

from functools import partial
from PIL import Image, TiffImagePlugin
from PIL.TiffImagePlugin import OPEN_INFO, II
# from PIL.TiffImagePlugin import BITSPERSAMPLE, SAMPLEFORMAT, EXTRASAMPLES, PHOTOMETRIC_INTERPRETATION, FILLORDER, OPEN_INFO


# Adjust PIL so that it will open .GEL files:
# GEL image mode; using same as for PhotoInterpretation=1 mode.
# (ByteOrder, PhotoInterpretation, SampleFormat, FillOrder, BitsPerSample,  ExtraSamples) => mode, rawmode
gelfilemodes = {(II, 0, 1, 1, (16,), ()): ("I;16", "I;16")}
OPEN_INFO.update(gelfilemodes)  # Update the OPEN_INFO dict; is used to identify TIFF image modes.
# PIL.Image.Image.convert has a little info on image modes.

def linearize(gelvalue, scalefactor):
    """ Converts a .GEL pixel value to linear grayscale value."""
    if isinstance(scalefactor, tuple):
        return float(gelvalue**2*scalefactor[0])/scalefactor[1]
    else:
        return float(gelvalue**2)/scalefactor

def pixel_transform(tifimg, func):
    """
    Applies func to all pixels in tifimg (in-place).
    """
    width, height = tifimg.size
    for x in xrange(width):
        for y in xrange(height):
            newval = func(tifimg.getpixel((x, y)))
            tifimg.putpixel((x, y), newval)

def linearize_gel(gelimg):
    """
    Linearizes all data points (pixels) in gelimg.
    gelimg should be a PIL.Image.Image object.
    """
    scalefactor = gelimg.tag.getscalar(33446) # or tifimg.tag.tags[33446][0]
    linearize_this = partial(linearize, scalefactor=scalefactor) # closure
    # alternatively:
    #linearize_this = lambda value: linearize(value, scalefactor)
    # getdata() just returns gelimg.im
    #linear_data = (linearize(value, scalefactor) for value in gelimg.getdata())
    #gelimg.putdate(linear_data)
    # edit: use Image.eval(image, function) to apply function to each pixel in image.
    # this just does image.point(function)
    # Note that PIL and PILLOW does a really weird thing when trying to do point()
    # on images with mode "I", "I;16", or "F".
    # else just go directly to gelimg.im.point() ?
    # return gelimg._new(gelimg.im.point(linearize_this, None))
    # Nope, im.point() REQUIRES a sequence-type look-up-table lut.
    # You could use point_transform, but that only does scaling and offset, no custom things.
    pixel_transform(gelimg, linearize_this) # Probably slow, but whatever.

def set_range(gelimg, dynamicrange=None):
    """
    Adjusts the dynamic range of the gel image.
    """

def get_gel(filepath, linearize=True):
    """
    Returns gel as PIL.Image.Image object.
    If linearize is True (default), the .GEL data will be linearized before returning.
    """
    gelimage = Image.open(filepath, 'rb')
    if linearize:
        linearize_gel(gelimage)
    return gelimage
