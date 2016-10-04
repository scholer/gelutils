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
# pylint: disable=W0142,C0103

"""

Common module for parsing and handling arguments.


"""
import os
import argparse

from .utils import mergedicts


def make_parser(prog='gelannotator', defaults=None,
                description='Gelutils - Convert and Annotate scientific .GEL/TIFF files.',
                **argparser_kwargs):
    """Make a parser to parse command line arguments.

    Default values if not specified are None for most arguments,
    except for switches (store_true/false), where it is the default is the opposite of the first given switch.
    E.g. if add_argument(--dothis, action='store_true'), dothis will default to False, unless
    of course, you specifically also add default=True. You can also add default=None for switches!

    When two switches with same destination are defined, the first will define the default value.
    E.g. below, both linearize and no-linearize are defined having dest=linearize.
    Because linearize is defined first, the default value of linearize will be False.

    Args:
        prog: A string e.g. 'gui' to create a parser customized for GUI app.
        defaults: A dict with default values for the parsers keyword arguments.
        description: A string describing the program for which the parser is used.
        argparser_kwargs: Other keywords passed to argparse.ArgumentParser init.

    Returns:
        An argparse.ArgumentParser instance customized for gelutils usage.

    Examples:
        ap = make_parser('gui', defaults={'openwebbrowser': False}, description='Gelutils Gel Annotator.')

    """
    if defaults is None:
        defaults = {
            'stdout_mode': 'w',
            'stderr_mode': 'w'
        }

    if prog.lower() == 'gui':
        defaults.setdefault('openwebbrowser', True)

    ap = argparse.ArgumentParser(prog="AnnotateGel" if prog.lower == 'gui' else prog,
                                 description=description,
                                 **argparser_kwargs)

    if prog == 'gui':
        # For GUI app the user can browse for gel file so it is not mandatory
        ap.add_argument('file', nargs='?')
        ap.add_argument('--gelfile',
                        help='Explicitly specify the gelfile to use. '
                        'Often used in "yaml-mode" where the primary file is a YAML config file ("yaml-mode"). '
                        'Specifying gelfile with this keyword will save it it the .gaml config file. '
                        'Useful for having multiple .gaml config files all using the same .GEL file, '
                        'e.g. with different crop regions if the GEL file contains multiple gels.')
    else:
        ap.add_argument('gelfile')

    #
    # Testing, logging and debugging parameters:
    # ------------------------------------------
    # parser.add_argument('--dryrun', '-n', action="store_true", help="Dry-run. Do not actually do anything.")
    ap.add_argument('--verbose', '-v', action='count', help="Verbosity.")
    ap.add_argument('--loglevel', default=defaults.get('loglevel'),
                    help="Logging level, e.g. 10, 30, or 'DEBUG', 'INFO.")
    ap.add_argument('--logtofile', default=defaults.get('logtofile'),
                    help="Write log output to file rather than console.")
    # Note: If action='store_true', then default is False not None.
    # Using default=None so None can be used to indicate a value that has not been specified.
    ap.add_argument('--disable-logging', dest='disable_logging', action='store_true', default=None,
                    help="Disable logging system.")
    # When adding a dest already in place, the default is not overwritten.
    ap.add_argument('--enable-logging', dest='disable_logging', action='store_false',
                    help="Enable logging system.")
    # Redirection of stdout/stderr (useful if console display is not available when launching program).
    ap.add_argument('--stdout', metavar="filename", default=defaults.get('stdout'),
                    help="Write stdout stream to file rather than console. "
                         "This may be useful in cases where a terminal is not available, "
                         "e.g. when invoking AnnotateGel on OSX with an Automator script.")
    ap.add_argument('--stderr', metavar="filename", default=defaults.get('stderr'),
                    help="Write stderr stream to file rather than console. Defaults to same value as stdout.")
    ap.add_argument('--stdout-mode', metavar="file mode", default='w',
                    help="File open mode for stdout stream, if stdout is given. Default: 'w'.")
    ap.add_argument('--stderr-mode', metavar="file mode", default='w',
                    help="File open mode for stderr stream, if stderr is given. Default: 'w'.")

    #
    # File inputs and outputs:
    # ------------------------
    # TODO: Rename convertgelto to image_format
    ap.add_argument('--convertgelto', default='png', metavar="png/jpg/etc",
                    help="Convert gel to this format.")
    # ap.add_argument('--png', action='store_true', help="Save as png.")
    ap.add_argument('--overwrite', action='store_true', default=True,
                    help=""""Overwrite existing png file. If set to false, the program will
                    re-use the any old PNG it finds instead of re-generating the PNG from the .GEL file.
                    If you are playing around with e.g. the annotations, this can save a bit of computation.""")
    ap.add_argument('--no-overwrite', action='store_false', dest='overwrite',
                    help="Do not overwrite existing png file.")
    # filename inputs and outputs:
    ap.add_argument('--pngfnfmt', default="{yamlfnroot}_{dr_rng}{N_existing}{ext}", metavar="format_string",
                    help=("Customize the png filename using python string formatting.",
                          "Note that {ext} includes the dot in '.png'"))
    ap.add_argument('--svgfnfmt', default="{pngfnroot}_annotated{ext}", metavar="format_string",
                    help=("Format for the svg filename, if created, using python string formatting."
                          "Valid placeholders include: {pngfnroot}, {gelfnroot}, {ext}, {ext} includes dot in '.svg'"))
    ap.add_argument('--pngfile', metavar="filename",
                    help="Use this png/image file instead of the specified gelfile.")
    # TODO: What is the functional difference between reusepng and overwrite ?
    ap.add_argument('--reusepng', action='store_true', default=None,
                    help=("Prefer png file over the specified gelfile,"
                          "IF a PNG file with matching the output already exists."
                          "Rotations and scaling are still applied, but not "))
    ap.add_argument('--no-reusepng', action='store_false', dest='reusepng',
                    help="Do not use pngfile, even if it is specified.")
    # Perform substitution of input filenames, e.g. to remove illegal characters.
    ap.add_argument('--filename-sub', nargs='+', metavar=("FIND", "REPLACE"),
                    help="Substitute FIND with REPLACE in output filename. ")
    # "If FIND is given and REPLACE isn't, then REPLACE defaults to ''.")
    ap.add_argument('--filename-sub-re', nargs='+', metavar=("FIND", "REPLACE"),
                    help="Substitute all substrings matching the regex FIND with REPLACE in output filename.")

    #
    # Config / yaml parameters:
    # -------------------------
    ap.add_argument('--no-load-system-config', action="store_false", dest="load_system_config",
                    help="Load standard system/user config. (Default is to load system config if one is found.)")
    ap.add_argument('--load-system-config', action="store_true",
                    help="Load standard system/user config.")
    ap.add_argument('--config-template', metavar="filename", default=defaults.get("config_template"),
                    help=("Use this yaml-formatted file as config template."
                          "The difference between config-template and config-filename is that the"
                          "template will never be updated/overwritten. It is just default config."))

    # TODO: Rename yamlfile keyword to config_filename
    ap.add_argument('--yamlfile', metavar="filename",
                    help="Load and save config parameters from YAML file, update and save.")
    # TODO: Rename to config_save_final_params  - final/fixed/static/post/processed
    ap.add_argument('--saveyamlto', metavar="filename",
                    default=defaults.get("saveyamlto"),
                    help="Force saving yaml to this file when complete.")
    # TODO: Rename to config_update_display - config/yaml/parameters/params/args/configuration/options
    # Usually this should be left disabled, but can be used to display and tune auto-calculated parameters.
    ap.add_argument('--no-update-yaml', dest='updateyaml', action='store_false', default=None,
                    help="Do not update yaml settings after run to reflect the final settings used.")
    ap.add_argument('--update-yaml', dest='updateyaml', action='store_true',
                    help="Update yaml settings after run to reflect the settings used.")

    # "save", "record", "write", "persist" or "remember" - add static parameters to config:
    # Edit, probably just always save gelutils version to final_params config file.
    ap.add_argument('--remember-gelutils-version', action='store_true', default=defaults.get('save_gelutils_version'),
                    help="Save svg as png (requires cairo package).")
    # Remember/record/save input gel filename to yaml config.
    # TODO: Rename to "record-gelfile" ?
    # TODO, edit: Maybe just have a mandatory "gelfile_lastused" entry?
    # TODO, edit: Or just always save the gelfile in the static version?
    ap.add_argument('--gelfile-remember', action='store_true', default=None,
                    help="Save last used gelfile in config for later use.")
    ap.add_argument('--no-gelfile-remember', dest='gelfile_remember', action='store_false', default=None,
                    help="Do not save last used gelfile in config for later use.")

    ap.add_argument('--gelfile_last_used', metavar="filename",
                    help="The last used gel/image file. The program will update this on every run.")
    ap.add_argument('--yamlfile_last_used', metavar="filename",
                    help="The last used yaml config file. The program will update this on every run.")
    ap.add_argument('--annotationsfile_last_used', metavar="filename",
                    help="The last used annotations file. The program will update this on every run.")

    #
    # Image processing parameters:  (geltransformer, gelannotator)
    # ----------------------------
    # TODO: Prefix all image processing/transformation keywords with "image_".
    ap.add_argument('--crop', nargs=4, type=int, metavar=('LEFT', 'UPPER', 'RIGHT', 'LOWER'),
                    help="""Crop image to this box (left upper right lower) aka (x1 y1 x2 y2),
                    Values can be either pixel values [500, 100, 1200, 400],
                    or fractional/percentage values [5%%, 3%%, 95%%, 0.9].
                    Note: Yes, 0.9 is 90%%. If gel image is 1000 pixels wide, 0.9 or 90%% are equivalent to 900 pixels.
                    OBS! Note that by default the values are interpreted as <strong>ABSOLUTE COORDINATE VALUES</strong>
                    from the top, left pixel. If you want to change this behaviour such that the
                    RIGHT and LOWER values are interpreted as the amount to crop away, e.g.
                    'crop 12%% from the right edge', set ```cropfromedges``` to true. """)
    ap.add_argument('--cropfromedges', action='store_true', default=None,
                    help="""If true, the crop values RIGHT and LOWER defined above
                    specifies pixels from their respective edges
                    instead of absolute coordinates from the upper left corner.
                    Default: false.""")

    ap.add_argument('--scale', metavar="scalefactor",
                    help=""""Scale the gel by this amount.
                    Can be a single value for uniform scaling, or two values for different scaling in x vs y.
                    Can be given as float (0.1, 2.5) or percentage (10%%, 250%%).""")

    ap.add_argument('--rotate', metavar="angle", type=float,
                    help="Rotate gel image by this angle (counter-clockwise). Default: 0.")
    ap.add_argument('--rotateexpands', action='store_true', default=None,
                    help="""When rotating, the image size expands to make room.
                    False (default) means that the gel will keep its original size.""")

    ap.add_argument('--flip_h', action='store_true', default=None,
                    help="Flip image horizontally left-to-right.")
    ap.add_argument('--flip_v', action='store_true', default=None,
                    help="Flip image vertically top-to-bottom.")

    # Contrast and display: Converting raw data to human-readable png image:
    # TODO: Prefix all keywords with "image_"
    ap.add_argument('--linearize', action='store_true', default=None,
                    help="Linearize gel input data stored in Square-Root Encoded Data (if Typhoon).")
    ap.add_argument('--no-linearize', action='store_false', dest='linearize',
                    help="Linearize gel (if e.g. typhoon).")
    ap.add_argument('--dynamicrange', nargs='+', metavar=("MIN", "MAX"),
                    help="""Specify dynamic range (contrast). Valid argumets are 'MIN MAX', 'MAX' and 'auto',
                    e.g. '1000, 20000' to set range from 1000 to 20000,
                    '20000' to set range from zero to 20000, and 'auto' to determine range automatically.
                    MIN and MAX are usually provided as absolute values e.g. '300 5000',
                    but can also be specified as percentage values, e.g. '0.1%% 99%%'.
                    If percentage or decimal values are given, the dynamic range is set such that
                    MIN %% of the pixels are below the lower range
                    and (1.0 - MAX) of the pixels are above the dynamic range.
                    If only one integer argument is given if is assumed to be the max, and min is set to 0.
                    If specifying 'auto', the software will try to determine
                    a suitable contrast range automatically.""".strip())
    # ap.add_argument('--autorange', action='store_true', help="Dynamic range, min max, e.g. 300 5000.")
    ap.add_argument('--invert', action='store_true', default=None,
                    help="Invert gel data, so zero is white, high intensity black.")
    ap.add_argument('--no-invert', action='store_false', dest='invert',
                    help="Do not invert image data. Zero will be black, high intensity white.")

    ap.add_argument('--pngmode', default='L',
                    help="PNG output format (bits per pixel). L = 8 bit integer, I = 16/32 bit.")

    #
    # Annotations config parameters:
    # ------------------------------
    if prog.lower() in ('gelannotator', 'gui'):

        # Image and text positioning:
        # TODO: Maybe prefix with image_ or img_pos_ or canvas_img_ or svg_img_ or svg_gel_ ?
        # TODO, edit: Some of these are for the text, some are for the image, but they are all somewhat related
        # TODO, edit: in that all relates to the position of text and image relative to each other.
        # TODO, edit: so maybe prefix with pos_img_*/pos_text_* or canvas_image_*/canvas_text_* ?
        ap.add_argument('--yoffset', metavar="int-or-fraction",
                        help="Y offset (how far down the gel image should be).") #, default=100
        ap.add_argument('--ypadding', metavar="int-or-fraction",
                        help="Vertical space between gel image and annotations.") #, default=100
        ap.add_argument('--xmargin', nargs=2, metavar=("left", "right"),
                        help="Margin to the right and left of lane annotations to the outer edge of GEL image.") # , default=(30, 40)
        ap.add_argument('--xspacing', metavar="int-or-fraction",
                        help="Force a certain x spacing between lanes.")
        ap.add_argument('--xtraspaceright', metavar="int-or-fraction",
                        help="""Add additional padding/whitespace to the right side of the gel image.
                        This is sometimes needed if the gel is not wide enough for the last lane annotation.""")

        # Annotation/text parameters:
        # TODO: prefix all keywords with "text_" (or "annotations_" ?)
        ap.add_argument('--textrotation', type=int, dest='textrotation', metavar="angle",
                        help="Rotate lane annotations by this angle (counter-clockwise). Default: 70.")
        ap.add_argument('--fontsize', type=int, metavar="size (int)",
                        help="Specify default font size, e.g. 12 or 16.")
        ap.add_argument('--fontfamily',
                        help="Specify default font family, e.g. arial or MyriadPro.")
        ap.add_argument('--fontweight',
                        help="""Font weight: normal | bold | bolder | lighter |
                        100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | inherit.""")
        # TODO: Rename to text_format (not fmt)
        ap.add_argument('--textfmt', metavar="format_string",
                        help="""How to format the lane annotations, e.g. '{idx} {name}'.
                        Format keys include: idx, name. Default: '{name}'.""")
        # TODO: Rename to text_idxstart (not lane)
        ap.add_argument('--laneidxstart', type=int,
                        help="Change the start number of the {idx} format parameter of lane annotations.")

        #
        # Annotation parameters:
        # ----------------------
        ap.add_argument('--annotationsfile', metavar="filename",
                        help="Load lane annotations from this file. "
                        "If not specified, will try to guess the right file.")

        # lineinputstyle->lines_inputstyle, lines_includeempty, lines_listchar, lines_commentchar, lines_commentmidchar
        # TODO: Maybe change all "lines_" to "annotations_" or text_input_?
        ap.add_argument('--lines_inputstyle', metavar="string-spec",
                        help="""This can be used to change how lines in the sample annotation file are interpreted.
                        Default is to use all non-empty lines that does not begin with '#'.
                        Set this to 'wikilist' to only include lines that starts with either of #, *, -, +.""")
        ap.add_argument('--lines_includeempty', action="store_true",
                        help="""Whether to include empty lines. Not applicable to 'wikilist' lines_inputstyle
                        (use blank lines starting with '#' in this case).""")
        ap.add_argument('--lines_listchar', metavar="string-spec",
                        help="""If annotations are copy-pasted from a wiki/markdown list and you want to strip the
                        list charaacter (e.g. '*' or '#'), specify the character here. Default: auto-detect.""")
        ap.add_argument('--lines_commentchar', metavar="string-spec",
                        help="Lines starting with this character are ignored (comments). Default: auto-detect.")
        # ap.add_argument('--lines_commentmidchar', metavar="string-spec",
        #                 help="Input to the right of this character is ignored (commented out). Default: auto-detect.")

        # TODO: Rename to "svg_embed_png" (or "canvas_embed_png" ?)
        ap.add_argument('--embed', action='store_true', default=True,
                        help="Embed image data in svg file. (default)")
        ap.add_argument('--no-embed', dest='embed', action='store_false',
                        help="Do not embed image data in svg file, link to the file instead. (default is to embed)")

        # TODO: Maybe prefix with "convert" - "convert-svg-to-png" or "svg_convert_to_png" ?
        ap.add_argument('--svgtopng', action='store_true', default=None,
                        help="Save svg as png (requires cairo package).")
        ap.add_argument('--no-svgtopng', action='store_false', dest='svgtopng',
                        help="Do not save svg as png (requires cairo package).")

        # TODO: Rename to to "show_annotated_svg", "show_annotated_png" (or "open", "show", or "display") ?
        ap.add_argument('--openwebbrowser', action='store_true', default=defaults.get('openwebbrowser'),
                        help="Open annotated svg file in default webbrowser. Default: Do not open files.")
        ap.add_argument('--no-openwebbrowser', action='store_false', dest='openwebbrowser',
                        help="Do not open file in webbrowser.")

    return ap


def parseargs(prog='gelannotator', argv=None, defaults=None):#, partial=False, mockstring=None):
    """
    Perform parsing.
    """
    ap = make_parser(prog=prog, defaults=defaults)
    #if partial:
    #    # parse_known_args will not raise errors if sys.argv arguments not recognized by this parser.
    #    # This is useful if you have several parts of the program parsing the arguments.
    #    return ap.parse_known_args()
    argns = ap.parse_args(argv)
    if getattr(argns, 'dynamicrange'):
        if argns.dynamicrange[0] == 'auto':
            argns.dynamicrange = 'auto'
    return argns




def argsnstodict(argsns):
    return argsns.__dict__
