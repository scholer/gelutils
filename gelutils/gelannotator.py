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

# pylint-xx: disable=W0142,W0621,C0103
# pylint: disable=W0142,C0103

"""

Module for annotating gels.

Annotates a gel image with lane descriptions from annotaitons file,
saves as svg (maybe add pdf ability?).

TODO: Consider adding support for using PIL.PSDraw or PIL.ImageDraw
as a fallback to using svgwrite + convert?
See:
    https://pillow.readthedocs.org/reference/ImageDraw.html
    https://pillow.readthedocs.org/reference/PSDraw.html
    https://pillow.readthedocs.org/handbook/tutorial.html#postscript-printing


"""

from __future__ import print_function, absolute_import
import os
import glob
import yaml
from yaml.representer import RepresenterError
import base64
from itertools import chain
from PIL import Image
import argparse
import webbrowser
import svgwrite
import logging

# Local imports:
from .clipboard import get_clipboard
from .utils import (gen_trimmed_lines, trimmed_lines_from_file, init_logging,
                    getabsfilepath, printdict, ensure_numeric, mergedicts)
from .argutils import parseargs  # , make_parser
from .geltransformer import convert
from .imageconverter import svg2png
from .config import config_ext
from . import __version__

# Constants:
# flush keyword only supported for python 3.3+, so create custom print function:
# Edit: Instead of modifying print to accept flush keyword, just make sure to use line-buffering for file objects

logging.addLevelName(4, 'SPAM')  # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)


def find_yamlfilepath(gelfn, rel=False, basedir=None):
    """Finds a suitable yaml filename depending on gel filename.

    Given a gel filename, returns a yaml filename.
    The returned file is absolute;
    use utils.getrelfilepath to get relative to gelfile.
    """
    if rel:
        gelfn = os.path.basename(gelfn)         # "filename", without directory
    basename, _ = os.path.splitext(gelfn)
    return basename + config_ext


def find_annotationsfilepath(filenames, rel=False, fallback=True):
    """Finds a suitable annotationsfile depending on gel filename.

    Return the first, best candidate for an annotation file for the given gel file.

    The filepath is actual, not relative.

    Update: modified get_annotation_fn_by_gel_fn to not raise StopIteration.
    """
    # gelfilebasename = os.path.basename(gelfn)       # gelfile, without directory
    # if gelfiledir:
    #    logger.debug('Changing dir to: %s', gelfiledir)
    #    os.chdir(gelfiledir)
    logger.debug("basenames (before removing Nones and stripping file extensions): %s", filenames)
    filenames = [os.path.splitext(fn)[0] for fn in filenames if fn is not None]
    if not filenames:
        raise ValueError("gelfn and yamlfn are both None; cannot derive annotationsfn")
    fnroot = filenames[0]
    # basedir = os.path.dirname(fnroot)
    if fallback is True:
        fallback = fnroot + '.annotations.txt'
        if rel:
            fallback = os.path.basename(fallback)
    # First search for files with a name similar to the gelfile, then search for standard annotation filenames:
    # use glob() or direct isfile()?
    # - glob uses unix style wildcards - these includes bracket groups [1-9], so patterns with [SYBR Gold] won't work!
    # search_ext = ("*.annotations.txt", "*.txt", "*.lanes.yml")
    search_ext = [".annotations.txt", ".txt", ".lanes.yml"]
    std_pats = ['samples.txt', 'annotations.txt']
    glob_pats = [base+"*"+ext for base in filenames for ext in search_ext]
    fn_cands = [base+ext for base in filenames for ext in search_ext] + std_pats  # direct fn matches
    logger.debug("basenames: %s", filenames)
    logger.debug("search_ext: %s", search_ext)
    logger.debug("fn_pats: %s", fn_cands)
    logger.debug("glob_pats: %s", glob_pats)
    for fn_cand in fn_cands:
        if os.path.isfile(fn_cand):
            ann_fn = fn_cand
            break
    else:
        try:
            ann_fn = next(fn for fn in chain(*(glob.glob(pat) for pat in glob_pats)))
        except StopIteration:
            logger.debug("None of the file patterns in search_pats matched any file, using fallback: %s", fallback)
            if fallback:
                ann_fn = fallback
            else:
                raise ValueError("Could not find any suitable annotationsfile.")

    logger.debug("Selected annotationsfile: %s", ann_fn)
    return ann_fn


# def asterix_line_trimming(annotation_lines, remove_asterix='first_only', require_asterix=False):
#     """
#     Removes asterix from lines. Useful if you have a
#     """
#     pass


def get_annotations(args=None, annotationsfile=None, gelfile=None):
    """Find gel/lane annotations.

    Load and return annotations from a gel/lane annotations file.
    This function is meant to make it easy to just pass all app config args and this function will
    figure out how to do the sane thing.
    If annotations file is not specified explicitly,
    do a brief search for a suitable annotations file (using the gelfile filename).

    Annotations can optionally be read from clipboard, if args['fromclipboard'] is True.

    Args:
        args: a dict with configuration/command-line arguments.
        annotationsfile: explicitly specify the annotations file to use.
        gelfile: Use this filename as the base for finding the correct annotations file.

    If both gelfile and annotationsfile are given, annotationsfile is assumed to be relative to gelfile.

    Returns:
        A tuple of (laneannotations, annotationsfile),
        where the first element is a list of lane annotations,
        and the second element is the filepath of the annotations file that was read.

    """
    if args.get('fromclipboard', False):
        laneannotations = list(gen_trimmed_lines(get_clipboard().split('\n')))
        if laneannotations and len(laneannotations) < 30:
            # If laneannotations is more than 30, it is probably not intended to use.
            print("Found lines in clipboard:", laneannotations)
            return laneannotations, None
    annotationsfile = annotationsfile or args['annotationsfile']
    gelfile = gelfile or args['gelfile']
    # annotationsfile is relative to gelfile:
    if annotationsfile and gelfile:
        annotationsfile = getabsfilepath(gelfile, annotationsfile)

    if not annotationsfile:
        logger.debug("annotationsfile is %s, searching for one by gelfilename...", annotationsfile)
        annotationsfile = find_annotationsfilepath([gelfile], fallback=False)

    # We have a filepath with annotations:
    if os.path.splitext(annotationsfile)[1].lower() == '.yml':
        laneannotations = yaml.load(open(annotationsfile))
    else:
        laneannotations = trimmed_lines_from_file(annotationsfile, args)
    return laneannotations, annotationsfile


def make_svg(gelfile, args=None, annotationsfile=None, laneannotations=None, yamlfile=None, **kwargs):
    """Creates SVG file with lane annotations overlayed over the gel.

    Arguments:
        gelfile : gelfile that is the basis. Not pngfile; that is given in args.
        args    : dict with arguments used to control the annotations.
        annotationsfile : file with lane annotations (only used if laneannotations is None).
        laneannotations : list of lane annotations.
        yamlfile: May be used if svgfilename format makes use of it.

    annotationsfile and laneannotations specifically not kwargs and defaultargs;

    We dont want to add this to args if it was not present there already.
    Supported keyword arguments:
    gelfile, laneannotations, xmargin, xspacing, yoffset, ypadding, textfmt, laneidxstart,
    yamlfile, embed, png, xtraspaceright, textrotation, fontsize, fontfamily, fontweight

    ypadding: vertical space between annotations and gel.

    precedence scheme:
        kwargs over argns over defaultargs

    b = ", ".join(name.strip() for name in (elem.split('=')[0] for elem in a.split(',')))
    """
    if args is None:
        args = {}
    defaultargs = dict(xmargin=[50, 50], xspacing=None, yoffset=150, ypadding=5,
                       textfmt="{name}", laneidxstart=0, embed=None,
                       xtraspaceright=0, textrotation=60,
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
    # Convention:
    # A file path is denoted as: <filepath> = <folderpath>/<basename> = <dirname>/<fnroot><ext>
    # dirname, dirpath and folderpath are all the same. Foldername, however, is only the last part, not the full path.
    gelfp_wo_ext, gelext = os.path.splitext(gelfile)
    gelfnroot = os.path.basename(gelfp_wo_ext)
    gelext = gelext.lower()
    yamlfnroot = os.path.splitext(os.path.basename(yamlfile))[0] if yamlfile else args.get('yamlfile', '')
    lanefnroot = os.path.splitext(os.path.basename(annotationsfile))[0] if annotationsfile else args.get('lanefile', '')

    # 1. Load annotations:
    laneannotations = laneannotations or args.get('laneannotations')
    annotationsfile = annotationsfile or args.get('annotationsfile')
    if not laneannotations:
        laneannotations, annotationsfile = get_annotations(args, annotationsfile=annotationsfile, gelfile=gelfile)

    # 2. Update gelfile if it is not a png file:
    if args.get('pngfile'):
        logger.debug("args['pngfile'] is specified; using this over gelfile. (%s)", args['pngfile'])
        pngfile_relative = args['pngfile']
        pngfile_actual = getabsfilepath(gelfile, pngfile_relative)  # 'pngfile' is relative to gelfile.
        # make sure we update gelext after re-setting to pngfile:
        # However, we do not want to update gelbasename
        # gelfp_no_ext
        pngfp_wo_ext, pngext = os.path.splitext(pngfile_actual)
        pngext = pngext.lower()
    elif gelext in ('.png', '.jpg', '.jpeg'):
        logger.debug("args['pngfile'] not specified, but gelfile ext is %s, using gelfile (%s) as pngfile.",
                     gelext, gelfile)
        pngfp_wo_ext, pngext = gelfp_wo_ext, gelext
        pngfile_actual = gelfile
        pngfile_relative = os.path.basename(gelfile)
    else:
        logger.warning("args['pngfile'] is None? : %s", args['pngfile'])
        logger.warning("args['gelfile'] is: %s", args['gelfile'])
        logger.warning("gelfile is: %s", gelfile)
        logger.warning("args is: {%s}", printdict(args))
        raise TypeError("Could not determine pngfile version of gel image.")

    # Get size of png image:
    pngimage = Image.open(pngfile_actual)
    imgwidth, imgheight = pngimage.size
    pngimage.fp.close()

    # Convert any relative values (fractions, percentage):
    ypad, yoff = ensure_numeric([args['ypadding'], args['yoffset']], imgheight)

    # convert relative values ('5%' or 0.05) to absolute image values:
    xmargin = ensure_numeric(args['xmargin'], imgwidth)
    xtra_right = ensure_numeric(args['xtraspaceright'], imgwidth)

    ext = '.svg'
    svgfnfmt = args.get('svgfnfmt', "{pngfnroot}_annotated{ext}")
    folderpath = os.path.dirname(pngfile_actual)
    pngfnroot = os.path.basename(pngfp_wo_ext)
    svgfilename = svgfnfmt.format(pngfnroot=pngfnroot, gelfnroot=gelfnroot, ext=ext,
                                  lanefnroot=lanefnroot, yamlfnroot=yamlfnroot)
    svgfilename = os.path.join(folderpath, svgfilename)
    size = dict(width="{}px".format(imgwidth+xtra_right),
                height="{}px".format(imgheight+yoff))
    # Apparently, setting width, height (using **size) cannot be done on instantiation:
    dwg = svgwrite.Drawing(svgfilename, profile='tiny')
    dwg.attribs.update(size)
    g1 = dwg.add(dwg.g(id='Gel'))   # elements group with gel file

    # Add png image data to svg drawing object:

    # xlink:href is first argument 'href'.
    # width="100%" height="100%" or  width="524" height="437" ?
    # additional image attribs: overflow, width, height, transform
    if args.get('embed', True):
        filedata = open(pngfile_actual, 'rb').read()
        # when you DECODE, the length of the base64 encoded data should be a multiple of 4.
        datab64 = base64.encodebytes(filedata)
        # See http://www.askapache.com/online-tools/base64-image-converter/ for info:
        mimebyext = {'.jpg': 'image/jpeg',
                     '.jpeg': 'image/jpeg',
                     '.png': 'image/png'}
        mimetype = mimebyext[pngext]
        logger.debug("Embedding data from %s into svg file.", pngfile_actual)
        imghref = "data:"+mimetype+";base64,"+datab64.decode()
    else:
        imghref = pngfile_relative
        logger.debug("Linking to png file %s in svg file.", pngfile_actual)
    img = g1.add(dwg.image(imghref, width=imgwidth, height=imgheight))  # Using size in percentage doesn't work.
    img.translate(tx=0, ty=yoff)

    # Add annotations to svg drawing object:
    g2 = dwg.add(dwg.g(id='Annotations'))   # Make annotations group

    # Consider deprechating xspacing argument; I only ever use xmargin.
    # Number of spaces is 1 less than number of lanes.
    xspacing = (imgwidth-sum(xmargin))/(len(laneannotations)-1) if not args.get('xspacing') else args['xspacing']

    logger.debug("xmargin: %s", xmargin)
    logger.debug("xspacing: %s", xspacing)

    for idx, annotation in enumerate(laneannotations):
        text = g2.add(dwg.text(args['textfmt'].format(idx=idx+args['laneidxstart'], name=annotation)))
        for att in ('font-size', 'font-family', 'font-weight'):
            argkey = att.replace('-', '')
            if args[argkey]:
                text.attribs[att] = args[argkey]
        text.translate(tx=xmargin[0]+xspacing*idx, ty=yoff-ypad)
        text.rotate(-args['textrotation'])  # Negative rotation, because that is the most intuitive.

    dwg.save()
    logger.info("Annotated gel saved to file: %s", svgfilename)

    return dwg, svgfilename


def ensure_png_exists(gelfile, args, yamlfile=None, lanefile=None):
    """Ensures that we have a png file to overlay our annotations on.

    If args['gelfile'] already is a png, then just skip.
    If gelfile is a .GEL file: Make PNG from GEL file and update args to reflect that change.

    Arguments:
        gelfile: Filename of the gel file which we are annotating.
        args: configuration arguments. If gelfile is not specified, use args['gelfile']
        yamlfile: Load extra config arguments from this file.
        lanefile: The annotationsfile with gel/lane annotations.

    Returns:
        None (no return value)

    Raises:
        ValueError if gelfile extension is not recognized.
        Will also raise any exception thrown by convert()
    """
    if args is None:
        args = {}
    if gelfile is None:
        gelfile = args['gelfile']
    _, gelext = os.path.splitext(gelfile)
    gelext = gelext.lower()
    if gelext.lower() in ('.png', '.jpg', '.jpeg'):
        # Hmm... it might be nicer to allow rotation of an existing png image, not only .gel files?
        if any(args.get(k) for k in ('invert', 'crop', 'rotate')):
            logger.debug("invert, crop or rotate requested; performing conversion even if gelfile is PNG...")
            convert(gelfile, args, yamlfile, lanefile)
        elif not args.get('reusepng', True):
            pass    #
        return
    if args.get('pngfile') and args.get('reusepng', True):
        # We have a png file and want to re-use it and not re-generate it:
        return

    if gelext.lower() == '.gel':
        # convert gel to png:
        args.setdefault('convertgelto', 'png')
        logger.info("ensure_png_exists: Converting %s to png...", gelfile)
        convert(gelfile, args, yamlfile, lanefile)   # convert will update args['pngfile']
    elif gelext.lower() in ('.tif', '.tiff'):
        # convert tif to png:
        if args.get('linearize') is None:  # set sane default
            args['linearize'] = False
        args.setdefault('convertgelto', 'png')
        convert(gelfile, args, yamlfile, lanefile)
    else:
        raise ValueError("gelfile extension not recognized. Recognized extensions are: .gel, .png, .jpg.")


def annotate_gel(gelfile=None, args=None, yamlfile=None, annotationsfile=None):
    """Annotate gel according to the given configuraiton args.

    This function is the primary function in charge of annotating gel files.
    It works as an outer wrapper with a series of responsibilities:
        0) Load yaml and annotations files.
        1) Creates/ensures a PNG file.
        2) Create SVG with annotations.
        3) Converts svg to png if requested and other stuff.

    Arguments:
        args: dict with standard arguments.
        gelfile: main gelfile.
        annotationsfile: file with annotations. Is this actual or relative to gelfile? - Relative.
        yamlfile: file with options in yaml format. Is this actual or relative to gelfile? - Relative.

    Returns:
        A 3-tuple with:
            drawing,
            svgfilename,
            args - updated args dict with anything that may have been changed as a result of the run.

    """
    logger.debug("""annotate_gel invoked with gelfile='%s', yamlfile='%s', annotationsfile='%s',
                 and args=%s""", gelfile, yamlfile, annotationsfile, printdict(args))
    if args is None:
        args = {}
    if isinstance(args, argparse.Namespace):
        args = args.__dict__
    if yamlfile is None:
        yamlfile = args.get('yamlfile')  # Do not update.
    if annotationsfile is None:
        annotationsfile = args.get('annotationsfile')
    if yamlfile:
        yamlfile = getabsfilepath(gelfile, yamlfile)
        try:
            logger.debug("Loading additional settings (those not already specified) from file: %s", yamlfile)
            yamlsettings = yaml.safe_load(open(yamlfile))
            # for key, value in settings.items():
            #    setattr(argns, key, value)
            # Make sure to update in-place:
            args.update(mergedicts(yamlsettings, args))
        except IOError as e:
            logger.debug(e)
            logger.debug("No existing yaml file: %s -- That's OK.", yamlfile)
            logger.debug("-- cwd is: %s", os.getcwd())
        except KeyError as e:
            logger.debug("KeyError: %s", e)
    if gelfile is None:
        gelfile = args['gelfile']
        args['_primary_file_mode'] = 'yaml'

    # If in yaml mode, ensure that args['gelfile'] correctly reflects the gelfile used:
    if args.get('_primary_file_mode') == 'yaml' or args.get('gelfile_remember', True):
        args['gelfile'] = gelfile
    # 'gelfile_last_used' is a fallback mechanism for cases where the app is started in gel_is_primary mode,
    # but we then save yaml file under a different name.
    args['gelfile_last_used'] = gelfile

    # args = mergeargs(argsns=args, argsdict=yamlsettings, excludeNone=True, precedence='argns')
    logger.debug("Ensuring that we have a PNG file to annotate using ensure_png_exists(%s, ...). "
                 "If a PNG file is not available, or if args['reusepng'] is false, "
                 "then a PNG file will be generated from the GEL file.", gelfile)
    ensure_png_exists(gelfile, args, yamlfile=yamlfile, lanefile=annotationsfile)
    # Note: args is updated in-place. yamlfile and lanefile is only used to generate pngfilename.

    # MAKE SVG FILE WITH ANNOTATIONS: #
    # annotationsfile is relative to gelfile; make_svg takes care of it.
    logger.debug("Making annotated SVG file using make_svg(%s, ...)", gelfile)
    dwg, svgfilename = make_svg(gelfile, args, annotationsfile=annotationsfile, yamlfile=yamlfile)

    # Convert SVG to PNG: #
    if args.get('svgtopng'):
        # svg's base64 encoding is not as optimal as a native file but about 40-50% larger.
        # Thus, it might be nice to be able to export
        # print "PNG export not implemented. Requires Cairo."
        # svg2pngfn = args['svgtopngfile'] = svg2png(svgfilename)
        logger.debug("Converting svg to png using svg2png(%s)", svgfilename)
        svg2pngfn = svg2png(svgfilename)    # not saving svgtopngfile in args...
    else:
        svg2pngfn = None

    # Open file: #
    if args.get('openwebbrowser'):
        # On OS X we need to add "file://" in front of the file path for it to work
        open_path = "file://" + os.path.abspath(svgfilename)
        print("Opening annotated svg file %s with default application for that file type." % open_path)
        logger.info("Opening annotated svg file %s", open_path)
        webbrowser.open(open_path)
        if svg2pngfn:
            open_path = "file://" + os.path.abspath(svg2pngfn)
            print("Opening annotated PNG file %s (converted from svg file) with default application." % open_path)
            logger.info("Opening annotated PNG file %s", open_path)
            webbrowser.open(open_path)
            # webbrowser.open will open with either default browser OR default application.
            # If you want to open with default application, use os.startfile on windows
            # subprocess.call(['open', filename]) on OSX, and
            # subprocess.call(['xdg-open', filename])  on POSIX (or possibly just use open)
            # c.f. http://stackoverflow.com/questions/434597/open-document-with-default-application-in-python

    if args.get("remember_gelutils_version", True):
        args['gelutils_version'] = __version__

    # Running ensure_png_exists and make_svg can update args dict, e.g. with automatic dynamic range.
    # if yamlfile and args.get('updateyaml', True):
    config_save_final_params = args.get('config_save_final_params', args.get('saveyamlto', True))
    if config_save_final_params:
        args['gelfile'] = gelfile
        args['yamlfile'] = yamlfile
        args['annotationsfile'] = annotationsfile
        if config_save_final_params is True:
            final_params_fn = yamlfile
        else:
            assert isinstance(config_save_final_params, str)
            yamlfile_fnroot, yamlfile_ext = os.path.splitext(yamlfile)
            final_params_fn = config_save_final_params.format(config_ext=config_ext, **locals())

        # Not sure if this should be done here or in AnnotateGel GUI app:
        logger.debug("Saving final config parameters to file: %s", final_params_fn)
        # For Python3 it is important that the file mode is correct: binary vs str
        # yaml safe_dump produces a str output, so the file must be opened in str mode:
        with open(final_params_fn, 'w') as fd:
            # Call signature: yaml.dump_all(documents, stream=None, Dumper=<class 'yaml.dumper.Dumper'>,
            # default_style=None, default_flow_style=None, canonical=None, indent=None, width=None,
            # allow_unicode=None, line_break=None, encoding='utf-8', explicit_start=None, explicit_end=None,
            # version=None, tags=None)
            try:
                yaml.safe_dump(args, fd, default_flow_style=False)
            except RepresenterError as e:
                logger.warning("yaml.representer.RepresenterError: %s. args is: %s", e, args)
                raise
    else:
        args['gelfile_last_used'] = gelfile
        args['yamlfile_last_used'] = yamlfile
        args['annotationsfile_last_used'] = annotationsfile

    return dwg, svgfilename, args


if __name__ == '__main__':

    init_logging()

    argns = parseargs()
    cmd_gelfile = argns.gelfile

    drawing, svgfn, updatedargs = annotate_gel(cmd_gelfile, argns)
    if drawing:
        print("Annotated svg saved as:", drawing.filename)
