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
    import svgwrite
except ImportError:
    sys.path.append(os.path.normpath(r"C:\Users\scholer\Dev\src-repos\svgwrite"))
    import svgwrite

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

from clipboard import get_clipboard
from utils import gen_trimmed_lines, trimmed_lines_from_file, getfilepath, init_logging
from argutils import mergedicts, parseargs #, make_parser
from geltransformer import convert

def find_yamlfilepath(gelfn, rel=True):
    """
    Finds a suitable yaml filename depending on gel filename.
    """
    if rel:
        gelfn = os.path.basename(gelfn)
    basename, _ = os.path.splitext(gelfn)
    return basename+'.yml'

def find_annotationsfilepath(gelfn, rel=True):
    """
    Finds a suitable yaml filename depending on gel filename.
    """
    try:
        return get_annotation_fn_by_gel_fn(gelfn)
    except StopIteration:
        # If no existing was found, use a new one:
        basename, _ = os.path.splitext(gelfn)
        basename = basename+'.txt'
        if rel:
            gelfn = os.path.basename(gelfn)
        else:
            return basename

def get_annotation_fn_by_gel_fn(gelfn, rel=True):
    """
    Return the first, best candidate for an annotation file for the given gel file.
    """
    gelfiledir = os.path.dirname(gelfn)
    if gelfiledir:
        logger.debug('Changing dir to: %s', gelfiledir)
        os.chdir(gelfiledir)
    annotationsfn = os.path.splitext(gelfn)[0]
    search_ext = ("*.annotations.txt", "*.txt", "*.lanes.yml")
    std_pats = ('samples.txt', 'annotations.txt')
    search_pats = (pat for pat in chain((annotationsfn+ext for ext in search_ext),
                                        std_pats))
    return next(fn for fn in chain(*(glob.glob(pat) for pat in search_pats)))

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
    if not annotationsfile:
        annotationsfile = get_annotation_fn_by_gel_fn(gelfile)

    # In case annotationsfile is relative to gelfile:
    annotation_filepath = getfilepath(gelfile, annotationsfile)
    ## We have a filepath with annotations:
    if os.path.splitext(annotation_filepath)[1].lower() == '.yml':
        laneannotations = yaml.load(open(annotation_filepath))
    else:
        laneannotations = trimmed_lines_from_file(annotation_filepath, args)
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
    defaultargs = dict(xmargin=[40, 30], xspacing=None, yoffset=100, ypadding=5,
            textfmt="{name}", laneidxstart=0, yamlfile=None, embed=False, png=False,
            extraspaceright=0, textrotation=60,
            fontsize=None, fontfamily=None, fontweight=None)
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
    gelbasename, gelext = os.path.splitext(gelfile)
    if gelext.lower() != '.png':
        #gelfile = next(args[k] for k in ('pngfile', 'jpgfile', 'gelfile')) # Supported filetypes
        if args['pngfile']:
            gelfile = args['pngfile'] # only supported right now; make_annotation should take care to ensure this is present.
        else:
            print "args['pngfile'] is None: ", args['pngfile']
            print "args['gelfile'] is: ", args['gelfile']
            print "args is: {%s}" % ", ".join("{} : {}".format(repr(k), repr(v)) for k, v in sorted(args.items()))
            raise TypeError("pngfile not recognized.")

    # locals().update(args) # I could have the args to the local namespace. However, it is better to keep the args in the args dict, so we can return an updated version of that. Also, changing locals() is not supported by pylint...
    laneannotations = laneannotations or args.get('laneannotations')
    annotationsfile = annotationsfile or args.get('annotationsfile')
    if not laneannotations:
        # If laneannotations are not already in args, we do not want to add them, so use laneannotations as local variable:
        laneannotations, annotationsfile = get_annotations(args, annotationsfile=annotationsfile, gelfile=gelfile)
    gelimage = Image.open(gelfile)
    # image size, c.f. http://stackoverflow.com/questions/15800704/python-get-image-size-without-loading-image-into-memory
    imgwidth, imgheight = gelimage.size
    gelimage.fp.close()
    svgfilename = gelbasename + '_annotated.svg'
    size = dict(width="{}px".format(imgwidth+args['extraspaceright']),
                height="{}px".format(imgheight+args['yoffset']))
    # Apparently, setting width, height here doesn't work:
    dwg = svgwrite.Drawing(svgfilename, profile='tiny') #, **size)
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
        imghref = ",".join(("data:image/png;base64", datab64))
    else:
        imghref = gelfile
    img = g1.add(dwg.image(imghref, width=imgwidth, height=imgheight))  # Using size in percentage doesn't work.
    img.translate(tx=0, ty=args['yoffset'])

    # Add annotations:
    g2 = dwg.add(dwg.g(id='Annotations'))

    Nlanes = len(laneannotations)
    if args['xspacing'] is None:
        xspacing = (imgwidth-sum(args['xmargin']))/(Nlanes-1)    # Number of spaces is 1 less than number of lanes.
    #print "xmargin=", xmargin, ", xspacing=", xspacing, "sum(xmargin)+xspacing:", sum(xmargin)+xspacing
    #print "imgwidth:", imgwidth, ", imgwidth-sum(xmargin):", imgwidth-sum(xmargin), ", N:", N
    #print "sum(xmargin)+(N-1)*xspacing:", sum(xmargin)+(N-1)*xspacing

    # Currently: use fixed xstart and xspacing to determine position.
    # In the future: probe the gel file for size.
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
    if args.get('svgtopng'):
        print "PNG export not implemented. Requires Cairo."
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
    gelbasename, gelext = os.path.splitext(gelfile)
    if gelfile is None:
        gelfile = args['gelfile']
    if gelext.lower() == '.png':
        args['pngfile'] = gelfile
    if args.get('pngfile', None) and args.get('reusepng', True):
        return
    _, gelext = os.path.splitext(gelfile)
    if gelext.lower() == '.gel':
        # convert gel to png:
        args.setdefault('convertgelto', 'png')
        print "ensurePNG: Converting %s to png..." % gelfile
        convert(gelfile, args)   # convert will update args['pngfile']
    elif gelext.lower() in ('.tif', '.tiff'):
        # convert tif to png:
        args['linearize'] = False
        args.setdefault('convertgelto', 'png')
        convert(gelfile, args)
    elif gelext.lower() in ('.jpg', 'jpeg'):
        args['jpgfile'] = gelfile
        raise NotImplementedError(".jpg not implemented.")
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
    if args.get('openwebbrowser'):
        webbrowser.open("file://"+os.path.abspath(svgfilename))

    if args.get('updateyaml', True):
        # Not sure if this should be done here or in gelannotator:
        logger.debug("Saving/updating yaml file: ")
        with open(yamlfile, 'wb') as fd:
            yaml.dump(args, fd, default_flow_style=False)


    return dwg, svgfilename





if __name__ == '__main__':

    init_logging()

    argns = parseargs()
    gelfile = argns.gelfile
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
    drawing, svgfilename = annotate_gel(gelfile, argns)
    if drawing:
        print "Annotated svg saved as:", drawing.filename
    #if argns.yamlfile:
    #    with open(argns.yamlfile, 'wb') as fd:
    #        yaml.dump(args, fd, default_flow_style=False)
    #        print "Settings written to file:", argns.yamlfile
