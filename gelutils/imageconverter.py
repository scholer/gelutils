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

Module for converting images.


## How to convert svg to png?

Use cairo / cairosvg / rsvg:
* http://stackoverflow.com/questions/6589358/convert-svg-to-png-in-python
* http://cairosvg.org/
* pypi.python.org/pypi/CairoSVG
* http://cairographics.org/pyrsvg/
* Is not in standard python, requires custom package.

Using PIL?
* Nope
* http://stackoverflow.com/questions/3600164/read-svg-file-with-python-pil
* Need to use cairo.
** EDIT: In fact, you could use PIL, if you instead of creating an SVG just creates a PostScript document:
    >>> from PIL import PSDraw
    See https://pillow.readthedocs.org/handbook/tutorial.html#postscript-printing

So... Trying to get it working on Windows...
* Installed cairosvg
* Installed Pycairo     (http://cairographics.org/pycairo/)
* Looking at cairocffi, https://pythonhosted.org/cairocffi/overview.html
* Installed GTK+ http://gtk-win.sourceforge.net/home/index.php/Main/Downloads
** Alternatives:
*** http://gladewin32.sourceforge.net/
*** http://www.gtk.org/download/
* Nothing.
* http://stackoverflow.com/questions/8704407/how-do-you-install-pycairo-cairo-for-python-on-windows
* http://www.lfd.uci.edu/~gohlke/pythonlibs/#pygtk
* Installers unable to find my anaconda installation...

On Windows, MSYS2 can be used to installing cairo (as well as GTK).

As always, there is also Christian Gohlke's windows build at http://www.lfd.uci.edu/~gohlke/pythonlibs/
 - yes, there is a pycairo wheel, which you as always can install with
    pip install pycairo-1.10.0-cp34-none-win_amd64.whl
 - Note: "The pycairo module was moved to gtk.cairo." ??


## Mac OS X

* Install cairo using homebrew or similar
* Install cffi in your python environment using pip (or conda if available)
* Install cairocffi using pip (or conda if available)
* Install cairosvg using pip (or conda if available)

/usr/local/opt/libffi/lib


## In conclusion:
The best way to get cairo up and running on Windows is:
    1. Find a libcairo-2.dll from *somewhere*,
    2. make sure this dll is available on your path (PATH, not PYTHONPATH = sys.path),
    3. then use this via cairocffi library.

Note that if you have e.g. graphviz installed and available on your path, this could include
libcairo-2.dll files that are NOT compatible with cairocffi.
In this case, if the graphviz library occours BEFORE the library directory with the "good" libcairo-2.dll file,
then cairocffi will try to load the bad dll. It will fail, without finding the "good" dll.
To fix this, make sure the "good" libcairo-2.dll occours before the bad in your PATH environment variable.

CairoSVG will preferably use cairocffi, but will fall back to regular pycairo cairo bindings, which may or may not work.

Of course, on Linux getting cairo to work should not be as much of an issue...

"""

from __future__ import print_function, absolute_import
from six import string_types # python 2*3 compatability
import os
import sys
from subprocess import Popen, PIPE, STDOUT
CLOSE_FDS = not sys.platform.startswith('win')

#import PIL

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

# Local imports:
from .geltransformer import convert



def gel2png(filepath, linearize=True, dynamicrange=None, crop=None, rotate=None, **kwargs):
    """
    Opens a .GEL file, linearize the data, adjust the range, crops, rotates,
    and saves as .png.
    Returns filename of the saved png file.
    """
    #gelbasename, gelext = os.path.split(filepath)
    img, args = convert(filepath, None,
                        linearize=linearize, dynamicrange=dynamicrange, crop=crop, rotate=rotate,
                        **kwargs) # pylint: disable=W0612
    return args['pngfile']


def svg2png(svgfilepath, target='png', tool=None, removeExt=True, **kwargs):
    """
    Converts svgfilepath file to target format.
    If target is just an extension, it is appended to svgfilepath.
    If removeExt is set to false, will save output as path/to/inputfile.svg.png
    instead of path/to/inputfile.png .

    <tool> can be either 'cairo' or 'imagemagick'.
    If tool is not specified, the best available tool is used.
    Tool can also be a tuple of choices from most to least preferred.

    Returns outputfilepath on success.
    Returns None if file could not be converted.
    Raises a ValueError if any arguments could not be interpreted.
    """

    # Cairo reads linked files relative to the cwd, not the svg file.
    # This is kind of weird, but easy to mitigate:
    initialcwd = os.getcwd()
    svgfiledir = os.path.dirname(svgfilepath)
    svgfilename = os.path.basename(svgfilepath)
    if svgfiledir:
        os.chdir(svgfiledir)

    if tool is None:
        # cairo renders the text annotations much better:
        tool = ('cairo', 'imagemagick')
    if isinstance(tool, string_types):
        tool = (tool, )

    methods = {'cairo': cairo_convert,
               'imagemagick': imagemagick_convert}

    outputfn = None
    for key in tool:
        convert_method = methods[key]
        try:
            #outputfn = convert_method(svgfilepath, target, kwargs)
            logger.debug("Trying to convert '%s' using method %s", svgfilename, convert_method)
            outputfn = convert_method(svgfilename, target, kwargs) # currently using filename, not path.
            outputfn = os.path.abspath(outputfn)
            logger.debug("--conversion succeeded, output file: '%s'", outputfn)
            break
        except RuntimeError as e:
            logger.info("Conversion with method '%s' failed: %s", convert_method, e)
    if svgfiledir:
        os.chdir(initialcwd)
    return outputfn

def target2outputfilepath(inputfilepath, target, removeExt=True):
    """
    Converts a generic target param, which can be either an actual filepath,
    or an extension with or without dot prefix, i.e. 'ext' or '.png',
    and returns an actual filepath.
    Refactored to separate function to ensure behaviour consistency across functions.
    """
    if os.path.splitext(target)[1]:
        # target is a filename with extension:
        # above yields '' for 'png' and '.png', but '.png' for 'output.png'
        outputfilepath = target
    else:
        # target is assumed to be a fileext:
        if not target[0] == '.':
            # Ensure that target (file ext) starts with '.', e.g. '.png':
            target = '.' + target
        if removeExt:
            # If input is 'myfile.bmp' and target is '.png', make outputfilepath 'myfile.png':
            outputfilepath = os.path.splitext(inputfilepath)[0] + target
        else:
            # Make outputfilepath myfile.bmp.png
            outputfilepath = inputfilepath + target
    return outputfilepath


def cairosvg_available():
    """ Probes whether cairosvg module is available. """
    try:
        import cairosvg                     # pylint: disable=W0612
        return True
    except ImportError:
        logger.debug("Could not import cairosvg.")
        return False


def debug_cairo():
    """
    Where to find libcairo-2.dll (or equivalent) for cairocffi:
    * https://pythonhosted.org/cairocffi/overview.html#installing-cairo-on-windows
    * http://www.gtk.org/download/ (Windows binaries are not currently available - but you can compile the source)
    ** https://blogs.gnome.org/nacho/2015/02/19/building-gtk-3-with-msvc-2013/
    ** https://blogs.gnome.org/nacho/2014/08/01/how-to-build-your-gtk-application-on-windows/
    * http://gtk-win.sourceforge.net/home/
    * https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
    * http://cairographics.org/releases/

    Where to find original (but old) pycairo builds:
    * http://cairographics.org/pycairo/

    Alternatives:
    * asmeurer has r-cairo bindings: anaconda.org/asmeurer/r-cairo
    ** Requires R binding, goes Python -> R -> r-cairo -> cairo, and back.

    """
    # Test for cairocffi:
    import cffi
    import ctypes.util
    import os, sys
    from fnmatch import fnmatch
    try:
        import cairocffi
        print("cairocffi library available (version %s / VERSION %s / cairo version: %s)" %
              (cairocffi.version, cairocffi.VERSION, cairocffi.cairo_version_string()))
        print("cairocffi module:", cairocffi.__file__)
    except ImportError as e:
        print("Failed to import cairocffi library (cffi-based cairo binding):", e)
        # cairocffi relies on the presence of a proper cairo library,
        # e.g. libcairo-2.dll on Windows.
        # This may be provided by GTK+ bundle (gtk_bundle_3.6.4-20131201_win64)
        # All you have to do is to make sure this is on your PATH (os.environ['PATH'], not PYTHONPATH = sys.path)
        from cffi import FFI
        ffi = FFI()
        # It may be convenient to patch cffi.dlopen() to include
        # print("OSError during dlopen(%s): %s" % (path, e))
        # instead of just pass after OSError.
        # ["%scairo%s" % (prefix, postfix) for prefix in ("", "lib") for postfix in ('', '-2')]
        suitable_lib_found = False
        libname_alternatives = ['cairo', 'cairo-2', 'libcairo', 'libcairo-2']
        for libname in libname_alternatives:
            path = ctypes.util.find_library(libname)
            if path:
                try:
                    lib = ffi.dlopen(path)
                    print("%s: %s --> WORKS! (%s)" % (libname, path, lib))
                    suitable_lib_found = True
                except OSError as e:
                    print("%s: %s --> FAIL! (%s)" % (libname, path, e))
            else:
                print("%s: (Not found)" % (libname,))
        if not suitable_lib_found:
            print("\nManually looking for cairo .dll/.so for cffi binding:")
            # TODO: You should add implicit paths, e.g. /usr/local/lib/ etc, on unix/OSX
            paths = [os.path.abspath(pth) for pth in sys.path if os.path.isdir(pth)] # Nope, not sys.path, but PATH
            paths = [os.path.abspath(pth) for pth in os.environ['PATH'].split(os.pathsep) if os.path.isdir(pth)] # path or PATH env var?
            print("\n".join("%s <- %s" % (p, elem)
                            for p in paths for elem in os.listdir(p)
                            #if any(fnmatch(elem, "*%s*.dll" % alt) for alt in libname_alternatives)))
                            if any(elem in ("%s.dll" % alt, "%s.so" % alt) for alt in libname_alternatives)))
    try:
        import cairo
        print("Original pycairo bindings available for cairo (version %s)" % cairo.version)
    except ImportError as e:
        print("Could not import pycairo library (original cairo binding):", e)


def cairo_available():
    """ Probes which 'cairo' modules is available. Obsolete. """
    available = []
    try:
        import cairosvg                     # pylint: disable=W0612
        available.append('cairosvg')
    except ImportError:
        logger.debug("Could not import cairosvg.")

    try:
        import cairocffi as cairo           # pylint: disable=W0612
        available.append('cairocffi')
        available.append('cairo')
    except ImportError:
        logger.debug("Could not import cairocffi.")
        try:
            import cairo                    # pylint: disable=F0401
            available.append('pycairo')
            available.append('cairo')
        except ImportError:
            logger.debug("Could not import (py2)cairo.")
            return False
    return available

def cairo_convert(inputfilepath, target='png', removeExt=True, **kwargs):   # I do not use kwargs, pylint: disable=W0613
    """
    Convert with cairo library.
    Several libraries:
    * Pycairo   : "original" cairo bindings.
    * cairocffi : "a drop-in replacement for Pycairo", github.com/SimonSapin/cairocffi
    * CairoSVG  : "export svg to pdf, ps and png". Requires Pycairo or cairocffi. github.com/Kozea/CairoSVG

    Raises ValueError if target is not recognized.
    Raises RuntimeError if no cairo library is available.
    """
    if not cairosvg_available():
        print("Cairosvg not available... debugging cairo...")
        # debug_cairo()  # Uncomment to do rudimentary path debugging of cairo installation.
        raise RuntimeError("Cairo library not available.")

    from cairosvg import svg2png, svg2pdf, svg2ps       # pylint: disable=E0611,W0621
    outputfilepath = target2outputfilepath(inputfilepath, target)
    ext = os.path.splitext(outputfilepath)[1].lower()
    if ext not in ('.png', '.pdf', '.ps'):
        raise ValueError("Target '%s' not recognized." % target)

    converters = {'.png': svg2png,
                  '.pdf': svg2pdf,
                  '.ps' : svg2ps
                 }
    convert_method = converters[ext]
    logger.info("Converting %s to %s using method %s", inputfilepath,
                 outputfilepath, convert_method)
    ret = convert_method(url=inputfilepath, write_to=outputfilepath)
    logger.info("%s(url=%s, write_to=%s) returned '%s'",
                 convert_method, inputfilepath, outputfilepath, ret)
    return outputfilepath



### ImageMagick functions:  ###

def imagemagick_available():
    """
    Probes whether ImageMagick command line tool is available on the current system.
    """
    # Test for ImageMagik
    process = Popen('convert --version', shell=True,
                    stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                    close_fds=CLOSE_FDS)
    res = process.stdout.read()
    # On Windows, there is a 'convert' command, which is used to convert FAT to NTFS.
    logger.debug("Imagemagick check: %s", res)
    if 'imagemagick' in res.decode().lower():
        return True
    else:
        logger.warn("ImageMagick NOT FOUND: ")
        return False

def imagemagick_convert(inputfilepath, target='png', removeExt=True, rotate='', scale='', resize='', crop='', cmdlineargs=''):  # pylint: disable=R0912,R0913
    """
    Convert inputfilepath to target using imagemagick.
    <target> can be either a filetype, e.g. 'png' or '.png',
    or a complete new filename, e.g. 'myoutputfile.png'.
    cmdlineargs is a string with arguments passed directly to imagemagic's convert tool,
    e.g. cmdlineargs='-resize <geometry> -rotate <degrees>'.
    I will add some of these as explicit kwargs as needed, but at the moment cmdlinearg is the only way to customize
    the converter's output.

    For a full list of imagemagick commands, see http://www.imagemagick.org/Usage

    Raises RuntimeError if ImageMagick command line tool is not available.

    Pst... there's also python wrappers for imagemagick:
    * pypi.python.org/pypi/PythonMagickWand/
    * pypi.python.org/pypi?%3Aaction=search&term=imagemagick
    """
    ## Try to use ImageMagick
    ## From eea.converter project, file converter/convert.py
    # The terms 'basename' and 'filename' are somewhat ambiguous:
    # - filename can either just 'filename.ext', or it can be the full filepath '/path/to/filename.txt'
    # - basename can also mean 'filename.ext' (python), or it can mean just 'filename' without extension (wikipedia, ruby)
    # I adopt the following convension:
    # - FILEPATH is the only term used for the full '/path/to/file.ext' (both absolute and relative).
    # - FILENAME and BASENAME both mean 'file.ext' and nothing else.
    # - FILEEXT or FILENAMEEXT refer to '.ext'. (with leading '.')
    # - FILETYPE or EXTTYPE refer to 'ext' or 'EXT'.
    # - FILESTEM or FILENAMESTEM refer to 'file' (without directory and extension).
    # - If you need to refer to '/path/to/file' (full filepath without extension)
    #   you should always make that very explicit and always use os.path.splitext(inputfilepath)[0]

    #dirpath = os.path.dirname(inputfilepath)
    #filename = os.path.basename(inputfilepath)
    #filenamestem, filenameext = os.path.splitext(filename)
    outputfilepath = target2outputfilepath(inputfilepath, target)
    ## Check that ImageMagick is available:
    if not imagemagick_available():
        raise RuntimeError('ImageMagick is not installed. Aborting...')


    if resize:
        if isinstance(resize, string_types):
            resize = '-resize ' + resize
        elif len(resize) == 2:
            resize = "-resize {}x{}".format(*resize)
        else:
            raise ValueError("Format for argument resize '%s' not recognized." % (resize, ))
    elif scale:
        if isinstance(scale, string_types):
            scale = '-scale ' + scale
        else:
            scale = '-scale {}'.format(scale)
    if rotate:
        if isinstance(rotate, string_types):
            scale = '-rotate ' + rotate
        else:
            scale = '-rotate {}'.format(rotate)
    if crop:
        if isinstance(rotate, string_types):
            scale = '-crop ' + rotate
        else:
            scale = '-crop {}'.format(rotate)       # Not really sure this would work...

    # ImageMagick convert command format is:
    # convert [reader options] <inputfile> [converter options] outputfile
    cmd = "convert {infile} {rotate} {resize} {scale} {crop} {cmdargs} {outfile}".format(
        infile=inputfilepath, rotate=rotate, resize=resize, scale=scale, crop=crop,
        cmdargs=cmdlineargs, outfile=outputfilepath
    )

    process = Popen(cmd, shell=True,
                        stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                        close_fds=CLOSE_FDS)
    res = process.stdout.read()
    if res:
        logger.info("ImageMagick command produced stdout messages: %s", res)

    return outputfilepath




if __name__ == '__main__':

    #from argutils import parseargs
    #argns = parseargs('imageconverter')
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('function')
    ap.add_argument('inputfiles', nargs="+")
    ap.add_argument('--target', default='png', help="Target file/filetype.")
    ap.add_argument('--loglevel', default=logging.WARNING, help="Logging level.")

    argns = ap.parse_args()

    functions = {'svg2png' : svg2png,
                 'convertgel': gel2png}

    for input_fn in argns.inputfiles:
        functions[argns.function](input_fn, target=argns.target)
