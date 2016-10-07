#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright 2014-2016 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
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

# pylint: disable=W0141,W0142,C0103,R0913,R0914

"""

Module for transforming gel images: converting, mapping, cropping, etc.

Requires Pillow version 2.7 (NOT version 3.0 or above!)


About .GEL files (from e.g. Typhoon scanners):
* Data structure like TIFF file
* Created by: Amersham Biosciences
* Owner: GE Healthcare Life Sciences
* Developer: Molecular Dynamics
* Name: Molecular Dynamics GEL file format, see http://www.awaresystems.be/imaging/tiff/tifftags/docs/gel.html
* AKA: amersham-biosciences-gel, "Square-Root Encoded Data"
* Pixel data is encoded as: stored_value = sqrt(intensity)/scale,
* where scale factor is stored in file metadata, MD_ScalePixel tag code 332446
* Decode pixel data as: actual_value = scale * stored_value^2
* Default Scale factor value: 21025 - 1/scale = 1/21025 = 4.75624256837099E-5


See also:
* http://www.awaresystems.be/imaging/tiff/tifftags/docs/gel.html
* http://www.openmicroscopy.org/site/support/bio-formats5.1/formats/amersham-biosciences-gel.html
* http://www.openmicroscopy.org/site/support/bio-formats5.1/metadata/BioRadGelReader.html
* http://www.openmicroscopy.org/site/support/bio-formats5.1/formats/bio-rad-gel.html
* https://github.com/openmicroscopy/bioformats/blob/v5.1.10/components/formats-gpl/src/loci/formats/in/GelReader.java


 CURRENT STATUS:
-----------------

It works, but I'm having problems linearizing the data because PIL wants
to fit the data into its own range.

It might be better to

Or skip PIL all together and use something else.



 READING .GEL FILES:
---------------------

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


 USING PIL:
------------

To open with PIL:
    from PIL.TiffImagePlugin import OPEN_INFO, II
    OPEN_INFO[(II, 0, 1, 1, (16,), ())] = ("I", "I;16")
Then:
    from PIL import Image
    Image.open(fp)

See tags with: sorted(tifimg.tag.items())
Use http://www.awaresystems.be/imaging/tiff/tifftags/search.html to identify tiff tags.
* MD FileTag: http://www.awaresystems.be/imaging/tiff/tifftags/mdfiletag.html
* MD ScalePixel: http://www.awaresystems.be/imaging/tiff/tifftags/mdscalepixel.html
Interesting tags are:
 (33445, (2,)), # MD FileTag. Specifies the pixel data format encoding in the Molecular Dynamics GEL file format.
 (33446, ((1, 21025),)), # MD ScalePixel. Specifies a scale factor in the Molecular Dynamics GEL file format.
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
----------------------------

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
from six import string_types  # python 2*3 compatability
import os
import glob
import re
from itertools import cycle, chain
import numpy
import PIL
from PIL import Image  # , TiffImagePlugin
from PIL.Image import BILINEAR  # , NEAREST, ANTIALIAS, BICUBIC  # pylint: disable=W0611
# from PIL.Image import FLIP_LEFT_RIGHT, FLIP_TOP_BOTTOM, ROTATE_90, ROTATE_180, ROTATE_270 # pylint: disable=W0611
from PIL import ImageOps
from PIL.TiffImagePlugin import OPEN_INFO, II
# from PIL.TiffImagePlugin import BITSPERSAMPLE, SAMPLEFORMAT, EXTRASAMPLES, PHOTOMETRIC_INTERPRETATION, FILLORDER
import logging

# Local imports
from .utils import init_logging, printdict, getrelfilepath, getabsfilepath, ensure_numeric, mergedicts
from .argutils import parseargs

logging.addLevelName(4, 'SPAM')  # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)
# flush keyword only supported for python 3.3+, so create custom print function:
# Edit: Instead of modifying print to accept flush keyword, just make sure to use line-buffering for file objects

# PIL.Image.Image.convert has a little info on image modes.
# Adjust PIL so that it will open .GEL files:
# GEL image mode; using same as for PhotoInterpretation=1 mode.
# (ByteOrder, PhotoInterpretation, SampleFormat, FillOrder, BitsPerSample,  ExtraSamples) => mode, rawmode
# See https://pillow.readthedocs.org/handbook/concepts.html
# Format is <bitmode>[;[bits][S][R][I], where <bitmode> is:
# {'1': 'monotone, 1-bit', 'L': 'Long, 8-bit', 'I': 'Integer, 32 or 16-bit', 'P': 'Palette', plus bitmodes for RGB... }
# [bits] specifies number of bits (if different from default), e.g. "I;16" is 16-bit integer while "I" is 32-bit.
# S = signed (otherwise unsigned), R = reversed bilevel, I = Inverted (0 means white)
gelfilemodes = {
    # (II, 0, 1, 1, (16,), ()): ("I;16", "I;16"),    # Gives problems with negative numbers.
    # (II, 0, 1, 1, (16,), ()): ("I;16S", "I;16S"), # "Unrecognized mode"
    # (II, 0, 1, 1, (16,), ()): ("I;16N", "I;16N"), # "Unrecognized mode"
    # (II, 0, 1, 1, (16,), ()): ("I", "I"), # "IOError: image file is truncated" - it expects 32-bit, image is 16-bit.
    (II, 0, 1, 1, (16,), ()): ("I", "I;16"),  # THIS WORKS. Does not produce negative numbers. I can put any value.
    # (II, 0, 1, 1, (16,), ()): ("I", "I;16I"), # What about this? - Nope, "unknown raw mode"
    # Below also works, but we get error when saving PNG: "cannot write mode I;16 as PNG"
    # (but I can change the output mode). But this also yields errors when rotating at right angels.
    # (II, 0, 1, 1, (16,), ()): ("I;16", "I;16"),
    # (II, 0, 1, 1, (16,), ()): ("F", "F;32F"), # "IOError: image file is truncated.
    # (II, 0, 1, 1, (16,), ()): ("I;32", "I;32N") # "Unrecognized mode"
    # (II, 0, 1, 1, (16,), ()): ("I", "I;32N") # This produces an IOError during load()
    # (II, 1, 1, 1, (32,), ()): ("I", "I;32N")
}

OPEN_INFO.update(gelfilemodes)  # Update the OPEN_INFO dict; is used to identify TIFF image modes.

PIL_VERSION = Image.VERSION
PIL_IS_PILLOW = getattr(Image, 'PILLOW_VERSION', False)

# Note: logging might not have been initialized yet...:
logger.info("PIL version: %s || PILLOW? - %s", PIL_VERSION, PIL_IS_PILLOW)
print("PIL version: %s || PILLOW? - %s" % (PIL_VERSION, PIL_IS_PILLOW))


def assert_image(img):
    """Perform basic checks that the image data looks alright."""
    assert img is not None
    if isinstance(img, numpy.ndarray):
        assert len(img) > 0
        assert img.any()
        assert img.min() >= 0
        assert img.max() > 0
    elif isinstance(img, Image.Image):
        assert len(img.getdata()) > 0
        minval, maxval = img.getextrema()
        if minval < 0:
            print("\nWARNING, minval < 0: %s\n" % (minval,))
        assert minval >= 0
        assert maxval > 0
    else:
        raise TypeError("img has unextected type %s" % type(img))


def get_mode_minmax(mode):
    """Determine the maximum values for the specified image mode.

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
    """get PIL pixel bits, mode and numpy data type for a given mode.

    Return:
        3-Tuple with (pixel_bits, pil_mode, numpy_dtype)
    """
    imgmode_to_bits = {'I': 32, 'L': 8}
    bits_to_imgmode = {8: 'L', 32: 'I'}  # These are the only two supported afaik.
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


def get_pmt_string(img):
    """Return PMT (photomultiplier) information for a PIL image or scan-info tag.

    Tags are in the format of:
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


def has_pmt_string(filename):
    """Determine whether filename has photomultipler designation in filename.

    E.g. "Agarose 500 V.gel", "Agarose_500V.gel", "Agarose_500_V_gel1.gel" all have PMT in filename.
    """
    prog = re.compile(r'.*\d{3}[_\s]?[Vv].*')
    return prog.match(filename)


def find_dynamicrange(npdata, cutoff=(0, 0.99), roundtonearest=None, converter='auto'):
    """find a suitable dynamic range by looking at histogram of pixel values.

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
    cutoffmin = 0  # Currently, this is hard-coded...
    try:
        binupper = next(i for i, cumsum in enumerate(counts.cumsum()) if cumsum > total*cutoff[1])
        cutoffmax = int(bins[binupper])  # Must return int
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
                def converter(x):
                    return int(round(float(x)/roundtonearest)*roundtonearest)
            else:
                converter = int
        else:
            def converter(x):
                return x
    return [converter(x) for x in dr]


def adjust_dynamic_range(npimg, args, info, output_mode, dr=None):
    """Adjust dynamic range.
    This actually performs several functions:
        1. Clip values beyond dynamic range bounds and scale values in between linearly.
        2. Invert pixel values if specified (high bound becomes low bound, etc).
        3. Scale pixel values according to the specified output_mode.
    We do all three with a single, vectorized, function.
    """
    if args is None:
        args = {}
    if info is None:
        info = {}
    assert_image(npimg)
    if dr is None:
        dr = args.get('dynamicrange')
        # It is possible for both dr and args['dynamicrange'] to be None, in which case
        # we either auto-determine a dr by histogram cut-off, or we do nothing at all (except print a message).
    else:
        args['dynamicrange'] = dr

    # Do automatic calculation of dynaic range if requested or needed:
    # If "invert" is specified, we must apply a dynamic range to get a suitable picture.
    # (It is only possible to invert by assuming a maximum image pixel value, which depends on the image format.)
    if dr == 'auto' or (args.get('invert') and not dr) or args.get('dr_auto_cutoff'):
        # If we want to invert, we need to have a range. If it is not specified, we need to find it.
        logger.debug("Dynamic range is %s (args['invert']=%s)", dr, args['invert'])
        cutoff = ensure_numeric(args.get('dr_auto_cutoff', [0, 0.99]))
        dr = args['dynamicrange'] = find_dynamicrange(npimg, cutoff=cutoff)
        logger.debug("auto-determined dynamic range (after rounding): %s", dr)

    if not dr:
        logger.info("dynamicrange is %s, will not adjust dynamic range...")
        print("dynamicrange is %s, will not adjust dynamic range...")
        return

    dr = ensure_numeric(dr)
    if isinstance(dr, (int, float)):
        # If we have only provided a single argument, assume it is dr_high and set low to 0.
        dr = args['dynamicrange'] = [0, dr]

    # # Dynamic range can be given as absolute values or relative "cutoff";
    # # The cutoff is the percentage of pixels below/above the dynamic range.
    # # Convert relative values: First, convert % to fraction:
    # dr = (float(x.strip('%'))/100 if isinstance(x, string_types) and '%' in x else x for x in dr)
    # # convert (0.05, 0.95) to absolute range:
    # # Note: What if you have floating-point pixel values between 0 and 1? (E.g. for HDR images).
    # # In that case, the dynamic range might not be describing fractions, but actual min/max pixel values.
    # # Maybe add new argument 'dynamicrange_is_absolute' to flag that dynamicrange is absolute not relative cutoff.
    # # Or maybe just check if the maximum pixel value is low, e.g. < 2.
    # if all(x < 1 for x in dr) and not args.get('dynamicrange_is_absolute'):
    # #    logger.debug("Finding dynamic range for cutoff %s (args['dynamicrange']=%s)", dr, args['dynamicrange'])
    # #    dr = map(int, find_dynamicrange(npimg, cutoff=dr, roundtonearest=args.get('dynamicrange_round')))
    # #    logger.debug("--- determined dynamic range: %s", dr)

    # Clip pixel values so all values < dynamicrange[0] is set to 0,
    # all values > dynamicrange[1] is set to the imagemode's max value,
    # and all values in between are scaled accordingly.
    logger.debug("args['dynamicrange']: %s; derived dr: %s", args['dynamicrange'], dr)
    logger.debug('npimg min, max before adjusting dynamic range: %s, %s', npimg.min(), npimg.max())
    # When we adjust the dynamic range, the minimum and maximum depends on the output image mode:
    # For 16-bit unsigned output, maxval is 2**16-1; for 8-bit unsigned output, it is 2**8-1:
    if output_mode is None:
        # We cannot really know what value is the maximum. It may be 8-bit (255), 16-bit (65535), etc.
        # Just pick the maximum value as the maxval:
        # minval, maxval = npimg.min(), npimg.max()
        # logger.info("output_mode = %s, using npimg.min()/max() = (%s, %s) as minval/maxval."
        minval, maxval = 0, dr[1]
        logger.info("output_mode = %s, using 0, dr[1] = (%s, %s) as minval/maxval."
                    % (output_mode, minval, maxval))
    else:
        minval, maxval = get_mode_minmax(output_mode)
        logger.info("output_mode = %s, get_mode_minmax(output_mode) returned (%s, %s) as minval/maxval."
                    % (output_mode, minval, maxval))
    dr_low, dr_high = info['dynamicrange'] = dr
    logger.debug("Output minval, maxval: %s, %s", minval, maxval)
    logger.debug("Dynamic range (dr_low, dr_high): %s, %s", dr_low, dr_high)
    # Define closure to adjust the values, depending on whether to invert the image:
    if args.get('invert'):
        def adjust_fun(val):
            """ Function to adjust dynamic range of image, inverting the image in the process. """
            if val <= dr_low:
                return maxval  # This is correct when we are inverting the image.
            elif val >= dr_high:
                return minval  # This is correct when we are inverting the image.
            # This might also be an issue: maxval*70000 > 2**32 ??
            # Multiply maxval before or after division?
            # If we want to stay in the integer domain, we should multiply maxval before
            # otherwise the fraction will always interger-divide to equal zero.
            # However, if using signed integers, the the integer multiplication may wrap around to negative numbers.
            return maxval*((dr_high - val)/(dr_high - dr_low)) + minval
        logger.debug('Using adjust_fun that will invert the pixel values...')
    else:
        def adjust_fun(val):
            """ Function to adjust dynamic range of image. """
            if val <= dr_low:
                return minval
            elif val >= dr_high:
                return maxval
            else:
                # return maxval*(val-dr_low)/(dr_high-dr_low)+minval
                return maxval*((val - dr_low)/(dr_high - dr_low)) + minval
                # return int(float(maxval)*(val-dr_low)/(dr_high-dr_low)+minval)
    # Numpy adjustment:
    # Note: This seems correct when I try it manually and plot it.
    adjust_vec = numpy.vectorize(adjust_fun)    # pylint: disable=E1101
    npimg = adjust_vec(npimg)
    logger.debug('npimg min, max after adjusting dynamic range: %s, %s', npimg.min(), npimg.max())

    # Preview with matplotlib: (After adjusting dynamic range)
    if args.get('image_plot_after_dr_adjust', False):
        show_npimage(npimg, title="after_dr_adjust")

    return npimg


def linearize_pixel_values(gelimg, scalefactor):
    """Perform "linearization" of pixel values for GEL images stored in MD Tiff format.

    Background:
        Typhoon scanners have a dynamic range of 0–100_000.
        The TIFF file format has a 16-bit dynamic range, i.e. 0–2**16-1 or 0–65535.
        In an attempt to retain as much accuracy as possible, the MD Tiff format applies
        a conversion of all pixel values: p1 = scalefactor * sqrt(p0)  <= 65535
        where scalefactor is calculated such that the all p1 values are <= 65535.
        That is, scalefactor <= 65535/sqrt(max(P0))
        If max(P0) is 100_000, then sqrt(max(P0)) is 316.22 and scalefactor <= 207.
        Note that scalefactor is typically stored as a tuple, (1, scalefactor).

    Args:
        :param gelimg:
        :param scalefactor:

    Returns:
        image as numpy.ndarray
    """
    assert_image(gelimg)

    # Default numpy value is int32 (signed).
    # We need to specify that we want 32-bit *unsigned* intergers;
    # otherwise values above 2**15*sqrt(2) gets squashed to negative values when we square the values.
    # Which dtype is better, float32 or uint32?
    if isinstance(gelimg, numpy.ndarray):
        npimg = gelimg
    else:
        # Important: Make sure to use unsigned integer values, dtype=numpy.uint32.
        npimg = numpy.array(gelimg, dtype=numpy.uint32)  # pylint: disable=E1101
        # npimg = numpy.array(gelimg, dtype=numpy.float32)  # pylint: disable=E1101
        # TODO: Do performance test to see if float32 is better than uint32
    #       And remember to alter mode when you return to Image.fromarray
    logger.debug('Linearizing gel data using scalefactor %s...', scalefactor)
    logger.debug('npimg min, max before linearization: %s, %s', npimg.min(), npimg.max())
    npimg = (npimg**2)/scalefactor[1]
    logger.debug('npimg min, max after linearization: %s, %s', npimg.min(), npimg.max())
    # You can use npimg.astype(<dtype>) to convert to other dtype:
    # We need to cast to lower or we cannot save back (at least for old PIL;
    # Pillow might handle 16-bit grayscale better?
    # npimg = npimg.astype('int32') # Maybe better to do this conversion later, right before casting back?
    logger.debug('npimg min, max after casting to int32: %s, %s', npimg.min(), npimg.max())
    # Can we simply set/adjust the image mode used when we return from npimg to pilimg?
    # npimgmode = 'I;32' # or maybe just set the npimagemode?
    # 'I;32' doesn't work. 'I;16' does. Support seems flaky. https://github.com/python-pillow/Pillow/issues/863
    # Maybe we should go even lower and force 8-bit grayscale? (That is more than enough for visual inspection!)
    # ...but how low?
    # For more on image modes, https://pillow.readthedocs.org/handbook/concepts.html
    # Note: Make sure whether you are using PIL or Pillow before you go exploring - PIL.PILLOW_VERSION
    return npimg


def transform_image(gelimg, args):
    """Apply geometric image transformation - rotate, crop, flip/transpose, scale.

    Args:
        gelimg: image
        args: dict with "rotate", "crop", "transpose", "scale" entries.
            args dict may be updated in-place with auto-determined values, e.g. for rotate="auto".

    Returns:
        gelimg - transformed gel image.

    Which order to do operations:
    - rotate before cropping to reduce the white wedges from rotation:
    - Then crop, so cropping is relative to original image. But doesn't matter if using relative values...
    - Then flip/transpose
    - Then scale
    Except maybe if we are using rotate="auto" because then we prefer only to rotate after cropping and scaling...

    """
    assert_image(gelimg)

    if args['rotate'] and not isinstance(args['rotate'], str):
        # PIL resample filters:: NONE = NEAREST = 0; ANTIALIAS = 1; LINEAR = BILINEAR = 2; CUBIC = BICUBIC = 3
        # PIL/Pillow rotate only supports NEAREST, BILINEAR, BICUBIC resample filters.
        # BICUBIC resampling produces white/squashed pixels for saturated areas, so only using bilinear resampling.
        logger.info("Rotating image by angle=%s degrees (resample=BILINEAR, expand=%s)",
                    args['rotate'], args.get('rotateexpands'))
        gelimg = gelimg.rotate(angle=args['rotate'], resample=BILINEAR, expand=args.get('rotateexpands'))

    if args['crop']:
        # crop is 4-tuple of (left, upper, right, lower)
        # convert fraction values (0.05 or "5%") to absolute pixels:
        width, height = gelimg.size  # Update, in case rotateexpands is True. # = widthheight
        left, upper, right, lower = crop = ensure_numeric(args['crop'], cycle(gelimg.size))
        if args.get('cropfromedges'):
            if width-right <= left or height-lower <= upper:
                raise ValueError("Wrong cropping values: width-right <= left or height-lower <= upper: "
                                 "%s-%s <= %s or %s-%s <= %s", width, right, left, height, lower, upper)
            logger.debug("Cropping image to: %s", (left, upper, width-right, height-lower))
            gelimg = gelimg.crop((left, upper, width-right, height-lower))
        else:
            if right <= left or height-lower < upper:
                raise ValueError("Wrong cropping values: right <= left or lower <= upper: "
                                 "%s <= %s or %s <= %s", right, left, lower, upper)
            logger.debug("Cropping image to: %s", (left, upper, right, lower))
            gelimg = gelimg.crop(crop)
        if args.get('crop_update_to_absolute'):
            args['cropfromedges'] = False
            args['crop'] = [left, upper, right, lower]
            if args.get('crop_update_to_absolute') == "str":
                args['crop'] = ", ".join(map(str, args["crop"]))

    # Auto-rotation:
    # If we are using rotate="auto", then it is better to perform rotation after crop/scale but still before flip.
    if isinstance(args['rotate'], str):
        if args['rotate'].lower() == "auto":
            from .auto_rotate import find_optimal_rotation
            logger.info("Finding optimal rotation...")
            # Note: for optimize_rotation, bands should be white (high pixel values), not black:
            args['rotate'] = find_optimal_rotation(gelimg)
        else:
            logger.warning("Unknown value for 'rotate': %s", args['rotate'])
        logger.info("Rotating image by angle=%s degrees (resample=BILINEAR, expand=%s)",
                    args['rotate'], args.get('rotateexpands'))
        gelimg = gelimg.rotate(angle=args['rotate'], resample=BILINEAR, expand=args.get('rotateexpands'))

    # transform after cropping to make cropping coordinates be relative to original image (albeit after rotation)
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

    scale = args.get('scale')
    if scale:
        # convert percentage values to fractional, if relevant:
        # convert fractional values (e.g. 0.05) to absolute pixels, if relevant:
        # TODO: There seems to be an issue with resize, similar to rotate. Changed ANTIALIAS to BILINEAR
        width, height = gelimg.size
        newsize = [ensure_numeric(scale, width), ensure_numeric(scale, height)]
        logger.info("Resizing image by a factor of %s (%s) to %s, resample=%s", scale, args['scale'], newsize, BILINEAR)
        gelimg = gelimg.resize(newsize, resample=BILINEAR)

    return gelimg


def processimage(gelimg, args=None, linearize=None, dynamicrange=None, invert=None,
                 crop=None, rotate=None, scale=None, **kwargs):          # pylint: disable=R0912
    """process a given gel image (rotate, scale, crop, image contrast, etc).

    TODO: Split this function up into two parts:
        One function that transforms IMAGE GEOMETRY: rotate, crop, flip/transpose, scale.
        One function that transforms PIXEL VALUES: linearize, invert, apply contrast/dynamic_range.

    Args:
        gelimg: PIL.Image.Image object (i.e. not just a path).
        args:  Config dict with default args, overwritten by kwargs
        linearize: If True, will apply GEL-to-TIFF linearization for all data points (pixels) in gelimg
                (e.g. for Typhoon gel image files)
        dynamicrange: Cut the data at these thresholds. Tuple of (lower, upper).
        invert: Invert data such that low data values appear whiter (high image values),
                i.e. "dark bands on white background".
        crop:  4-tuple of (left, top, right, bottom) used to crop the image.
        rotate: rotate image by this amount (degrees).
        scale: scale the image by this factor.
        kwargs: Further kwargs used to alter behaviour, e.g.:
            cropfromedges: Instead of crop <right> and <bottom> being absolute values (from upper left corner),
                           crop the amount from the right and bottom edge.
            flip_h: Flip image horizontally left-to-right using Image.transpose(PIL.Image.FLIP_LEFT_RIGHT)
            flip_v: Flip image vertically top-to-bottom using Image.transpose(PIL.Image.FLIP_TOP_BOTTOM)
            transpose: (advanced) Transpose image using Image.transpose(:transpose:)

    Return:
        (pilimg, info)  2-tuple,
        where <pilimg> is the processed image (linearized, cropped, rotated,
        scaled, adjusted dynamic range, etc), and <info> is a dict with various
        image information, e.g.

    Notes and references:
        Info about PIL image modes: https://pillow.readthedocs.org/handbook/concepts.html

        numpy dtypes:
        * http://docs.scipy.org/doc/numpy/reference/arrays.dtypes.html
        * http://docs.scipy.org/doc/numpy/reference/arrays.scalars.html
        * http://docs.scipy.org/doc/numpy/user/basics.types.html
        * np.typecodes, np.sctypes

    """
    assert_image(gelimg)
    stdargs = dict(linearize=linearize, dynamicrange=dynamicrange, invert=invert, crop=crop, rotate=rotate, scale=scale)
    logger.debug("processimage() invoked with gelimg %s, args %s, stdargs %s and kwargs %s",
                 gelimg, printdict(args), printdict(stdargs), printdict(kwargs))
    if args is None:
        args = {}
    # mergedicts only overrides non-None entries:
    args.update(mergedicts(args,
                           stdargs,     # I ONLY have this after args because all of them default to None.
                           kwargs))     # Otherwise I would have used the 'defaultdict' approach.
    logger.debug("--combined args dict is: %s", printdict(args))

    # unpack variables (that are not changed - if values are updated, leave in `args`):
    info = gelimg.info
    width, height = gelimg.size
    # using "ante"/"post" rather than "pre"/"post" or "before"/"after", because "ante" is ordered before "post".
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
        scalefactor = gelimg.tag.getscalar(33446)  # or tifimg.tag.tags[33446][0]
    except (AttributeError, KeyError):
        # AttributeError if gelimg does not have .tag attribute (e.g. PNG file),
        # KeyError if .tag dict does not include 33449 key (e.g. TIFF file)
        scaninfo = ""
        scalefactor = None
    info.update({
        'width': width, 'height': height, 'pmt': get_pmt_string(scaninfo),
        'scalefactor': scalefactor, 'scaninfo': scaninfo})
    logger.debug("Gel scaninfo: %s", scaninfo)
    logger.debug("Image info dict: %s", info)

    #
    # Perform geometric image transformations (rotate, crop, flip/transpose, scale):
    gelimg = transform_image(gelimg=gelimg, args=args)
    info['size_after'] = gelimg.size
    info['height_after'], info['width_after'] = gelimg.size
    # width, height = gelimg.size  # Make sure to update width and height

    #
    # Prepare to LINEARIZE and apply dynamic range threshold (contrast):
    # ------------------------------------------------------------------

    # If we are not linearizing or adjusting dynamic range, we can take a shortcut that does not involve numpy:
    if (not (args['linearize'] and scalefactor)) and (not args['dynamicrange'] or args['dynamicrange'] == 'auto'):
        logger.debug("Not linearizing, avoiding numpy detour...")
        print("Not linearizing, avoiding numpy detour...")
        try:
            if args['invert']:
                gelimg = ImageOps.invert(gelimg)
            if args['dynamicrange'] == 'auto':
                # This may yield a rather different result than the dynamic range below:
                gelimg = ImageOps.autocontrast(gelimg)
        except IOError as e:
            logger.info("""Could not use PIL ImageOps to perform requested operations, "%s"
                        -- falling back to standard numpy.""", e)
        else:
            info['extrema_post'] = gelimg.getextrema()  # getextrema() will actually load the image.
            # TODO: Make sure the PIL image returned here has the proper image mode
            return gelimg, info

    # To linearize and apply dynamic range, we convert PIL image to 2D numpy.ndarray:
    # Important: Make sure to use unsigned integer values, dtype=numpy.uint32,
    # Otherwise it may use signed integers and wrap around to negative values.
    npimg = numpy.array(gelimg, dtype=numpy.uint32)
    if args.get("debug_show_all_image_transformations"):
        show_npimage(npimg, title="before_linearize")

    # IMAGE MODE: ('I' = 32-bit signed integer, 'F' = 32-bit float, 'L' = 8-bit, etc)
    input_image_mode = gelimg.mode  # Default is 'I' for GEL and TIFF, 'L' for grayscale PNG.
    info['input_mode'] = input_image_mode
    logger.debug("Original PIL image mode: '%s'", input_image_mode)
    output_bits, output_mode, output_dtype = get_bits_mode_dtype(args.get('png_mode', 'L'))

    #
    # LINEARIZE, using numpy to do pixel transforms:
    # ----------------------------------------------
    if args['linearize'] and scalefactor:
        npimg = linearize_pixel_values(npimg, scalefactor=scalefactor)

    #
    # ADJUST DYNAMIC RANGE:
    # ---------------------
    # Preview with matplotlib: Linearized image before adjusting dynamic range:
    # (Useful for debugging and other stuff)
    # if args.get('image_plot_before_dr_adjust', False):
    if args.get("debug_show_all_image_transformations"):
        show_npimage(npimg, title="after linearize (%s), before adjust_dr" % (args['linearize'] and scalefactor,))

    npimg = adjust_dynamic_range(npimg, args, info, output_mode)
    assert_image(npimg)

    #
    # CONVERT BACK TO PIL IMAGE:
    # --------------------------
    # Convert numpy image to proper data type:
    # npimg = npimg.astype('int32')
    # npimg = npimg.astype('uint32')
    # npimg = npimg.astype('uint8')  # If output_mode is 'L', this needs to be int8 or uint8.
    npimg = npimg.astype(output_dtype)  # If output_mode is 'L', this needs to be int8 or uint8.

    # Convert numpy image to PIL.Image.Image object:
    # Maybe this is what gives the problem? No, also seems good.
    # Is it the linearization?
    # pilimg = Image.fromarray(npimg, gelimg.mode)
    logger.debug("Reverting back to PIL image using image mode '%s'", input_image_mode)
    try:
        assert_image(npimg)
    except AssertionError:
        pass
    try:
        pilimg = Image.fromarray(npimg, output_mode)  # output_mode, not input_image_mode
    except ValueError as e:
        # For PNG, the only accepted image modes are I, I;16 and L.
        print("len(npimg):", len(npimg))
        print("npimg.size, npimg.shape:", npimg.size, npimg.shape)
        print("npimg.min(), npimg.max():", npimg.min(), npimg.max())
        logger.error("Unable to convert npimage to PIL image using image mode '%s': %s", input_image_mode, e)
        raise ValueError(e)

    # save information about image after processing:
    info['extrema_post'] = pilimg.getextrema()
    info['output_mode'] = output_mode

    return pilimg, info


def get_gel(filepath, args):
    """Open gelfile and process it.

    Image is a PIL.Image.Image object of the gel after processing as specified by args.
    Info is a dict with various info on the original image (before round-trip to numpy).
    If linearize is True (default), the .GEL data will be linearized before returning.
    Note that invert only takes effect if you specify a dynamic range.

    Returns:
         2-Tuple of (image, info), where image is a PIL.Image instance
         and info is a dict with information about the image.
    """
    gelimage = Image.open(filepath)
    if args.get("debug_show_all_image_transformations"):
        show_npimage(numpy.array(gelimage), title="right after Image.open(filepath)")
    gelimage, info = processimage(gelimage, args)
    return gelimage, info


# (too many branches, statements) pylint: disable=R0912,R0915
def convert(gelfile, args, yamlfile=None, lanefile=None, **kwargs):
    """Convert gel file to png given the info in args (using processimage to apply transformations).

    Args:
        gelfile: <str> file path pointing to a gel file.
        args: config dict, forwarded to get_gel/processimage together with gelfile
            to load gelfile data and apply image transformations.
        yamlfile: load args from this file and merge with args.
        lanefile: Load lane annotations from this file. Only used as argument to format png filename.

    Return:
        2-tuple of (image, info), where
        Image is a PIL.Image.Image object of the gel after processing as specified by args.
        Info is a dict with various info on the original image (before round-trip to numpy).

    <args> may be updated in-place by the process to contain transformed arguments, e.g.
      dynamicrange='auto' being converted to an actual (min, max) tuple value.

    If linearize is True (default for gel data), the .GEL data will be linearized before returning.
    """
    logger.debug("convert() invoked with gelfile %s, args %s and kwargs %s", gelfile, args, kwargs)
    if args is None:
        args = {}
    args.update(mergedicts(args, kwargs))
    logger.debug("--combined args dict is: %s", printdict(args))  # printdict to sort keys

    gelfile = gelfile or args['gelfile']
    basename, gelext = os.path.splitext(gelfile)
    gelext = gelext.lower()

    if gelext == '.gel':
        logger.debug("GEL filetype detected (extension '%s'), enabling linearize and invert if not specified.", gelext)
        if args.get('linearize') is None:
            args['linearize'] = True
        if args.get('invert') is None:
            args['invert'] = True

    # Parsing/conforming dynamicrange is done by transform()

    # Process and transform gel:
    # Good to have gel info even if args is locked for updates:
    logger.debug("getting image file...")
    gelimg, info = get_gel(gelfile, args)
    print("Loaded gelfile:", gelfile)
    print("Gel info: ", ", ".join("{}: {}".format(k, v) for k, v in info.items()))
    # Use orgimg for info, e.g. orgimg.info and orgimg.tag
    logger.debug("gelimg extrema: %s", gelimg.getextrema())
    dr = info.get('dynamicrange')
    logger.debug("dynamic range: %s", dr)
    # Dynamic range is used to format the PNG filename:
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
        n_existing = "_{}".format(len(glob.glob(basename+'*.'+ext)))
    else:
        n_existing = ""
    pngfnfmt_default = u'{gelfnroot}_{dr_rng}{n_existing}{ext}'
    if not has_pmt_string(basename) and info.get('pmt'):
        pngfnfmt_default = u'{gelfnroot}_{pmt}V_{dr_rng}{n_existing}{ext}'

    # Make pngfilename:
    pngfnfmt = args.get('pngfnfmt', pngfnfmt_default)
    yamlfnroot = os.path.splitext(os.path.basename(yamlfile))[0] if yamlfile else args.get('yamlfile', '')
    lanefnroot = os.path.splitext(os.path.basename(yamlfile))[0] if lanefile else args.get('lanefile', '')
    pngfilename = pngfnfmt.format(gelfnroot=basename, pmt=info['pmt'], dr_rng=rng,
                                  lanefnroot=lanefnroot, yamlfnroot=yamlfnroot,
                                  N_existing=n_existing, ext=ext)
    # Substitute bad characters/strings in filename:
    if args.get('filename_sub'):
        logger.info("Doing filename substitution using filename_sub = %s", args['filename_sub'])
        if len(args['filename_sub']) % 2 != 0:
            logger.warning("The number of elements in filename_sub list should be a multiple of 2"
                           "(find1, replace1, find2, replace2, ...), but is has %s elements",
                           len(args['filename_sub']))
        list_iter = iter(args['filename_sub'])
        find_replace_iter = zip(list_iter, list_iter)
        for find, replace in find_replace_iter:
            logger.info("filename_sub: replacing '%s' with '%s' in %s", find, replace, pngfilename)
            try:
                pngfilename = pngfilename.replace(find, replace)
                logger.debug("New pngfilename: %s", pngfilename)
            except (ValueError, TypeError) as e:
                logger.warning("Failed to do filename_sub using re.sub(%s, %s, %s): %s",
                               find, replace, pngfilename, e)
                print("\nERROR: Something went wrong doing filename_sub using find=%s, replace=%s\n" % (find, replace))
    else:
        logger.debug("args.get('filename_sub') = %s", args.get('filename_sub'))
    if args.get('filename_sub_re'):
        logger.info("Doing regex substitution using filename_sub_re = %s", args['filename_sub_re'])
        if len(args['filename_sub_re']) % 2 != 0:
            logger.warning("The number of elements in filename_sub_re list should be a multiple of 2"
                           "(find1, replace1, find2, replace2, ...), but is has %s elements",
                           len(args['filename_sub_re']))
        list_iter = iter(args['filename_sub_re'])
        find_replace_iter = zip(list_iter, list_iter)
        for find, replace in find_replace_iter:
            logger.info("filename_sub_re: replacing '%s' with '%s' in %s", find, replace, pngfilename)
            try:
                pngfilename = re.sub(find, replace, pngfilename)
                logger.debug("New pngfilename: %s", pngfilename)
            except (ValueError, TypeError) as e:
                logger.warning("Failed to do filename_sub_re using re.sub(%s, %s, %s): %s",
                               find, replace, pngfilename, e)
                print("\nERROR: Something went wrong doing filename_sub_re using find=%s, replace=%s\n"
                      % (find, replace))
    else:
        logger.debug("args.get('filename_sub_re') = %s", args.get('filename_sub_re'))

    # The 'pngfile' in args is relative to the gelfile, but it should be absolute when passed to save():
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


def show_npimage(npimg, hold=None, interactive=False, cmap="gray_r", block=False, title=None, backend='tkagg'):
    """Show image (in numpy array format) using matplotlib."""
    if backend:
        import matplotlib
        # Use matplotlib.get_backend() to check current backend; See matplotlib.backend for available backends.
        matplotlib.use(backend)     # Must be invoked before loading pyplot
    from matplotlib import pyplot
    # pyplot.ioff()    # Disable interactive mode.
    pyplot.interactive(interactive)
    if hold is not None:
        # hold: whether to retain old data:
        # "When hold is True, subsequent plot commands will be added to the current axes.
        # When hold is False, the current axes and figure will be cleared on the next plot command.
        pyplot.hold(hold)
        fig = pyplot.gcf()
        ax = pyplot.gca()
    else:
        # Create a new figure:
        fig = pyplot.figure()
        ax = fig.add_subplot(111)
    # axesimg = pyplot.imshow(npimg, cmap=cmap)
    # pyplot.colorbar(ax=ax)
    # Prefer matplotlib figure API rather than the pyplot statemachine magics:
    axesimg = ax.imshow(npimg, cmap=cmap)
    fig.colorbar(axesimg, ax=ax)
    if title:
        ax.set_title(title)
    # The problem with block=False is that it draws everything at once.
    pyplot.show(block=block)
    # imgplot.remove()


if __name__ == '__main__':

    # def activate_readline():
    #    #import rlcompleter
    #    import readline
    #    readline.parse_and_bind('tab: complete')
    # ar = activate_readline
    init_logging()

    argns = parseargs(prog='geltransformer')
    cmdgelfile = argns.gelfile
    cmdargs = argns.__dict__
    convert(cmdgelfile, cmdargs)
