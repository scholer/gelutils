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

"""

import os
import glob
import re

#from functools import partial
import numpy
from PIL import Image#, TiffImagePlugin
from PIL.Image import NEAREST, ANTIALIAS, BICUBIC, BILINEAR  # pylint: disable=W0611
from PIL import ImageOps
from PIL.TiffImagePlugin import OPEN_INFO, II
# from PIL.TiffImagePlugin import BITSPERSAMPLE, SAMPLEFORMAT, EXTRASAMPLES, PHOTOMETRIC_INTERPRETATION, FILLORDER, OPEN_INFO

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

from utils import init_logging, printdict, getrelfilepath
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


def processimage(gelimg, args=None, linearize=None, dynamicrange=None, invert=None,
                 crop=None, rotate=None, scale=None, **kwargs):          # pylint: disable=R0912
    """
    gelimg is a PIL Image file, not just a path.
    Linearizes all data points (pixels) in gelimg.
    gelimg should be a PIL.Image.Image object.
    crop is a 4-tuple box:
        (x1, y1, x2, y2)
        (1230, 100, 2230, 800)

    Returns processed image
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

    # unpack essentials (that are not changed):

    info = gelimg.info
    width, height = gelimg.size
    widthheight = [width, height]
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
    except (AttributeError, KeyError):
        # AttributeError if gelimg does not have .tag attribute (e.g. PNG file),
        # KeyError if .tag dict does not include 33449 key (e.g. TIFF file)
        scaninfo = ""
        scalefactor = None
    pmt = get_PMT(scaninfo)
    info.update(dict(width=width, height=height, pmt=pmt, scalefactor=scalefactor))
    logger.debug("Image info: %s", info)

    if args['rotate']:
        # NEAREST=1, BILINEAR=2, BICUBIC=3
        # Edit, no, at least not for original PIL: NONE = NEAREST = 0; ANTIALIAS = 1; LINEAR = BILINEAR = 2; CUBIC = BICUBIC = 3
        # OLD PIL rotate only supports NEAREST, BILINEAR, BICUBIC
        # gelimg = gelimg.rotate(angle=args['rotate'], resample=3, expand=args.get('rotateexpands'))
        # Edit: There is an issue in rotate, if I have pixels that are almost saturated,
        # then after rotation they are squashed to negative values.
        gelimg = gelimg.rotate(angle=args['rotate'], resample=0, expand=args.get('rotateexpands'))

    if args['crop']:
        # left, upper, right, lower
        crop = (float(x.strip('%'))/100 if isinstance(x, basestring) and '%' in x else x for x in args['crop'])
        # convert 0.05 to absolute pixels:
        crop = [int(widthheight[i % 2]*x) if x < 1 else x for i, x in enumerate(crop)]
        left, upper, right, lower = crop
        if args.get('cropfromedges'):
            logger.debug("Cropping image to: %s", (left, upper, width-right, height-lower))
            gelimg = gelimg.crop((left, upper, width-right, height-lower))
        else:
            logger.debug("Cropping image to: %s", (left, upper, right, lower))
            gelimg = gelimg.crop(crop)

    if args.get('scale'):
        scale = float(args['scale'].strip('%'))/100 if isinstance(args['scale'], basestring) and '%' in args['scale'] \
                else args['scale']
        # convert 0.05 to absolute pixels:
        newsize = [int(scale*width), int(scale*height)]
        logger.info("Resizing image by a factor of %s (%s) to %s", scale, args['scale'], newsize)
        #resample = 3 #
        gelimg = gelimg.resize(newsize, resample=ANTIALIAS)


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

    # https://pillow.readthedocs.org/handbook/concepts.html
    # 'I' = 32-bit signed integer, 'F' = 32-bit float, 'L' = 8-bit
    npimgmode = gelimg.mode # Default is 'I' for GEL and TIFF, 'L' for grayscale PNG.

    # Using numpy to do pixel transforms:
    if args['linearize'] and scalefactor:
        # We need to have 32-bit unsigned interger when we square the values;
        # otherwise values above 2**15*sqrt(2) gets squashed to negative values.
        npimg = numpy.array(gelimg, dtype=numpy.uint32) # Consider specifying dtype, e.g. uint32? # pylint: disable=E1101
        #npimg = numpy.array(gelimg, dtype=numpy.float32) # Which is better, float32 or uint32? # pylint: disable=E1101
        # TODO: Do performance test to see if float32 is better than uint32
        #       And remember to alter mode when you return to Image.fromarray
        logger.debug('Linearizing gel data using scalefactor %s...', scalefactor)
        logger.debug('npimg min, max before linearization: %s, %s', npimg.min(), npimg.max())
        # It seems that this gives some weird results??
        # Try to find a pixel that is at max in npimg, e.g. npimg[176, 250]
        # nplinimg[176, 250] is then -4 ??
        # npimg.dtype is dtype('int32') -- should be ok?
        # No, wait... when you do multiplication, that might be an issue... Yes:
        # >>> aarr = np.array([0, 1, 2**12, 2**14, 2**16-1])
        # >>> aarr**2
        # array([        0,         1,  16777216, 268435456,   -131071])  <--- NEGATIVE NUMBER!
        # maybe use npimg.astype()
        # Ah, of course -- by default we get a signed int32. This means the max is 2**31, not 2**32.
        # sqrt(2**31) = 46340 <-- this was the max value before hitting the floor. (2**15*sqrt(2))
        # For more: http://docs.scipy.org/doc/numpy/reference/arrays.dtypes.html
        #   http://docs.scipy.org/doc/numpy/reference/generated/numpy.dtype.html
        #   http://docs.scipy.org/doc/numpy/reference/arrays.scalars.html
        #npimg = npimg.astype('float32') # Is this overkill?
        #npimg = npimg.astype('uint32') # This is good for values up to 2**16-1 (2**16 yields 0)
        npimg = (npimg**2)/scalefactor[1]
        logger.debug('npimg min, max after linearization: %s, %s', npimg.min(), npimg.max())
        npimg = npimg.astype('int32') # Need to cast to lower or we cannot save back (it seems)
        logger.debug('npimg min, max after casting to int32: %s, %s', npimg.min(), npimg.max())
        #npimgmode = 'I;32' # or maybe just set the npimagemode?
        # 'I;32' doesn't work. 'I;16' does. Support seems flaky. https://github.com/python-pillow/Pillow/issues/863
        #npimg = npimg.astype('uint16') # ...but how low? (This is too low...)
        # Edit: Just using uint32 at numpy.array(gelimg), should do the trick.
        # Summary:
        # * It seems that as long as you do the calculations as float32 or uint32 it is fine,
        # * And you must cast back to int32 or it looks weird.
        # ** Edit: well, duh, you use gelimg.mode when you use Image.fromarray, so if npimg is
        #       in float format, you have to set the mode accordingly.
        # * For more on image modes, https://pillow.readthedocs.org/handbook/concepts.html
        # Note: Make sure whether you are using PIL or Pillow before you go exploring:
        # PIL.PILLOW_VERSION
    else:
        npimg = numpy.array(gelimg) # Do not use getdata(), just pass the image. # pylint: disable=E1101


    dr = args.get('dynamicrange')
    if dr == 'auto' or (args['invert'] and not dr):
        # If we want to invert, we need to have a range. If it is not specified, we need to find it.
        #dynamicrange = (0, 100000)
        logger.debug("Dynamic range is %s (args['invert']=%s)", dr, args['invert'])
        dr = args['dynamicrange'] = map(int, find_dynamicrange(npimg)) # Ensure you receive ints.
        logger.debug("--- determined dynamic range: %s", dr)

    if dr:
        if isinstance(args['dynamicrange'], (int, float, basestring)):
            # If we have only provided a single argument, assume it is dr_high and set low to 0.
            dr = args['dynamicrange'] = [0, args['dynamicrange']]
        if len(args['dynamicrange']) == 1:
            dr = args['dynamicrange'] = [0, args['dynamicrange'][0]]

        # Convert relative values: First, convert % to fraction:
        dr = (float(x.strip('%'))/100 if isinstance(x, basestring) and '%' in x else x for x in dr)
        # convert (0.05, 0.95) to absolute range:
        # Note: What if you have floating-point pixel values between 0 and 1? (E.g. for HDR images).
        # In that case, the dynamic range might not be distribution ranges but actual min/max pixel values.
        if all(x < 1 for x in dr):
            logger.debug("Finding dynamic range for %s (args['dynamicrange']=%s)", dr, args['dynamicrange'])
            dr = map(int, find_dynamicrange(npimg))
            logger.debug("--- determined dynamic range: %s", dr)


        # Transform image so all values < dynamicrange[0] is set to 0
        # all values > dynamicrange[1] is set to 2**16 and all values in between are scaled accordingly.
        # Closure:
        logger.debug("(a) dynamicrange: %s", args['dynamicrange'])
        logger.debug('npimg min, max before adjusting dynamic range: %s, %s', npimg.min(), npimg.max())
        ## TODO: FIX THIS FOR non 16-bit images:
        ## TODO: THERE IS A BUG WHERE OVERSATURATED AREAS ARE PAINTED WHITE.
        ## IT IS NOT THE INVERSION, HOWEVER, SO TAKE A LOOK AT HOW THE FILE IS READ,
        ## I.e. open file with PIL and look at the values or see if there is a mask or something.
        ## TODO: Consider converting the image to 32-bit floating point
        minval, maxval = 0, 2**16-1     # Note: This is not true for e.g. 8-bit png files.
        # (However PNG files may be in 'I' mode as well, probably 16-bit?)
        dr_low, dr_high = info['dynamicrange'] = args['dynamicrange']
        logger.debug("minval, maxval: %s, %s", minval, maxval)
        logger.debug("dr_low, dr_high: %s, %s", dr_low, dr_high)
        if args['invert']:
            logger.debug('Inverting image...')
            def adjust_fun(val):
                """ Function to adjust dynamic range of image, inverting the image in the process. """
                if val <= dr_low:
                    return maxval # This is correct when we are inverting the image.
                    #return minval
                elif val >= dr_high:
                    return minval # This is correct when we are inverting the image.
                    #return maxval
                # This might also be an issue: maxval*70000 > 2**32
                return (maxval*(dr_high-val))/(dr_high-dr_low)
        else:
            # Aparently, there is a case where when the higher boundary is reached, it behaves weird?
            # Higher values are whiter:
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
        logger.debug('npimg min, max after adjusting dynamic range: %s, %s', npimg.min(), npimg.max())

    # Maybe this is what gives the problem? No, also seems good.
    # Is it the linearization?
    #linimg = Image.fromarray(npimg, gelimg.mode)
    linimg = Image.fromarray(npimg, npimgmode)

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
    # Note: gelimg may be in 16-bit; saving would produce a 16-bit grayscale PNG.
    # Image size can possibly be reduced by 50% by saving as 8-bit grayscale.
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
