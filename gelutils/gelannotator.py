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
# pylint-xx: disable=W0142,W0621,C0103
# pylint: disable=W0142,C0103

"""

Module for annotating gels.

Annotates a gel image with lane descriptions from annotaitons file,
saves as svg (maybe add pdf ability?).


"""


import os
import sys
import glob
import yaml
import base64
from itertools import chain
from PIL import Image
import argparse
import webbrowser

try:
    import svgwrite     # pylint: disable=F0401
except ImportError:
    sys.path.append(os.path.normpath(r"C:\Users\scholer\Dev\src-repos\svgwrite"))
    import svgwrite     # pylint: disable=F0401

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

from clipboard import get_clipboard
from utils import gen_trimmed_lines, trimmed_lines_from_file, init_logging, getabsfilepath
from argutils import mergedicts, parseargs #, make_parser
from geltransformer import convert
from imageconverter import svg2png

#from utils import open_utf  # not required for


def find_yamlfilepath(gelfn, rel=False):
    """
    Finds a suitable yaml filename depending on gel filename.
    The returned file is absolute;
    use utils.getrelfilepath to get relative to gelfile.
    """
    if rel:
        gelfn = os.path.basename(gelfn)         # "filename", without directory
    basename, _ = os.path.splitext(gelfn)
    return basename+'.yml'

def find_annotationsfilepath(gelfn, rel=False):
    """
    Finds a suitable yaml filename depending on gel filename.
    Update: modified get_annotation_fn_by_gel_fn to not raise StopIteration.
    """
    return get_annotation_fn_by_gel_fn(gelfn, rel=rel)

def get_annotation_fn_by_gel_fn(gelfn, rel=False, fallback=True):
    """
    Return the first, best candidate for an annotation file for the given gel file.
    """
    gelfiledir = os.path.dirname(gelfn)
    gelfilebasename = os.path.basename(gelfn)       # gelfile, without directory
    #if gelfiledir:
    #    logger.debug('Changing dir to: %s', gelfiledir)
    #    os.chdir(gelfiledir)
    annotationsfn = os.path.splitext(gelfn)[0]
    # First search for files with a name similar to the gelfile, then search for standard annotation filenames:
    search_ext = ("*.annotations.txt", "*.txt", "*.lanes.yml")
    std_pats = ('samples.txt', 'annotations.txt')
    search_pats = (pat for pat in chain((annotationsfn+ext for ext in search_ext),
                                        std_pats))
    if not fallback:
        return next(fn for fn in chain(*(glob.glob(pat) for pat in search_pats)))
    if rel:
        fallback = os.path.basename(annotationsfn) + '.annotations.txt'
    else:
        fallback = annotationsfn + '.annotations.txt'
    return next((fn for fn in chain(*(glob.glob(pat) for pat in search_pats))), fallback)

#def asterix_line_trimming(annotation_lines, remove_asterix='first_only', require_asterix=False):
#    """
#    Removes asterix from lines. Useful if you have a
#    """
#    pass


def get_annotations(args=None, annotationsfile=None, gelfile=None):#, remove_asterix='first_only'):
    """
    Returns annotations given gel filename.
    """
    if args.get('fromclipboard', False):
        laneannotations = list(gen_trimmed_lines(get_clipboard().split('\n')))
        if laneannotations and len(laneannotations) < 30:
            # If laneannotations is more than 30, it is probably not intended to use.
            print "Found lines in clipboard:", laneannotations
            return laneannotations
    annotationsfile = annotationsfile or args['annotationsfile']
    gelfile = gelfile or args['gelfile']
    # annotationsfile is relative to gelfile:
    if annotationsfile and gelfile:
        annotationsfile = getabsfilepath(gelfile, annotationsfile)

    if not annotationsfile:
        logger.debug("annotationsfile is %s, searching for one by gelfilename...", annotationsfile)
        try:
            # get_annotation_fn_by_gel_fn returns an actual filepath, not relative to gelfile.
            annotationsfile = get_annotation_fn_by_gel_fn(gelfile, fallback=False)
        except StopIteration:
            logger.warning("Could not find annotationsfile!")
            raise ValueError("Could not find any suitable annotationsfile.")
        logger.debug("Using annotations file: %s", annotationsfile)

    ## We have a filepath with annotations:
    if os.path.splitext(annotationsfile)[1].lower() == '.yml':
        laneannotations = yaml.load(open(annotationsfile))
    else:
        laneannotations = trimmed_lines_from_file(annotationsfile, args)
    return laneannotations, annotationsfile



def makeSVG(gelfile, args=None, annotationsfile=None, laneannotations=None, **kwargs):
    """
    annotationsfile and laneannotations specifically not kwargs and defaultargs;
    we dont want to add this to args if it was not present there already.
    Supported keyword arguments:
    gelfile, laneannotations, xmargin, xspacing, yoffset, ypadding, textfmt, laneidxstart,
    yamlfile, embed, png, extraspaceright, textrotation, fontsize, fontfamily, fontweight

    ypadding: vertical space between annotations and gel.

    precedence scheme:
        kwargs over argns over defaultargs

    b = ", ".join(name.strip() for name in (elem.split('=')[0] for elem in a.split(',')))
    """
    if args is None:
        args = {}
    defaultargs = dict(xmargin=[40, 40], xspacing=None, yoffset=100, ypadding=5,
            textfmt="{name}", laneidxstart=0, embed=False,
            extraspaceright=0, textrotation=60,
            fontsize=None, fontfamily='sans-serif', fontweight='bold')
    if isinstance(args, argparse.Namespace):
        args = args.__dict__
    # Update in place?
    args.update(mergedicts(defaultargs, args, kwargs))

    logger.debug("gelfile: %s", gelfile)
    logger.debug("annotationsfile: %s", annotationsfile)
    logger.debug("laneannotations: %s", laneannotations)
    logger.debug("args: %s", args)
    logger.debug("kwargs: %s", kwargs)

    if gelfile is None:
        gelfile = args['gelfile']
    gelfp_wo_ext, gelext = os.path.splitext(gelfile)
    gelext = gelext.lower()

    # Load annotations:
    # locals().update(args) # I could have the args to the local namespace. However, it is better to keep the args in the args dict, so we can return an updated version of that. Also, changing locals() is not supported by pylint...
    laneannotations = laneannotations or args.get('laneannotations')
    annotationsfile = annotationsfile or args.get('annotationsfile')
    if not laneannotations:
        # If laneannotations are not already in args, we do not want to add them, so use laneannotations as local variable:
        laneannotations, annotationsfile = get_annotations(args, annotationsfile=annotationsfile, gelfile=gelfile)

    # Update gelfile if it is not a png file:
    if args.get('pngfile'):
        logger.debug("args['pngfile'] is specified; using this over gelfile. (%s)", args['pngfile'])
        pngfile_relative = args['pngfile']
        pngfile_actual = getabsfilepath(gelfile, pngfile_relative) # 'pngfile' is relative to gelfile.
        # make sure we update gelext after re-setting to pngfile:
        # However, we do not want to update gelbasename
        # gelfp_no_ext
        pngfp_wo_ext, pngext = os.path.splitext(pngfile_actual)
        pngext = pngext.lower()
    elif gelext in ('.png', '.jpg', '.jpeg'):
        logger.debug("args['pngfile'] not specified, but gelfile ext is suitable (%s), referring to gelfile (%s) as pngfile.",
                     gelext, gelfile)
        pngfp_wo_ext, pngext = gelfp_wo_ext, gelext
        pngfile_actual = gelfile
        pngfile_relative = os.path.basename(gelfile)
    else:
        print "args['pngfile'] is None? : ", args['pngfile']
        print "args['gelfile'] is: ", args['gelfile']
        print "gelfile is:", gelfile
        print "args is: {%s}" % ", ".join("{} : {}".format(repr(k), repr(v)) for k, v in sorted(args.items()))
        raise TypeError("Could not determine pngfile version of gel image.")

    pngimage = Image.open(pngfile_actual)
    # image size, c.f. http://stackoverflow.com/questions/15800704/python-get-image-size-without-loading-image-into-memory
    imgwidth, imgheight = pngimage.size
    pngimage.fp.close()
    # use gelfp_wo_ext or pngfp_wo_ext as basis?
    svgfilename = pngfp_wo_ext + '_annotated.svg'
    size = dict(width="{}px".format(imgwidth+args['extraspaceright']),
                height="{}px".format(imgheight+args['yoffset']))
    # Apparently, setting width, height here doesn't work:
    dwg = svgwrite.Drawing(svgfilename, profile='tiny') #, **size)      # size can apparently not be specified here
    dwg.attribs.update(size)
    g1 = dwg.add(dwg.g(id='Gel'))   # elements group with gel file

    # Add image:
    # xlink:href is first argument 'href'.
    # width="100%" height="100%" or  width="524" height="437" ?
    # additional image attribs: overflow, width, height, transform
    if args['embed']:
        filedata = open(gelfile, 'rb').read()
        # when you DECODE, the length of the base64 encoded data should be a multiple of 4.
        #print "len(filedata):", len(filedata)
        datab64 = base64.encodestring(filedata)
        # See http://www.askapache.com/online-tools/base64-image-converter/ for info:
        mimebyext = {'.jpg' : 'image/jpeg',
                     '.jpeg': 'image/jpeg',
                     '.png' : 'image/png'}
        mimetype = mimebyext[pngext]
        imghref = ",".join(("data:"+mimetype+";base64", datab64))
    else:
        imghref = pngfile_relative
    img = g1.add(dwg.image(imghref, width=imgwidth, height=imgheight))  # Using size in percentage doesn't work.
    img.translate(tx=0, ty=args['yoffset'])

    # Add annotations:
    g2 = dwg.add(dwg.g(id='Annotations'))

    Nlanes = len(laneannotations)
    if not args['xspacing']:
        xspacing = (imgwidth-sum(args['xmargin']))/(Nlanes-1)    # Number of spaces is 1 less than number of lanes.

    #print "xmargin=", xmargin, ", xspacing=", xspacing, "sum(xmargin)+xspacing:", sum(xmargin)+xspacing
    #print "imgwidth:", imgwidth, ", imgwidth-sum(xmargin):", imgwidth-sum(xmargin), ", N:", N
    #print "sum(xmargin)+(N-1)*xspacing:", sum(xmargin)+(N-1)*xspacing

    for idx, annotation in enumerate(laneannotations):
        text = g2.add(dwg.text(args['textfmt'].format(idx=idx+args['laneidxstart'], name=annotation)))
        for att in ('font-size', 'font-family', 'font-weight'):
            argkey = att.replace('-', '')
            if args[argkey]:
                text.attribs[att] = args[argkey]
        text.translate(tx=args['xmargin'][0]+xspacing*idx, ty=args['yoffset']-args['ypadding'])
        text.rotate(-args['textrotation']) # rotate(self, angle, center=None)

    dwg.save()
    print "Annotated gel saved to file:", svgfilename

    return dwg, svgfilename

    # rotate(<degree> <point>)
    # e.g. "rotate(30 10,22)" to rotate 30 degree clockwise around the point (10,22).
    # translate(x, y)  # x pixels to the right, y pixels down.
    # translate(10 100)
    # Note that the order of transformations matter.
    #


def ensurePNG(gelfile, args):
    """
    Ensures that we have a png file to work with.
    If args['gelfile'] already is a png, then just skip.

    If gelfile is a .GEL file:
    Make PNG from GEL file and update args to reflect that change.
    """
    if gelfile is None:
        gelfile = args['gelfile']
    _, gelext = os.path.splitext(gelfile)
    gelext = gelext.lower()
    if gelext.lower() in ('.png', '.jpg', '.jpeg'):
        # Hmm... it might be nicer to allow rotation of an existing png image, not only .gel files?
        if any(args.get(k) for k in ('invert', 'crop', 'rotate')):
            convert(gelfile, args)
        return
    if args.get('pngfile') and args.get('reusepng', True):
        # We have a png file and want to re-use it and not re-generate it:
        return

    if gelext.lower() == '.gel':
        # convert gel to png:
        args.setdefault('convertgelto', 'png')
        logger.info("ensurePNG: Converting %s to png...", gelfile)
        convert(gelfile, args)   # convert will update args['pngfile']
    elif gelext.lower() in ('.tif', '.tiff'):
        # convert tif to png:
        if args('linearize') is None: # set sane default
            args['linearize'] = False
        args.setdefault('convertgelto', 'png')
        convert(gelfile, args)
    else:
        raise ValueError("gelfile extension not recognized. Recognized extensions are: .gel, .png, .jpg.")





def annotate_gel(gelfile, args=None, yamlfile=None, annotationsfile=None):
    """
    Idea: Pass in an args dict, and this will take care of everything.
    Returns updated args dict with anything that may have been changed as a result of the run.
    """
    if args is None:
        args = {}
    if isinstance(args, argparse.Namespace):
        args = args.__dict__
    if yamlfile is None:
        yamlfile = args.get('yamlfile') # Do not update.
    if annotationsfile is None:
        annotationsfile = args.get('annotationsfile')
    if yamlfile:
        try:
            logger.debug("Loading additional settings (those not already specified) from file: %s", yamlfile)
            yamlsettings = yaml.load(open(yamlfile))
            #for key, value in settings.items():
            #    setattr(argns, key, value)
            # Make sure to update in-place:
            args.update(mergedicts(yamlsettings, args))
        except IOError as e:
            logger.debug(e)
            logger.debug("No existing yaml file: %s -- That's OK.", yamlfile)
        except KeyError as e:
            logger.debug("KeyError: %s", e)
    # update no
    #args = mergeargs(argsns=args, argsdict=yamlsettings, excludeNone=True, precedence='argns')

    ensurePNG(gelfile, args)

    dwg, svgfilename = makeSVG(gelfile, args, annotationsfile=annotationsfile)

    if args.get('svgtopng'):
        # svg's base64 encoding is not as optimal as a native file but about 40-50% larger.
        # Thus, it might be nice to be able to export
        #print "PNG export not implemented. Requires Cairo."
        #svg2pngfn = args['svgtopngfile'] = svg2png(svgfilename)
        svg2pngfn = svg2png(svgfilename)    # not saving svgtopngfile in args...
    else:
        svg2pngfn = None

    if args.get('openwebbrowser'):
        webbrowser.open(os.path.abspath(svgfilename))
        if svg2pngfn:
            webbrowser.open(os.path.abspath(svg2pngfn))
            # webbrowser.open will open with either default browser OR default application.
            # If you want to open with default application, use os.startfile on windows
            # subprocess.call(['open', filename]) on OSX, and
            # subprocess.call(['xdg-open', filename])  on POSIX (or possibly just use open)
            # c.f. http://stackoverflow.com/questions/434597/open-document-with-default-application-in-python

    if yamlfile and args.get('updateyaml', True):
        # Not sure if this should be done here or in gelannotator:
        logger.debug("Saving/updating yaml file: ")
        with open(yamlfile, 'wb') as fd:
            yaml.dump(args, fd, default_flow_style=False)

    return dwg, svgfilename, args





if __name__ == '__main__':

    init_logging()

    argns = parseargs()
    cmd_gelfile = argns.gelfile
    #args = {}
    #if argns.yamlfile:
    #    try:
    #        settings = yaml.load(open(argns.yamlfile))
    #        print "Loading settings from file:", argns.yamlfile
    #        args.update(settings)
    #        #for key, value in settings.items():
    #        #    setattr(argns, key, value)
    #    except IOError as e:
    #        print e
    #        print "No existing yaml file", argns.yamlfile, " -- That's OK."
    #args.update(argns.__dict)   # To get all arguments in the args dict
    #args.update((k, v) for k, v in argns.__dict__.items() if v is not None)    # To remove None-value arguments.
    #print argns.__dict__
    #print args

    ## If you want to go directly from a .GEL file, here is the spot:
    # pass

    #drawing = makeSVG(**args)
    drawing, svgfn, updatedargs = annotate_gel(cmd_gelfile, argns)
    if drawing:
        print "Annotated svg saved as:", drawing.filename
    #if argns.yamlfile:
    #    with open(argns.yamlfile, 'wb') as fd:
    #        yaml.dump(args, fd, default_flow_style=False)
    #        print "Settings written to file:", argns.yamlfile
