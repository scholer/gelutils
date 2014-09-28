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

Module for annotating gels.

Annotates a gel image with lane descriptions from annotaitons file,
saves as svg (maybe add pdf ability?).


"""


import os
import sys
import glob
import yaml
import base64
import argparse
from itertools import chain
from PIL import Image


try:
    import svgwrite
except ImportError:
    sys.path.append(os.path.normpath(r"C:\Users\scholer\Dev\src-repos\svgwrite"))
    import svgwrite


from rsenv.utils.clipboard import get_clipboard
from rsenv.dataparsing.textdata_util import gen_trimmed_lines
from rsenv.dataparsing.file_parsers import trimmed_lines_from_file



def get_annotation_fn_by_gel_fn(gelfn):
    """
    Return the first, best candidate for an annotation file for the given gel file.
    """
    annotationsfn = os.path.splitext(gelfn)[0]
    search_ext = ("*.annotations.txt", "*.txt", "*.yml")
    std_pats = ('samples.txt', 'annotations.txt')
    search_pats = (pat for pat in chain((annotationsfn+ext for ext in search_ext),
                                        std_pats))
    return next(fn for fn in chain(*(glob.glob(pat) for pat in search_pats)))

#def asterix_line_trimming(annotation_lines, remove_asterix='first_only', require_asterix=False):
#    """
#    Removes asterix from lines. Useful if you have a
#    """
#    pass


def get_annotations(gelfn):#, remove_asterix='first_only'):
    """
    Returns annotations given gel filename.
    """
    #annotation_lines = False
    try:
        annotation_filepath = get_annotation_fn_by_gel_fn(gelfn)
        if os.path.splitext(annotation_filepath)[1] == 'yml':
            annotation_lines = yaml.load(open(annotation_filepath))
        else:
            annotation_lines = trimmed_lines_from_file(annotation_filepath)
    except StopIteration:
        print "No annotations-file found for file", gelfn
        print "Trying to read from clipboard..."
        annotation_lines = list(gen_trimmed_lines(get_clipboard().split('\n')))
        print annotation_lines
        if not annotation_lines or len(annotation_lines) > 30:
            raise ValueError("Could not find annotations file; clipboard is either empty or very large.")
        print "Found lines in clipboard:", annotation_lines
    return annotation_lines



def makeSVG(gelfile, laneannotations=None, xmargin=None, xspacing=None, yoffset=100, ypadding=5,
            textfmt="{name}", laneidxstart=0, yamlfile=None, embed=False, png=False,
            extraspaceright=0, rotation=60,
            fontsize=None, fontfamily=None, fontweight=None):
    """

    ypadding: vertical space between annotations and gel.
    """
    gelbasename, gelext = os.path.splitext(gelfile)
    if laneannotations is None:
        laneannotations = get_annotations(gelfile)
    if xmargin is None:
        xmargin = (40, 30)
    if yoffset is None:
        yoffset = 100
    if laneidxstart is None:
        laneidxstart = 0
    if textfmt is None:
        textfmt = "{name}"
    if extraspaceright is None:
        extraspaceright = 0
    if rotation is None:
        rotation = 60
    gelimage = Image.open(gelfile)
    imgwidth, imgheight = gelimage.size
    gelimage.fp.close()
    svgfilename = gelbasename + '_annotated.svg'
    size = dict(width="{}px".format(imgwidth+extraspaceright), height="{}px".format(imgheight+yoffset))
    #print "size:", size
    # Apparently, setting width, height here doesn't work:
    dwg = svgwrite.Drawing(svgfilename, profile='tiny') #, **size)
    g1 = dwg.add(dwg.g(id='Gel'))
    #imageatt = {'xlink:href': "RS323_Agarose_ScaffoldPrep_550V_0-5k.PNG"}
    #imageatt = {'xlink:href': gelfile}
    # additional image attribs: overflow, width, height, transform
    # xlink:href is first argument 'href'.
    # width="100%" height="100%" or  width="524" height="437"
    # to get image size:
    # http://stackoverflow.com/questions/15800704/python-get-image-size-without-loading-image-into-memory
    if embed:
        filedata = open(gelfile, 'rb').read()
        # when you DECODE, the length of the base64 encoded data should be a multiple of 4.
        #print "len(filedata):", len(filedata)
        datab64 = base64.encodestring(filedata)
        imghref = ",".join(("data:image/png;base64", datab64))
    else:
        imghref = gelfile
    img = g1.add(dwg.image(imghref, width=imgwidth, height=imgheight))
    #img = g1.add(dwg.image(gelfile, width="100%", height="100%"))
    img.translate(tx=0, ty=yoffset)
    #
    g2 = dwg.add(dwg.g(id='Annotations'))

    Nlanes = len(laneannotations)
    if xspacing is None:
        xspacing = (imgwidth-sum(xmargin))/(Nlanes-1)    # Number of spaces is 1 less than number of lanes.
    #print "xmargin=", xmargin, ", xspacing=", xspacing, "sum(xmargin)+xspacing:", sum(xmargin)+xspacing
    #print "imgwidth:", imgwidth, ", imgwidth-sum(xmargin):", imgwidth-sum(xmargin), ", N:", N
    #print "sum(xmargin)+(N-1)*xspacing:", sum(xmargin)+(N-1)*xspacing

    # Currently: use fixed xstart and xspacing to determine position.
    # In the future: probe the gel file for size.
    for idx, annotation in enumerate(laneannotations):
        text = g2.add(dwg.text(textfmt.format(idx=idx+laneidxstart, name=annotation)))
        if fontsize:
            text.attribs['font-size'] = fontsize
        if fontfamily:
            text.attribs['font-family'] = fontfamily
        if fontweight:
            text.attribs['font-weight'] = fontweight
        text.translate(tx=xmargin[0]+xspacing*idx, ty=yoffset-ypadding)
        text.rotate(-rotation) # rotate(self, angle, center=None)

    dwg.attribs.update(size)
    dwg.save()
    if png:
        print "PNG export not implemented. Requires Cairo."
    return dwg

    # rotate(<degree> <point>)
    # e.g. "rotate(30 10,22)" to rotate 30 degree clockwise around the point (10,22).
    # translate(x, y)  # x pixels to the right, y pixels down.
    # translate(10 100)
    # Note that the order of transformations matter.
    #







if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gelfile')
    ap.add_argument('--yoffset', type=int, help="Y offset (how far down the gel image should be).") #, default=100
    ap.add_argument('--ypadding', type=int, help="Vertical space between gel image and annotations.") #, default=100
    ap.add_argument('--xmargin', nargs=2, type=int, help="Margin (right and left).") # , default=(30, 40)
    ap.add_argument('--xspacing', type=int, help="Force a certain x spacing.")
    ap.add_argument('--extraspaceright', type=int, help="Add additional padding/whitespace to the right (if the gel is not wide enought for the last annotation).")

    ap.add_argument('--rotation', type=int, help="Angle to rotate text (counter-clockwise).")

    ap.add_argument('--fontsize', type=int, help="Specify default font size.")
    ap.add_argument('--fontfamily', help="Specify default font family, e.g. arial or MyriadPro.")
    ap.add_argument('--fontweight', help="Font weight: normal | bold | bolder | lighter | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | inherit.")

    ap.add_argument('--textfmt', help="How to format the lane annotations, e.g. '{idx} {name}'.")

    ap.add_argument('--yamlfile', help="Load options from YAML file, update and save.")
    ap.add_argument('--embed', action='store_true', help="Embed image data in svg file. (default is to link)")
    ap.add_argument('--no-embed', dest='embed', action='store_false', help="Do not embed image data in svg file, link to the file instead.")
    ap.add_argument('--png', action='store_true', help="Save svg as png (requires cairo package).")

    #xmargin=(40, 30), xspacing=None, yoffset=100
    #textfmt="{idx} {name}", laneidxstart=0

    argns = ap.parse_args()
    args = {}
    if argns.yamlfile:
        try:
            settings = yaml.load(open(argns.yamlfile))
            print "Loading settings from file:", argns.yamlfile
            args.update(settings)
            #for key, value in settings.items():
            #    setattr(argns, key, value)
        except IOError as e:
            print e
            print "No existing yaml file", argns.yamlfile, " -- That's OK."
    #args.update(argns.__dict)   # To get all arguments in the args dict
    args.update((k, v) for k, v in argns.__dict__.items() if v is not None)    # To remove None-value arguments.
    #print argns.__dict__
    #print args
    drawing = makeSVG(**args)
    print "Annotated svg saved as:", drawing.filename
    if argns.yamlfile:
        with open(argns.yamlfile, 'wb') as fd:
            yaml.dump(args, fd)
            print "Settings written to file:", argns.yamlfile
