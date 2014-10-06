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
# pylint: disable=W0141,W0142,C0103,R0913,R0914

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
import re

#from functools import partial
import numpy
from PIL import Image#, TiffImagePlugin
from PIL import ImageOps
from PIL.TiffImagePlugin import OPEN_INFO, II
# from PIL.TiffImagePlugin import BITSPERSAMPLE, SAMPLEFORMAT, EXTRASAMPLES, PHOTOMETRIC_INTERPRETATION, FILLORDER, OPEN_INFO

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

from utils import init_logging, printdict, getabsfilepath, getrelfilepath
from argutils import parseargs, mergedicts

# PIL.Image.Image.convert has a little info on image modes.
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




def get_PMT(img):
    """
     (33449, <Scan Info>)
    """
    if isinstance(img, basestring):
        scaninfo = img
    else:
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
    """
    Returns whether filename has photomultipler designation in filename.
    E.g. "Agarose 500 V.gel", "Agarose_500V.gel", "Agarose_500_V_gel1.gel"
    """
    prog = re.compile(r'.*\d{3}[_\s]?[Vv].*')
    return prog.match(filename)


def find_dynamicrange(npdata, cutoff=(0, 0.99)):
    """
    Try to determine the range given the numpy data, so that the
    values within the cutoff fraction is within the dynamic range,
    and the fraction of values above and below the cutoff is beyond the dynamic range.
    I.e. for a cutoff of (0.02, 0.95), this function will return a dynamic range
    that will quench the lowest 2% and the top 5%.
    """
    counts, bins = numpy.histogram(npdata, bins=100)        # pylint: disable=E1101
    total = sum(counts)
    cutoffmin = 0
    #print counts.cumsum()
    try:
        binupper = next(i for i, cumsum in enumerate(counts.cumsum()) if cumsum > total*cutoff[1])
        cutoffmax = int(bins[binupper]) # Must return int
        print "Cutoffmax:", cutoffmax
    except StopIteration:
        cutoffmax = cutoff*npdata.max()
        print "Could not find any bins, setting cutoffbin to", cutoffmax
    print "(cutoffmin, cutoffmax):", (cutoffmin, cutoffmax)
    return (cutoffmin, cutoffmax)


def processimage(gelimg, args=None, linearize=None, dynamicrange=None, invert=None, crop=None, rotate=None, **kwargs):          # pylint: disable=R0912
    """
    gelimg is a PIL Image file, not just a path.
    Linearizes all data points (pixels) in gelimg.
    gelimg should be a PIL.Image.Image object.
    crop is a 4-tuple box:
        (x1, y1, x2, y2)
        (1230, 100, 2230, 800)

    Returns processed image
    """
    stdargs = dict(linearize=linearize, dynamicrange=dynamicrange, invert=invert, crop=crop, rotate=rotate)
    logger.debug("processimage() invoked with gelimg %s, args %s, stdargs %s and kwargs %s",
                 gelimg, printdict(args), printdict(stdargs), printdict(kwargs))
    if args is None:
        args = {}
    #defaultargs = dict(linearize=None, dynamicrange=None, invert=None, crop=None)
    # mergedicts only overrides non-None entries:
    args.update(mergedicts(args,
                           stdargs,     # I ONLY have this after args because all of them default to None.
                           kwargs))     # Otherwise I would have used the 'defaultdict' approach.
    logger.debug("--combined args dict is: %s", printdict(args))

    # unpack essentials (that are not changed):

    info = gelimg.info
    width, height = gelimg.size
    info['extrema_ante'] = gelimg.getextrema()
    tifftags = {33445: 'MD_FileTag', 33446: 'MD_ScalePixel', 33447: 'unknown', 33448: 'user'}
    for tifnum, desc in tifftags.items():
        try:
            info[desc] = gelimg.tag[tifnum]
        except KeyError:
            pass
        except AttributeError:
            # gelimg does not have a tag property, e.g. if png file:
            break
    try:
        scaninfo = gelimg.tag[33449]
        scalefactor = gelimg.tag.getscalar(33446) # or tifimg.tag.tags[33446][0]
    except AttributeError:
        scaninfo = ""
        scalefactor = None
    pmt = get_PMT(scaninfo)
    info.update(dict(width=width, height=height, pmt=pmt, scalefactor=scalefactor))
    logger.debug("Image info: %s", info)

    if args['rotate']:
        # NEAREST=1, BILINEAR=2, BICUBIC=3
        gelimg = gelimg.rotate(angle=args['rotate'], filter=3, expand=args.get('rotateexpands'))

    if args['crop']:
        if args.get('cropfromedges'):
            left, upper, right, lower = args['crop']
            gelimg = gelimg.crop((left, upper, width-right, height-lower))
        else:
            gelimg = gelimg.crop(args['crop'])

    # If we are not linearizing or adjusting dynamic range, we can take a shortcut that does not involve numpy:
    if (not (args['linearize'] and scalefactor)) and (not args['dynamicrange'] or args['dynamicrange'] == 'auto'):
        logger.debug("Not linearizing, avoiding numpy detour...")
        modimg = None
        try:
            if args['invert']:
                # credit: http://stackoverflow.com/questions/2498875/how-to-invert-colors-of-image-with-pil-python-imaging
                modimg = ImageOps.invert(modimg or gelimg)
            if args['dynamicrange'] == 'auto':
                # This may yield a rather different result than the dynamic range below:
                modimg = ImageOps.autocontrast(modimg or gelimg)
            info['extrema_post'] = gelimg.getextrema()
            return modimg or gelimg, info
        except IOError as e:
            logger.info("""Could not use PIL ImageOps to perform requested operations, "%s"
                        -- falling back to standard numpy.""", e)

    # Using numpy to do pixel transforms:
    npimg = numpy.array(gelimg) # Do not use getdata(), just pass the image. # pylint: disable=E1101
    if args['linearize'] and scalefactor:
        logger.debug('Linearizing gel data using scalefactor %s...', scalefactor)
        npimg = (npimg**2)/scalefactor[1]

    dr = args.get('dynamicrange')
    if dr == 'auto' or (args['invert'] and not dr):
        # If we want to invert, we need to have a range. If it is not specified, we need to find it.
        #dynamicrange = (0, 100000)
        args['dynamicrange'] = map(int, find_dynamicrange(npimg)) # Ensure you receive ints.


    if args['dynamicrange']:
        if isinstance(args['dynamicrange'], int):
            args['dynamicrange'] = [0, args['dynamicrange']]
        if len(args['dynamicrange']) == 1:
            args['dynamicrange'] = [0, args['dynamicrange'][0]]

        # Transform image so all values < dynamicrange[0] is set to 0
        # all values > dynamicrange[1] is set to 2**16 and all values in between are scaled accordingly.
        # Closure:
        logger.debug("(a) dynamicrange: %s", args['dynamicrange'])
        ## TODO: FIX THIS FOR non 16-bit images:
        minval, maxval = 0, 2**16-1     # Note: This is not true for e.g. 8-bit png files
        lowest, highest = info['dynamicrange'] = args['dynamicrange']
        if args['invert']:
            logger.debug('Inverting image...')
            def adjust_fun(val):
                """ Function to adjust dynamic range of image, inverting the image in the process. """
                if val < lowest:
                    return maxval
                elif val > highest:
                    return minval
                return (maxval*(highest-val))/(highest-lowest)
        else:
            def adjust_fun(val):
                """ Function to adjust dynamic range of image. """
                if val < lowest:
                    return minval
                elif val > highest:
                    return maxval
                return (maxval*(val-lowest))/(highest-lowest)
        adjust_vec = numpy.vectorize(adjust_fun)    # pylint: disable=E1101
        npimg = adjust_vec(npimg)

    linimg = Image.fromarray(npimg, gelimg.mode)
    # saving org info in info dict:

    info['extrema_post'] = linimg.getextrema()

    return linimg, info


def get_gel(filepath, args):
    """
    Returns (image, info) tuple.
    Image is a PIL.Image.Image object of the gel after processing as specified by args.
    Info is a dict with various info on the original image (before round-trip to numpy).
    If linearize is True (default), the .GEL data will be linearized before returning.
    Note that invert only takes effect if you specify a dynamic range.
    """
    gelimage = Image.open(filepath)
    gelimage, info = processimage(gelimage, args)
    return gelimage, info



def convert(gelfile, args, **kwargs):   # (too many branches and statements, bah) pylint: disable=R0912,R0915
    """
    Converts gel file to png given the info in args.

    Returns (image, info) tuple.
    Image is a PIL.Image.Image object of the gel after processing as specified by args.
    Info is a dict with various info on the original image (before round-trip to numpy).

    <args> may be updated by the process to contain transformed arguments, e.g.
      dynamicrange='auto' being converted to an actual (min, max) tuple value.

    If linearize is True (default for gel data), the .GEL data will be linearized before returning.
    """
    logger.debug("convert() invoked with gelfile %s, args %s and kwargs %s", gelfile, printdict(args), printdict(kwargs))
    #defaultargs = dict(linearize=False, dynamicrange=None, invert=False, crop=None, opts=None)
    if args is None:
        args = {}
    args.update(mergedicts(args, kwargs))
    logger.debug("--combined args dict is: %s", printdict(args))

    gelfile = gelfile or args['gelfile']
    basename, gelext = os.path.splitext(gelfile)
    gelext = gelext.lower()

    if gelext == '.gel':
        logger.debug("Gel file input ('%s') -> enabling linearize and invert if not specified.", gelext)
        if args.get('linearize') is None:
            args['linearize'] = True
        if args.get('invert') is None:
            args['invert'] = True

    dr = args.get('dynamicrange', None)
    # If you want to specify a default value, do it at the very top.
    # Parsing/conforming dynamicrange is done by transform():
    #if dr is None:
    #    dr = args['dynamicrange'] = 'auto'
    #if isinstance(dr, int):
    #    dr = args['dynamicrange'] = (0, dr)
    #elif len(dr) < 2:
    #    dr = args['dynamicrange'] = (0, dr[0])

    # Process and transform gel:
    # Good to have gel info even if args is locked for updates:
    logger.debug("getting image file...")
    gelimg, info = get_gel(gelfile, args)
    # Use orgimg for info, e.g. orgimg.info and orgimg.tag
    logger.debug("gelimg extrema: %s", gelimg.getextrema())
    dr = info.get('dynamicrange')
    logger.debug("dynamic range: %s", dr)

    #if args.get('convertgelto', 'png') is None:
    #    args['convertgelto'] = 'png'
    #if args.get('convertgelto'] == 'png'):
    if dr is None:
        rng = "norange"
    else:
        if dr[1] % 1000 == 0:
            if dr[0] % 1000 == 0:
                rng = "{}-{}k".format(*(i/1000 for i in dr))
            else:
                rng = "{}-{}k".format(dr[0], dr[1]/1000)
        else:
            rng = "{}-{}".format(*dr)
    if not has_PMT(basename):
        if info.get('pmt'):
            rng = "{}V_{}".format(info['pmt'], rng)

    if not args.get('convertgelto'):
        args['convertgelto'] = 'png'
    ext = args['convertgelto']

    # basename is gelfile minus extension but with directory:
    if not args.get('overwrite', True):
        N_existing = len(glob.glob(basename+'*.'+ext))
        pngfilename = u"{}_{}_{}.{}".format(basename, rng, N_existing, ext)
    else:
        pngfilename = u"{}_{}.{}".format(basename, rng, ext)

    # Make sure you save relative to the gelfile:
    pngfilename_relative = getrelfilepath(gelfile, pngfilename)
    logger.debug("pngfilename: %s", pngfilename)
    logger.debug("pngfilename_relative: %s", pngfilename_relative)
    logger.debug("Saving gelfile to: %s", pngfilename)
    gelimg.save(pngfilename)
    # Note: 'pngfile' may also be a jpeg file, if the user specified convertgelto jpg
    args['pngfile'] = info['pngfile'] = pngfilename_relative

    return gelimg, info



if __name__ == '__main__':

    #def activate_readline():
    #    #import rlcompleter
    #    import readline
    #    readline.parse_and_bind('tab: complete')
    #ar = activate_readline
    init_logging()

    #testdir = r'C:\Users\scholer\Dropbox\_experiment_data\2014_Harvard\RS323 p8634 scaffold prep w Nandhini v2\RS323d Agarose analysis of p8634 prep (20140925)'
    #os.chdir(testdir)
    #testfile = 'RS323_Agarose_ScaffoldPrep_550V.gel'

    argns = parseargs(prog='geltransformer')
    cmdgelfile = argns.gelfile
    cmdargs = argns.__dict__
    convert(cmdgelfile, cmdargs)

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
