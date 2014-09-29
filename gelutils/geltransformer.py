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

= CURRENT STATUS =

It works, but I'm having problems linearizing the data because PIL wants
to fit the data into its own range.

It might be better to

Or skip PIL all together and use something else.



= READING .GEL FILES: ==

Options:
* PIL
* tiffany: Tiff with PIL without PIL
** https://bitbucket.org/pydica/tiffany/
* pylibtiff
** https://code.google.com/p/pylibtiff/
** python wrapper for libtiff
* tifffile.py by Christoph Gohlke
** http://www.lfd.uci.edu/~gohlke/code/tifffile.py.html
** Uses numpy! :-D
* FreeImagePy
** http://freeimagepy.sourceforge.net/
** Wrapper for freeimage.dll/.so
* PythonMagick
** http://www.imagemagick.org/download/python/


== USING PIL ==

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


https://pillow.readthedocs.org/en/latest/handbook/concepts.html
- Which to use?
    I (32-bit signed integer pixels)
    F (32-bit floating point pixels)


"""

import os
import glob
#from functools import partial
import numpy
from PIL import Image#, TiffImagePlugin
from PIL.TiffImagePlugin import OPEN_INFO, II
# from PIL.TiffImagePlugin import BITSPERSAMPLE, SAMPLEFORMAT, EXTRASAMPLES, PHOTOMETRIC_INTERPRETATION, FILLORDER, OPEN_INFO

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)


# Adjust PIL so that it will open .GEL files:
# GEL image mode; using same as for PhotoInterpretation=1 mode.
# (ByteOrder, PhotoInterpretation, SampleFormat, FillOrder, BitsPerSample,  ExtraSamples) => mode, rawmode
gelfilemodes = {
        #(II, 0, 1, 1, (16,), ()): ("I;16", "I;16"),    # Gives problems with negative numbers.
        #(II, 0, 1, 1, (16,), ()): ("I;16S", "I;16S"), # "Unrecognized mode"
        #(II, 0, 1, 1, (16,), ()): ("I;16N", "I;16N"), # "Unrecognized mode"
        #(II, 0, 1, 1, (16,), ()): ("I", "I"), # "IOError: image file is truncated."
        (II, 0, 1, 1, (16,), ()): ("I", "I;16"), # THIS WORKS. Well, at least it does not produce negative numbers. I can put any value.
        #(II, 0, 1, 1, (16,), ()): ("F", "F;32F"), # "IOError: image file is truncated.
        #(II, 0, 1, 1, (16,), ()): ("I;32", "I;32N") # "Unrecognized mode"
        #(II, 0, 1, 1, (16,), ()): ("I", "I;32N") # This produces an IOError during load()
        #(II, 1, 1, 1, (32,), ()): ("I", "I;32N")
        }

OPEN_INFO.update(gelfilemodes)  # Update the OPEN_INFO dict; is used to identify TIFF image modes.
# PIL.Image.Image.convert has a little info on image modes.


#def linearize(gelvalue, scalefactor):
#    """
#    Converts a .GEL pixel value to linear grayscale value.
#    Hmm... Now does this yield ok results?
#    """
#    if isinstance(scalefactor, tuple):
#        return float(gelvalue**2*scalefactor[0])/scalefactor[1]
#    else:
#        return float(gelvalue**2)/scalefactor

#def pixel_transform(img, func):
#    """
#    Applies func to all pixels in tifimg (in-place).
#    Note: This is indeed VERY slow.
#    It might be better to create a numpy array, operate on that,
#    and produce a new image from the numpy-transformed data.
#
#    This won't work: If newval is larger than 2**16/2, then the value is "wrapped around".
#        50000 => -15536 = 50000 - 2**16
#
#    Also, it is probably better to use
#    >>> pixelmap = tifimg.load()
#    >>> pielmap[x,y] = newval
#
#    Edit: This is actually not that slow. The problem is just the whole "range thing".
#    Obviously, this is a problem even when you first load the gel.
#    Edit: Yes, it is slow. Very slow. But with the correct mode, the "range wrap thing"
#    is no-longer an issue.
#
#    """
#    width, height = img.size
#    #for x in xrange(width):
#    #    for y in xrange(height):
#    #        newval = round(func(tifimg.getpixel((x, y))))
#    #        #if newval < 0:
#    #        #    print "{},{} "
#    #        tifimg.putpixel((x, y), newval)
#    # trying as a generator:
#    # Returns None, so will go through all to see if any is True.
#    #any(tifimg.putpixel((x, y), round(func(tifimg.getpixel((x, y)))))
#    #    for x in xrange(width) for y in xrange(height))
#    # Still extremely slow...
#    npdata = numpy.asarray(img.getdata())
#    npdata**2


def find_dynamicrange(npdata, cutoff=(0, 0.99)):
    """
    Try to determine the range given the numpy data, so that the
    values within the cutoff fraction is within the dynamic range,
    and the fraction of values above and below the cutoff is beyond the dynamic range.
    I.e. for a cutoff of (0.02, 0.95), this function will return a dynamic range
    that will quench the lowest 2% and the top 5%.
    """
    counts, bins = numpy.histogram(npdata, bins=20)
    total = sum(counts)
    cutoffmin = 0
    print counts.cumsum()
    try:
        binupper = next(i for i, cumsum in enumerate(counts.cumsum()) if cumsum > total*cutoff[1])
        cutoffmax = int(bins[binupper]) # Must return int
        print "Cutoffmax:", cutoffmax
    except StopIteration:
        cutoffmax = cutoff*npdata.max()
        print "Could not find any bins, setting cutoffbin to", cutoffmax
    print "(cutoffmin, cutoffmax):", (cutoffmin, cutoffmax)
    return (cutoffmin, cutoffmax)


def processimage(gelimg, linearize=False, dynamicrange=None, invert=False, crop=None):
    """
    Linearizes all data points (pixels) in gelimg.
    gelimg should be a PIL.Image.Image object.
    crop is a 4-tuple box:
        (x1, y1, x2, y2)
        (1230, 100, 2230, 800)
    """
    scalefactor = gelimg.tag.getscalar(33446) # or tifimg.tag.tags[33446][0]
    opts = {}
    if crop:
        orgimage = gelimg
        gelimg = gelimg.crop(crop)

    #linearize_this = partial(linearize, scalefactor=scalefactor) # closure
    # alternatively:
    #linearize_this = lambda value: linearize(value, scalefactor)
    # getdata() just returns gelimg.im
    #linear_data = (linearize(value, scalefactor) for value in gelimg.getdata())
    #gelimg.putdate(linear_data)
    # edit: use Image.eval(image, function) to apply function to each pixel in image.
    # this just does image.point(function)
    # Note that PIL and PILLOW does a really weird thing when trying to do point()
    # on images with mode "I", "I;16", or "F".
    # The function must have the format: argument * scale + offset
    # else just go directly to gelimg.im.point() ?
    # return gelimg._new(gelimg.im.point(linearize_this, None))
    # Nope, im.point() REQUIRES a sequence-type look-up-table lut.
    # You could use point_transform, but that only does scaling and offset, no custom things.
    # pixel_transform(gelimg, linearize_this) # Probably slow, but whatever. It is. VERY SLOW.
    # Maybe you could use PIL.ImageChops.multiply(img, img) ?
    # Except this divides with MAX.

    # Trying numpy instead:
    #npdata = numpy.asarray(img.getdata())
    #npdata = numpy.asarray(gelimg.getdata())
    npimg = numpy.array(gelimg) # Do not use getdata
    if linearize:
        npimg = (npimg**2)/scalefactor[1]

    if dynamicrange == 'auto' or (invert and not dynamicrange):
        # If we want to invert, we need to have a range:
        #dynamicrange = (0, 100000)
        dynamicrange = map(int, find_dynamicrange(npimg)) # Ensure you receive ints.

    if dynamicrange:
        # Transform image so all values < dynamicrange[0] is set to 0
        # all values > dynamicrange[1] is set to 2**16 and all values in between are scaled accordingly.
        # Closure:
        minval, maxval = 0, 2**16-1
        lowest, highest = dynamicrange
        if invert:
            def adjust_fun(val):
                if val < lowest:
                    return maxval
                elif val > highest:
                    return minval
                return (maxval*(highest-val))/(highest-lowest)
        else:
            def adjust_fun(val):
                if val < lowest:
                    return minval
                elif val > highest:
                    return maxval
                return (maxval*(val-lowest))/(highest-lowest)
        adjust_vec = numpy.vectorize(adjust_fun)
        npimg = adjust_vec(npimg)
    linimg = Image.fromarray(npimg, gelimg.mode)
    opts['dynamicrange'] = dynamicrange
    return linimg, opts


def get_gel(filepath, linearize=False, dynamicrange=None, invert=False, crop=None):
    """
    Returns gel as PIL.Image.Image object.
    If linearize is True (default), the .GEL data will be linearized before returning.
    Note that invert only takes effect if you specify a dynamic range.
    """
    orgimage = Image.open(filepath)
    gelimage, opts = processimage(orgimage, linearize=linearize, dynamicrange=dynamicrange, invert=invert, crop=crop)
    return gelimage, orgimage, opts

import re

def get_PMT(img):
    """
     (33449, <Scan Info>)
    """
    try:
        scaninfo = img.tag[33449]
    except (KeyError, AttributeError):
        return
    prog = re.compile(r'(\d{3})\sV')
    for line in scaninfo.split('\n'):
        match = prog.match(line)
        if match:
            return match.groups()[0]

def has_PMT(filename):
    prog = re.compile(r'.*\d{3}[_\s]?V.*')
    return prog.match(filename)


def convert(argns):
    """
    Converts gel file to png given the info in argns.
    """

    basename, gelext = os.path.splitext(argns.gelfile)

    if argns.autorange and not argns.dynamicrange:
        argns.dynamicrange = 'auto'

    argkeys = ('linearize', 'dynamicrange', 'crop', 'invert')
    args = {k: v for k, v in argns.__dict__.items() if k in argkeys}
    print args
    gelimg, orgimg, opts = get_gel(argns.gelfile, **args)
    # Use orgimg for info, e.g. orgimg.info and orgimg.tag
    print "Range: ", gelimg.getextrema()
    argns.opts = opts
    dr = opts['dynamicrange']

    if argns.png:
        if dr[1] % 1000 == 0:
            if dr[0] % 1000 == 0:
                rng = u"{}-{}k".format(*(i/1000 for i in dr))
            else:
                rng = u"{}-{}k".format(dr[0], dr[1]/1000)
        else:
            rng = u"{}-{}".format(*dr)
        if not has_PMT(basename):
            pmt = get_PMT(orgimg)
            if pmt:
                rng = u"{}V_{}".format(pmt, rng)
        if not argns.overwrite:
            N_existing = len(glob.glob(basename+'*.png'))
            pngfilename = u"{}_{}_{}.png".format(basename, rng, N_existing)
        else:
            pngfilename = u"{}_{}.png".format(basename, rng)
        gelimg.save(pngfilename)
        argns.pngfilename = pngfilename
        print "PNG saved:", pngfilename

    return gelimg, orgimg, argns


if __name__ == '__main__':

    def activate_readline():
        import rlcompleter
        import readline
        readline.parse_and_bind('tab: complete')
    ar = activate_readline

    #testdir = r'C:\Users\scholer\Dropbox\_experiment_data\2014_Harvard\RS323 p8634 scaffold prep w Nandhini v2\RS323d Agarose analysis of p8634 prep (20140925)'
    #os.chdir(testdir)
    #testfile = 'RS323_Agarose_ScaffoldPrep_550V.gel'
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('gelfile')
    ap.add_argument('--linearize', action='store_true', help="Linearize gel (if e.g. typhoon).") #, default=100
    ap.add_argument('--no-linearize', action='store_false', dest='linearize', help="Linearize gel (if e.g. typhoon).") #, default=100
    ap.add_argument('--dynamicrange', nargs=2, type=int, help="Dynamic range, min max, e.g. 300 5000.")
    ap.add_argument('--autorange', action='store_true', help="Dynamic range, min max, e.g. 300 5000.")
    ap.add_argument('--crop', nargs=4, type=int, help="Crop image to this box (x1 y1 x2 y2) aka (left upper right lower), e.g. 500 100 1200 400.")
    ap.add_argument('--invert', action='store_true', help="Invert image data.")
    ap.add_argument('--no-invert', action='store_false', dest='invert', help="Invert image data.")
    ap.add_argument('--png', action='store_true', help="Save as png.")
    ap.add_argument('--overwrite', action='store_true', default=True, help="Overwrite existing png.")
    ap.add_argument('--no-overwrite', action='store_false', dest='overwrite', help="Do not overwrite existing png.")

    argns = ap.parse_args()
    print argns.__dict__
    argns.png = True
    convert(argns)

"""
Old stuff:
    #datalist = gelimg.getdata()
    pixelmap = gelimg.load()
    ar()
    print "pixel 0,0:", gelimg.getpixel((0, 0))
    width, height = gelimg.size
    all_pixels = ((x, y, pixelmap[x, y]) for x in xrange(width) for y in xrange(height))
    negative_pixels = list((x, y, val) for x, y, val in all_pixels if val < 0)
    print negative_pixels
    #print "({},{}): {}".format(*next(negative_pixels))
    print "Linearizing data..."
    #lin_gel = linearize_gel(gelimg, dynamicrange=(0, 5000), invert=True)
    print "Range: ", lin_gel.getextrema()
    print "pixel 0,0:", lin_gel.getpixel((0, 0))
    pixelmap = lin_gel.load()
    all_pixels = ((x, y, pixelmap[x, y]) for x in xrange(width) for y in xrange(height))
    negative_pixels = list((x, y, val) for x, y, val in all_pixels if val < 0)
    print "negative_pixels:", negative_pixels
    img = lin_gel
    import glob
    N_existing = len(glob.glob('pil_geltest*'))
    img.save('pil_geltest{}.png'.format(N_existing+1))
    #point transform:
    # a) Using scale+offset:
    # b) Using look-up-table:
    #

    # If we say a range of "300-5000", we mean that 300 should be dark and 5000 should be all white.
    # So, make a scaling so:
    #       300 -> 0 and 5000 -> (max)
    #       values between 300-5000 is scaled to the proper value,
    #       and everything higher/lower is outside the (min/max) range.

    print "Done!"
"""
