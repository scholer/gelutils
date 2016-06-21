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

Requires Pillow version 2.7 (NOT version 3.0 or above!)


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
    from PIL.TiffImagePlugin import OPEN_INFO, II
    OPEN_INFO[(II, 0, 1, 1, (16,), ())] = ("I", "I;16")
Then:
    from PIL import Image
    Image.open(fp)

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

MORE PILLOW refs:
    http://pillow.readthedocs.org/en/latest/handbook/writing-your-own-file-decoder.html
    http://pillow.readthedocs.org/en/latest/handbook/image-file-formats.html
    https://pillow.readthedocs.org/handbook/concepts.html


Alternatives to using PIL:

MATPLOTLIB:
* Is suggested by: http://stackoverflow.com/questions/15284601/python-pil-struggles-with-uncompressed-16-bit-tiff-images

TIFFLIB:
* Christoph Gohlke's tifffile module
* http://stackoverflow.com/questions/18446804/python-read-and-write-tiff-16-bit-three-channel-colour-images

CV2 (+numpy):
* http://blog.philippklaus.de/2011/08/handle-16bit-tiff-images-in-python/  [uses old Pillow]

SciPy alone:
* http://docs.scipy.org/doc/scipy-0.14.0/reference/ndimage.html
* http://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.ndimage.interpolation.rotate.html

# For more on numpy dtypes:
#   http://docs.scipy.org/doc/numpy/reference/arrays.dtypes.html
#   http://docs.scipy.org/doc/numpy/reference/generated/numpy.dtype.html
#   http://docs.scipy.org/doc/numpy/reference/arrays.scalars.html


"""

from __future__ import print_function, absolute_import
from six import string_types # python 2*3 compatability
import os
import glob
import re
from itertools import cycle, chain

#from functools import partial
import numpy
import PIL
from PIL import Image#, TiffImagePlugin
from PIL.Image import NEAREST, ANTIALIAS, BICUBIC, BILINEAR # pylint: disable=W0611
from PIL.Image import FLIP_LEFT_RIGHT, FLIP_TOP_BOTTOM, ROTATE_90, ROTATE_180, ROTATE_270 # pylint: disable=W0611
from PIL import ImageOps
from PIL.TiffImagePlugin import OPEN_INFO, II
# from PIL.TiffImagePlugin import BITSPERSAMPLE, SAMPLEFORMAT, EXTRASAMPLES, PHOTOMETRIC_INTERPRETATION, FILLORDER, OPEN_INFO

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

# Local imports
from .utils import init_logging, printdict, getrelfilepath, getabsfilepath, setIfNone, ensure_numeric
from .argutils import parseargs, mergedicts

# PIL.Image.Image.convert has a little info on image modes.
# Adjust PIL so that it will open .GEL files:
# GEL image mode; using same as for PhotoInterpretation=1 mode.
# (ByteOrder, PhotoInterpretation, SampleFormat, FillOrder, BitsPerSample,  ExtraSamples) => mode, rawmode
# See https://pillow.readthedocs.org/handbook/concepts.html
# Format is <bitmode>[;[bits][S][R][I], where
# <bitmode> is {'1': 'monotone, 1-bit', 'L': 'Long, 8-bit', 'I': 'Integer, 32 or 16-bit', 'P': 'Palette', plus some bitmodes for RGB... }
# [bits] specifies number of bits (if different from default), e.g. "I;16" is 16-bit integer while "I" is 32-bit.
# S = signed (otherwise unsigned), R = reversed bilevel, I = Inverted (0 means white)
gelfilemodes = {
        #(II, 0, 1, 1, (16,), ()): ("I;16", "I;16"),    # Gives problems with negative numbers.
        #(II, 0, 1, 1, (16,), ()): ("I;16S", "I;16S"), # "Unrecognized mode"
        #(II, 0, 1, 1, (16,), ()): ("I;16N", "I;16N"), # "Unrecognized mode"
        #(II, 0, 1, 1, (16,), ()): ("I", "I"), # "IOError: image file is truncated." - because it expects 32-bit and image is 16-bit.
        (II, 0, 1, 1, (16,), ()): ("I", "I;16"), # THIS WORKS. Well, at least it does not produce negative numbers. I can put any value.
        #(II, 0, 1, 1, (16,), ()): ("I", "I;16I"), # What about this? - Nope, "unknown raw mode"
        #(II, 0, 1, 1, (16,), ()): ("I;16", "I;16"), # This also works, but we get error when saving PNG: "cannot write mode I;16 as PNG" (but I can change the output mode). But this also yields errors when rotating at right angels.
        #(II, 0, 1, 1, (16,), ()): ("F", "F;32F"), # "IOError: image file is truncated.
        #(II, 0, 1, 1, (16,), ()): ("I;32", "I;32N") # "Unrecognized mode"
        #(II, 0, 1, 1, (16,), ()): ("I", "I;32N") # This produces an IOError during load()
        #(II, 1, 1, 1, (32,), ()): ("I", "I;32N")
        }

OPEN_INFO.update(gelfilemodes)  # Update the OPEN_INFO dict; is used to identify TIFF image modes.

PIL_VERSION = Image.VERSION
PIL_IS_PILLOW = getattr(Image, 'PILLOW_VERSION', False)

# Note: logging might not have been initialized yet...:
logger.info("PIL version: %s || PILLOW? - %s", PIL_VERSION, PIL_IS_PILLOW)
print("PIL version: %s || PILLOW? - %s" % (PIL_VERSION, PIL_IS_PILLOW))


def get_mode_minmax(mode):
    """
    Determine the maximum values for the specified image mode.
    E.g. for a 32-bit integer image mode, the max value is 2**32-1.
    """
    # For float we set bit to 1 so that maxval becomes 1.0 .
    # For now, we assume that 'I' is 16 bit, otherwise it won't work...
    imgmode_to_bits = {'I': 16, 'I;16': 16, 'L': 8, '1': 1, 'F': 1.0}
    try:
        bits = imgmode_to_bits[mode]
    except KeyError:
        # Fall back to only using the first character in mode:
        bits = imgmode_to_bits[mode[0]]
    if 'S' in mode:
        # signed, reduce bits by 1:
        maxval = 2**(bits-1) - 1
        minval = -maxval
    else:
        minval, maxval = 0, 2**bits - 1
    return minval, maxval

def get_bits_mode_dtype(mode):
    """
    Returns tuple of
        (pixel_bits, pil_mode, numpy_dtype)
    """
    imgmode_to_bits = {'I': 32, 'L': 8}
    bits_to_imgmode = {8: 'L', 32: 'I'} # These are the only two supported afaik.
    try:
        # If mode is an integer:
        bits = int(mode)
        pil_mode = bits_to_imgmode[bits]
        dtype = 'int'+str(bits)   # e.g. 'int8'.
    except ValueError:
        # mode is not an integer, probably PIL image mode:
        bits = int(imgmode_to_bits[mode])
        dtype = 'int'+str(bits)   # e.g. 'int8'.
        pil_mode = mode
    return bits, pil_mode, dtype



def get_PMT(img):
    """
     (33449, <Scan Info>)
    """
    if isinstance(img, string_types):
        scaninfo = img
    else:
        try:
            scaninfo = img.tag[33449]
        except (KeyError, AttributeError):
            logger.info("Could not extract scaninfo (tag 33449) from image.")
            return
    prog = re.compile(r'(\d{3})\s?V')
    alllines = scaninfo.split('\n')
    pmtlines = [line for line in alllines if 'PMT=' in line]
    matches = (prog.search(line) for line in chain(pmtlines, alllines))
    matches = (match.group(0) for match in matches if match)
    return next(matches, None)
    #for line in pmtlines+alllines:
    #    match = prog.match(line)
    #    if match:
    #        return match.groups()[0]

def has_PMT(filename):
    """
    Returns whether filename has photomultipler designation in filename.
    E.g. "Agarose 500 V.gel", "Agarose_500V.gel", "Agarose_500_V_gel1.gel"
    """
    prog = re.compile(r'.*\d{3}[_\s]?[Vv].*')
    return prog.match(filename)


def find_dynamicrange(npdata, cutoff=(0, 0.99), roundtonearest=None, converter='auto'):
    """
    Try to determine the range given the numpy data, so that the
    values within the cutoff fraction is within the dynamic range,
    and the fraction of values above and below the cutoff is beyond the dynamic range.
    I.e. for a cutoff of (0.02, 0.95), this function will return a dynamic range
    that will quench the lowest 2% and the top 5%.
    """
    if roundtonearest in (None, True):
        roundtonearest = 1000
    counts, bins = numpy.histogram(npdata, bins=100)        # pylint: disable=E1101
    total = sum(counts)
    cutoffmin = 0 # Currently, this is hard-coded...
    #print counts.cumsum()
    try:
        binupper = next(i for i, cumsum in enumerate(counts.cumsum()) if cumsum > total*cutoff[1])
        cutoffmax = int(bins[binupper]) # Must return int
        logger.debug("Cutoffmax: %s", cutoffmax)
    except StopIteration:
        cutoffmax = cutoff*npdata.max()
        logger.debug("Could not find any bins, setting cutoffbin to %s", cutoffmax)
    logger.debug("(cutoffmin, cutoffmax): %s", (cutoffmin, cutoffmax))
    dr = [cutoffmin, cutoffmax]
    if converter in ('auto', None):
        # If converter is not specified, find a suitable converter function
        if dr[1] > 10:
            if roundtonearest:
                converter = lambda x: int(round(float(x)/roundtonearest)*roundtonearest)
            else:
                converter = int
        else:
            converter = lambda x: x
    return [converter(x) for x in dr]


def processimage(gelimg, args=None, linearize=None, dynamicrange=None, invert=None,
                 crop=None, rotate=None, scale=None, **kwargs):          # pylint: disable=R0912
    """
    gelimg is a PIL Image file, not just a path.
    Linearizes all data points (pixels) in gelimg.
    gelimg should be a PIL.Image.Image object.
    crop is a 4-tuple box:
        (x1, y1, x2, y2)
        (1230, 100, 2230, 800)

    Args:
        :gelimg: PIL Image file - not just a path.
        :args:  Config dict with default args, overwritten by kwargs
        :linearize: If True, will apply GEL-to-TIFF linearization (for e.g. Typhoon gel files)
        :dynamicrange: Cut the data at these thresholds. Tuple of (lower, upper).
        :invert: Invert data such that low data values appear whiter (high image values), i.e. "dark bands on white background".
        :crop:  4-tuple of (left, top, right, bottom) used to crop the image.
        :rotate: rotate image by this amount (degrees).
        :scale: scale the image by this factor.
        :kwargs: Further kwargs used to alter behaviour, e.g.:
            :cropfromedges: Instead of crop <right> and <bottom> being absolute values (from upper left corner),
                            crop the amount from the right and bottom edge.
            :flip_h: Flip image horizontally left-to-right using Image.transpose(PIL.Image.FLIP_LEFT_RIGHT)
            :flip_v: Flip image vertically top-to-bottom using Image.transpose(PIL.Image.FLIP_TOP_BOTTOM)
            :transpose: (advanced) Transpose image using Image.transpose(:transpose:)

    Returns
        linimg, info
    where <linimg> is the processed image (linearized, cropped, rotated,
    scaled, adjusted dynamic range, etc), and <info> is a dict with various
    image information, e.g.
    """
    stdargs = dict(linearize=linearize, dynamicrange=dynamicrange, invert=invert, crop=crop, rotate=rotate, scale=scale)
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

    ## unpack essentials (that are not changed):
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
        # Extract scaninfo and scalefactors:
        scaninfo = gelimg.tag[33449]
        scalefactor = gelimg.tag.getscalar(33446) # or tifimg.tag.tags[33446][0]
    except (AttributeError, KeyError):
        # AttributeError if gelimg does not have .tag attribute (e.g. PNG file),
        # KeyError if .tag dict does not include 33449 key (e.g. TIFF file)
        scaninfo = ""
        scalefactor = None
    pmt = get_PMT(scaninfo)
    info.update({'width': width, 'height': height, 'pmt': pmt, 'scalefactor': scalefactor, 'scaninfo': scaninfo})
    logger.debug("Gel scaninfo: %s", scaninfo)
    logger.debug("Image info dict: %s", info)

    if args['rotate']:
        # PIL resample filters:: NONE = NEAREST = 0; ANTIALIAS = 1; LINEAR = BILINEAR = 2; CUBIC = BICUBIC = 3
        # PIL/Pillow rotate only supports NEAREST, BILINEAR, BICUBIC resample filters.
        # Using BICUBIC resampling produces white/squashed pixels for saturated areas, so only using bilinear resampling.
        logger.info("Rotating image by angle=%s degrees (resample=BILINEAR, expand=%s)",
                    args['rotate'], args.get('rotateexpands'))
        gelimg = gelimg.rotate(angle=args['rotate'], resample=BILINEAR, expand=args.get('rotateexpands'))
        width, height = gelimg.size # Update, in case rotateexpands is True. # = widthheight

    if args.get('flip_h'):
        # :flip_h: Flip image horizontally left-to-right using Image.transpose(PIL.Image.FLIP_LEFT_RIGHT)
        logger.info("Flipping image horizontally using gelimg.transpose(FLIP_LEFT_RIGHT)")
        gelimg = gelimg.transpose(PIL.Image.FLIP_LEFT_RIGHT)
    if args.get('flip_v'):
        # :flip_v: Flip image vertically top-to-bottom using Image.transpose(PIL.Image.FLIP_TOP_BOTTOM)
        logger.info("Flipping image vertically using gelimg.transpose(FLIP_TOP_BOTTOM)")
        gelimg = gelimg.transpose(PIL.Image.FLIP_TOP_BOTTOM)
    if args.get('transpose'):
        # :transpose: (advanced) Transpose image using Image.transpose(:transpose:)
        logger.info("Transposing image using gelimg.transpose(%s)", args['transpose'])
        gelimg = gelimg.transpose(args['transpose'])

    if args['crop']:
        # crop is 4-tuple of (left, upper, right, lower)
        #crop = args['crop']
        #if isinstance(crop, string_types) and ',' in crop:
        #    # Maybe the user provided crop as a string: "left, top, right, lower"
        #    crop = [item.strip() for item in crop.split(',')]
        #    logger.debug("Converted input crop arg '%s' to: %s", args['crop'], crop)
        #crop = (float(x.strip('%'))/100 if isinstance(x, string_types) and '%' in x else x for x in crop)
        ## convert fraction values ("0.05") to absolute pixels:
        #crop = [int(widthheight[i % 2]*x) if x < 1 else x for i, x in enumerate(crop)]
        left, upper, right, lower = crop = ensure_numeric(args['crop'], cycle([width, height]))
        if args.get('cropfromedges'):
            if width-right <= left or height-lower <= upper:
                raise ValueError("Wrong cropping values: width-right <= left or height-lower <= upper: "\
                                 "%s-%s <= %s or %s-%s <= %s", width, right, left, height, lower, upper)
            logger.debug("Cropping image to: %s", (left, upper, width-right, height-lower))
            gelimg = gelimg.crop((left, upper, width-right, height-lower))
        else:
            if right <= left or height-lower < upper:
                raise ValueError("Wrong cropping values: right <= left or lower <= upper: "\
                                 "%s <= %s or %s <= %s", right, left, lower, upper)
            logger.debug("Cropping image to: %s", (left, upper, right, lower))
            gelimg = gelimg.crop(crop)
        width, height = widthheight = gelimg.size # Update (for use with e.g. scale/resize)

    # Which order to do operations:
    # Rotate first, because we need as much information as possible, and if rotateexpands=True then we might get some white areas we want to trim with crop.
    # scale before or after crop?
    # - If using relative values, this shouldn't matter much...
    scale = args.get('scale')
    if scale:
        # convert percentage values to fractional, if relevant:
        #scale = ensure_numeric(args['scale'])
        #scale = float(args['scale'].strip('%'))/100 if isinstance(args['scale'], string_types) and '%' in args['scale'] \
        #        else args['scale']
        # convert fractional values (e.g. 0.05) to absolute pixels, if relevant:
        ## TODO: There seems to be an issue with resize, similar to rotate. Changed ANTIALIAS to BILINEAR
        newsize = [ensure_numeric(scale, width), ensure_numeric(scale, height)]
        logger.info("Resizing image by a factor of %s (%s) to %s using resample=%s", scale, args['scale'], newsize, ANTIALIAS)
        gelimg = gelimg.resize(newsize, resample=BILINEAR)
        width, height = widthheight = gelimg.size


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
            info['extrema_post'] = gelimg.getextrema()  # getextrema() will actually load the image.
            return modimg or gelimg, info
        except IOError as e:
            logger.info("""Could not use PIL ImageOps to perform requested operations, "%s"
                        -- falling back to standard numpy.""", e)


    ### IMAGE MODE ###
    # https://pillow.readthedocs.org/handbook/concepts.html
    # 'I' = 32-bit signed integer, 'F' = 32-bit float, 'L' = 8-bit
    npimgmode = gelimg.mode # Default is 'I' for GEL and TIFF, 'L' for grayscale PNG.
    logger.debug("Original PIL image mode: '%s'", npimgmode)
    output_bits, output_mode, output_dtype = get_bits_mode_dtype(args.get('png_mode', 'L'))


    ### LINEARIZE, using numpy to do pixel transforms: ###
    if args['linearize'] and scalefactor:
        # Default numpy value is int32 (signed).
        # We need to specify that we want 32-bit *unsigned* intergers;
        # otherwise values above 2**15*sqrt(2) gets squashed to negative values when we square the values.
        npimg = numpy.array(gelimg, dtype=numpy.uint32) # Which dtype is better, float32 or uint32? # pylint: disable=E1101
        #npimg = numpy.array(gelimg, dtype=numpy.float32) # Which dtype is better, float32 or uint32? # pylint: disable=E1101
        # TODO: Do performance test to see if float32 is better than uint32
        #       And remember to alter mode when you return to Image.fromarray
        logger.debug('Linearizing gel data using scalefactor %s...', scalefactor)
        logger.debug('npimg min, max before linearization: %s, %s', npimg.min(), npimg.max())
        npimg = (npimg**2)/scalefactor[1]
        logger.debug('npimg min, max after linearization: %s, %s', npimg.min(), npimg.max())
        # You can use npimg.astype(<dtype>) to convert to other dtype:
        # We need to cast to lower or we cannot save back (at least for old PIL;
        # Pillow might handle 16-bit grayscale better?
        #npimg = npimg.astype('int32') # Maybe better to do this conversion later, right before casting back?
        logger.debug('npimg min, max after casting to int32: %s, %s', npimg.min(), npimg.max())
        # Can we simply set/adjust the image mode used when we return from npimg to pilimg?
        #npimgmode = 'I;32' # or maybe just set the npimagemode?
        # 'I;32' doesn't work. 'I;16' does. Support seems flaky. https://github.com/python-pillow/Pillow/issues/863
        # Maybe we should go even lower and force 8-bit grayscale? (That is more than enough for visual inspection!)
        # ...but how low?
        # For more on image modes, https://pillow.readthedocs.org/handbook/concepts.html
        # Note: Make sure whether you are using PIL or Pillow before you go exploring - PIL.PILLOW_VERSION
    else:
        npimg = numpy.array(gelimg) # Do not use getdata(), just pass the image. # pylint: disable=E1101



    ### Preview with matplotlib: Linearized image before adjusting dynamic range
    # Useful for debugging and other stuff:
    if args.get('image_plot_before_dr_adjust', False):
        # Consider ensuring that the backend is tkinter (however, that should probably be done by the GUI)
        #from matplotlib import backends, get_backend, use as use_backend
        import matplotlib
        # Use matplotlib.get_backend() to check current backend; See matplotlib.backend for available backends.
        matplotlib.use('tkagg')     # Must be invoked before loading pyplot
        from matplotlib import pyplot
        pyplot.ioff()    # Disable interactive mode.
        imgplot = pyplot.imshow(npimg)
        pyplot.colorbar()
        pyplot.hold(False)
        pyplot.show()
        imgplot.remove()


    ### ADJUST DYNAMIC RANGE ###

    dr = args.get('dynamicrange')
    ## Do automatic calculation of dynaic range if requested or needed:
    if dr == 'auto' or (args['invert'] and not dr) or args.get('dr_auto_cutoff'):
        # If we want to invert, we need to have a range. If it is not specified, we need to find it.
        logger.debug("Dynamic range is %s (args['invert']=%s)", dr, args['invert'])
        cutoff = ensure_numeric(args.get('dr_auto_cutoff', [0, 0.99]))
        dr = args['dynamicrange'] = find_dynamicrange(npimg, cutoff=cutoff)
        logger.debug("--- determined dynamic range: %s", dr)

    if dr:
        dr = ensure_numeric(dr)
        if isinstance(dr, (int, float)):
            # If we have only provided a single argument, assume it is dr_high and set low to 0.
            dr = args['dynamicrange'] = [0, dr]

        ## Dynamic range can be given as absolute values or relative "cutoff";
        ## The cutoff is the percentage of pixels below/above the dynamic range.
        ## Convert relative values: First, convert % to fraction:
        #dr = (float(x.strip('%'))/100 if isinstance(x, string_types) and '%' in x else x for x in dr) # pylint: disable=E1103
        ## convert (0.05, 0.95) to absolute range:
        ## Note: What if you have floating-point pixel values between 0 and 1? (E.g. for HDR images).
        ## In that case, the dynamic range might not be distribution ranges but actual min/max pixel values.
        ## Adding new argument 'dynamicrange_is_absolute' which can be used to force interpreting dynamicrange as absolute rather than relative cutoff.
        ## Edit: It might be better to have args: dr_autocalc_cutoff!!
        #if all(x < 1 for x in dr) and not args.get('dynamicrange_is_absolute'):
        #    logger.debug("Finding dynamic range for cutoff %s (args['dynamicrange']=%s)", dr, args['dynamicrange'])
        #    dr = map(int, find_dynamicrange(npimg, cutoff=dr, roundtonearest=args.get('dynamicrange_round')))
        #    logger.debug("--- determined dynamic range: %s", dr)


        # Transform image so all values < dynamicrange[0] is set to 0,
        # all values > dynamicrange[1] is set to the imagemode's max value,
        # and all values in between are scaled accordingly.
        logger.debug("args['dynamicrange']: %s; derived dr: %s", args['dynamicrange'], dr)
        logger.debug('npimg min, max before adjusting dynamic range: %s, %s', npimg.min(), npimg.max())
        # When we adjust the dynamic range, the minimum and maximum depends on the output image mode:
        # For 16-bit unsigned output, maxval is 2**16-1; for 8-bit unsigned output, it is 2**8-1:
        minval, maxval = get_mode_minmax(output_mode)
        dr_low, dr_high = info['dynamicrange'] = dr
        logger.debug("Output minval, maxval: %s, %s", minval, maxval)
        logger.debug("Dynamic range (dr_low, dr_high): %s, %s", dr_low, dr_high)
        # Define closure to adjust the values, depending on whether to invert the image:
        if args['invert']:
            logger.debug('Using adjust_fun that will invert the pixel values...')
            def adjust_fun(val):
                """ Function to adjust dynamic range of image, inverting the image in the process. """
                if val <= dr_low:
                    return maxval # This is correct when we are inverting the image.
                elif val >= dr_high:
                    return minval # This is correct when we are inverting the image.
                # This might also be an issue: maxval*70000 > 2**32 ??
                return (maxval*(dr_high-val))/(dr_high-dr_low)
        else:
            def adjust_fun(val):
                """ Function to adjust dynamic range of image. """
                if val <= dr_low:
                    return minval # I would expect this to be the correct behaviour?
                    #return int(0.66*maxval)
                    # When we are at very high values, we get this? -- confirmed. (And we also get it for low values < dr_low...)
                    # Try it by doing numpy.array(gelimg) or numpy.asarray(gelimg)
                    # Note that numpy "flips" the y-axis of the image relative to how it is treated by PIL.
                    # And, in numpy the indexing is reversed.
                    #return int(0.50*maxval)
                elif val >= dr_high:
                    return maxval # I would expect this to be the correct behaviour?
                    #return int(0.33*maxval)
                    #return int(0.80*maxval)
                    #return int(0.33*minval)
                else:
                    # return maxval*(val-dr_low)/(dr_high-dr_low)+minval
                    return int(float(maxval)*(val-dr_low)/(dr_high-dr_low)+minval)
        # Numpy adjustment:
        # Note: This seems correct when I try it manually and plot it.
        adjust_vec = numpy.vectorize(adjust_fun)    # pylint: disable=E1101
        npimg = adjust_vec(npimg)
        npimgmode = output_mode
        logger.debug('npimg min, max after adjusting dynamic range: %s, %s', npimg.min(), npimg.max())


    # Preview with matplotlib: After adjusting dynamic range
    if args.get('image_plot_after_dr_adjust', False):
        from matplotlib import pyplot
        imgplot = pyplot.imshow(npimg)
        pyplot.colorbar()
        pyplot.show()
        imgplot.remove()

    #npimg = npimg.astype('int32')
    #npimg = npimg.astype('uint32')
    #npimg = npimg.astype('uint8') # If output_mode is 'L', this needs to be int8 or uint8.
    npimg = npimg.astype(output_dtype) # If output_mode is 'L', this needs to be int8 or uint8.


    # Maybe this is what gives the problem? No, also seems good.
    # Is it the linearization?
    #linimg = Image.fromarray(npimg, gelimg.mode)
    logger.debug("Reverting back to PIL image using image mode '%s'", npimgmode)
    try:
        linimg = Image.fromarray(npimg, npimgmode)
    except ValueError as e:
        # For PNG, the only accepted image modes are I, I;16 and L.
        logger.error("Unable to convert npimage to PIL image using image mode '%s': %s", npimgmode, e)
        raise ValueError(e)

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



def convert(gelfile, args, yamlfile=None, lanefile=None, **kwargs):   # (too many branches and statements, bah) pylint: disable=R0912,R0915
    """
    Converts gel file to png given the info in args (using processimage to apply transformations).
    Args:
    :gelfile: <str> file path pointing to a gel file.
    :args: forwarded to get_gel/processimage together with gelfile to load gelfile data and apply image transformations.

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
        logger.debug("Gel file input detected (extension '%s') -> enabling linearize and invert if not specified.", gelext)
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
    print("Loaded gelfile:", gelfile)
    print("Gel info: ", ", ".join("{}: {}".format(k, v) for k, v in info.items()))
    # Use orgimg for info, e.g. orgimg.info and orgimg.tag
    #logger.debug("get_gel returned with ")
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
                rng = "{}-{}k".format(*(int(i/1000) for i in dr))
            else:
                rng = "{}-{}k".format(int(dr[0]), int(dr[1]/1000))
        else:
            rng = "{}-{}".format(*(int(i) for i in dr))

    if not args.get('convertgelto'):
        args['convertgelto'] = 'png'
    ext = '.'+args['convertgelto']

    # Calculate existing. basename is gelfile minus extension but with directory:
    if not args.get('overwrite', True):
        N_existing = "_{}".format(len(glob.glob(basename+'*.'+ext)))
    else:
        N_existing = ""
    pngfnfmt_default = u'{gelfnroot}_{dr_rng}{N_existing}{ext}'
    if not has_PMT(basename) and info.get('pmt'):
        pngfnfmt_default = u'{gelfnroot}_{pmt}V_{dr_rng}{N_existing}{ext}'

    ## Make pngfilename ##
    pngfnfmt = args.get('pngfnfmt', pngfnfmt_default)
    yamlfnroot = os.path.splitext(os.path.basename(yamlfile))[0] if yamlfile else args.get('yamlfile', '')
    lanefnroot = os.path.splitext(os.path.basename(yamlfile))[0] if lanefile else args.get('lanefile', '')
    pngfilename = pngfnfmt.format(gelfnroot=basename, pmt=info['pmt'], dr_rng=rng,
                                  lanefnroot=lanefnroot, yamlfnroot=yamlfnroot,
                                  N_existing=N_existing, ext=ext)

    if args.get('filename_substitution'):
        try:
            find, replace = args.get('filename_substitution')
        except ValueError:
            print("ERROR: filename_substitution must be a list of length 2. Will not perform filename_substitution.")
        else:
            if find in pngfilename:
                logger.info("filename_substitution: replacing '%s' with '%s' in %s", find, replace, pngfilename)
                pngfilename = pngfilename.replace(*args.get('filename_substitution'))
                logger.debug("New pngfilename: %s", pngfilename)

    # The 'pngfile' in args is relative to the gelfile,
    # But when you save, it should be absolute:
    pngfilename = getabsfilepath(gelfile, pngfilename)
    pngfilename_relative = getrelfilepath(gelfile, pngfilename)
    logger.debug("pngfilename: %s", pngfilename)
    logger.debug("pngfilename_relative: %s", pngfilename_relative)
    logger.debug("Saving converted gel image to: %s", pngfilename)
    # Note: gelimg may be in 16-bit; saving would produce a 16-bit grayscale PNG.
    # Image size can possibly be reduced by 50% by saving as 8-bit grayscale.
    gelimg.save(pngfilename)
    # Note: 'pngfile' may also be a jpeg file, if the user specified convertgelto: jpg
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
