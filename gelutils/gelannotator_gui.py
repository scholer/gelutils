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

Module for annotating gels.

Annotates a gel image with lane descriptions from annotaitons file,
saves as svg (maybe add pdf ability?).

= Workflow: =
The GUI is used mostly as an editor for the yaml and laneannotations files.
When pressing "process", the files are saved and gelannotator.compile(args) is invoked.

The files are then re-read, the gel is processed, the svg is created with annotations
and png and svg files are saved, the omnipresent args is also saved.

"""

from __future__ import print_function

try:
    from tkFileDialog import askopenfilename
except ImportError:
    # python 3:
    from tkinter.filedialog import askopenfilename      # pylint: disable=F0401

import os
import yaml
import webbrowser

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

from gelannotator import annotate_gel, find_yamlfilepath, find_annotationsfilepath
from argutils import parseargs, make_parser, mergedicts
from utils import init_logging, getrelfilepath, getabsfilepath, printdict
from tkui.gelannotator_tkroot import GelAnnotatorTkRoot

from utils import open_utf  # unicode writer.
open = open_utf     # overwrite built-in, yes that's the point: pylint: disable=W0622

def yaml_get(filepath, default=None):
    """ Load yaml from filepath. Return default if file could not be loaded. """
    try:
        with open(filepath) as fd:
            data = yaml.safe_load(fd)
            logger.debug("yaml file loaded: %s", filepath)
    except IOError:
        logger.debug("Could not find/load yaml file %s", filepath)
        data = default
    return data


class GelAnnotatorApp(object):   # pylint: disable=R0904
    """
    Main gel annotator App object.
    Encapsulates Tk root GUI object.

    TODO: Add feature that allows the user to specify 'crop', and 'xmargin' by clicking a PIL image.
    Implementation alternatives:
    * Use matplotlib
    * Use tkinter
    * Use something else?

    Other projects with interactive crop, rotate, etc:
    * cropgui : tkinter python crop gui application, http://emergent.unpythonic.net/01235516977, https://github.com/jepler/cropgui/
    * photo_splitter : Splits a photo into several smaller pieces, very nice python tkinter gui app, https://github.com/dnouri/photo_splitter
    * cropy   : No GUI, but tries to guess the optimal cropping parameters/content provided a given size, https://github.com/mapado/cropy
    * pycrop  : Another entropy-based "auto-crop" tool, https://github.com/christopherhan/pycrop

    After looking at cropgui and photo_splitter, I think Tkinter is a viable option.
    How it should work:
    * Display the image in a frame.
    * A vertical radio button to select the argument you are adjusting: crop, xmargin, rotate.
    * Rotate should actually rotate the preview image. (That is easier than having to make rotated rectangles, etc)
    * Scale should be a separate radio-button with options "100%, 50%, 33%, 25%" and should scale the preview image.
    * Crop is a red-framed overlay of the cropped area. It can be drag-drop of edged, or user can draw a new rectangle.
    * xmargin is a horizontal ruler that extends from the left to the right. Is dependent on crop.
    * Rotate can use the same horizontal ruler. Rotation can be controlled by aligning the ends of the ruler.
    ** Consider also having a number-wheel for adjusting rotation?

    How much would it take to make automatic functions?

    xmargin: can be extracted from the well pattern at the top of the gel.
    * Locate wells by...?
    * FFT can probably be used to determine the well spacing, since the pixel values vs column number
      will look like a square wave, http://en.wikipedia.org/wiki/Square_wave
    * Then look for when the gel image does not match the FFT approximation.
    * The first and last well is the first and last of the fft wells where the FFT approximation is still good.
    * numpy functions: fft.fft, fft.rfft, fft.rfftfreq
    * scipy functions: fftpack  # http://docs.scipy.org/doc/scipy-0.14.0/reference/tutorial/fftpack.html


    rotation: adjusted using the bottom of the wells. These can usually be identified from the sharp vertical peak.
    * Only use the top 10% of the gel.
    * For each column of pixels, determine if there is one that stands out. Use the derivative and find the first significant peak.
    * Filter for badly identified pixels (where the position "jumps").
    * "Plot" the pixels that stands out vs the column and make a linear fit. [Figuratively]
    * Use the slope of the linear fit to determine rotation.
    """
    def __init__(self, args):           # pylint: disable=W0621
        self.Args = args                # only saved to make init easier.
        logger.debug("GelAnnotatorApp initializing with args=%s", printdict(args))
        self.Root = tkroot = GelAnnotatorTkRoot(self, title="Gel Annotator GUI")
        # self.AnnotationsText, self.YamlText
        self.Root.bind_all("<Control-Return>", self.annotate)
        self.Root.AnnotationsText.bind("<Control-Return>", self.annotate)
        self.Root.YamlText.bind("<Control-Return>", self.annotate)

        ## We generally do not want gelfile to be in args after this point:
        gelfilepath = args.pop('gelfile', '')
        if not gelfilepath:
            # Better to allow tkinter to fully initialize before making user prompts:
            self.Lastuseddir = os.path.expanduser('~')
            tkroot.after_idle(self.browse_for_gelfile)
        else:
            #gelfilepath = os.path.realpath(gelfilepath) # no reason to do this?
            self.Lastuseddir = os.path.dirname(gelfilepath)
            self.set_gelfilepath(gelfilepath)
            self.reset_aux_files(gelfilepath)

    def reset_aux_files(self, gelfilepath):
        """
        Resets yaml and annotation files after changing the gelfile.
        Remember that all filepaths except gelfile should be given relative to gelfile.
        """
        # Desired location for yaml file, either input or based on gel file:
        args = self.Args    # pylint: disable=W0621
        yamlfilepath = args.pop('yamlfile', '')
        if not yamlfilepath:
            yamlfilepath = find_yamlfilepath(gelfilepath)
            yamlfilepath = getrelfilepath(gelfilepath, yamlfilepath)
        annotationsfilepath = args.pop('annotationsfile', '')
        # Desired location for annotations file, either input or based on gel file:
        if not annotationsfilepath:
            annotationsfilepath = find_annotationsfilepath(gelfilepath)
            annotationsfilepath = getrelfilepath(gelfilepath, annotationsfilepath)

        self.set_yamlfilepath(yamlfilepath)
        self.set_annotationsfilepath(annotationsfilepath)

        #try:
        #    self.load_yaml()
        #except (IOError, OSError) as e:
        #    print(str(e), "-- No problem.")
        self.init_yaml(args)
        try:
            self.load_annotations()
        except (IOError, OSError) as e:
            logger.debug("%s -- No problem, will save to default when annotating.", e)


    def get_gelfilepath(self, ):
        """ Returns content of gel-filepath entry widget. """
        return self.Root.Gelfilepath.get()

    def set_gelfilepath(self, filepath):
        """ Sets content of gel-filepath entry widget. """
        self.Root.Gelfilepath.set(filepath)
        self.Root.Gelfiledirectory.set(os.path.dirname(os.path.abspath(filepath)))
        #set_workdir(value)

    def getgeldir(self):
        """ Returns directory of gel-filepath entry widget, if not empty else user home dir. """
        gelfilepath = self.get_gelfilepath()
        if gelfilepath:
            return os.path.dirname(gelfilepath)
        else:
            return os.path.expanduser('~')

    def get_yamlfilepath(self, ):
        """ Returns content of yaml-filepath entry widget. """
        return self.Root.Yamlfilepath.get()

    def set_yamlfilepath(self, value):
        """ Sets content of yaml-filepath entry widget. """
        self.Root.Yamlfilepath.set(value)

    def get_yaml(self):
        """ Returns content of yaml text widget. """
        return self.Root.get_yaml()

    def set_yaml(self, value):
        """ Set content of yaml text widget. """
        #print("Setting content of yaml widget to:", value)
        self.Root.set_yaml(value)

    def init_yaml(self, args, filepath=None):       # pylint: disable=W0621
        """
        Merge args with yaml file (args take precedence).
        """
        #if args is None:
        #    args = self.Args
        gelfile = self.get_gelfilepath()
        yamlfile_relative = self.get_yamlfilepath()
        fn = filepath or getabsfilepath(gelfile, yamlfile_relative)
        default_config_file = args.pop('default_config', None)
        default_config = yaml_get(default_config_file, {}) \
                            if default_config_file else {}
        yamlconfig = yaml_get(fn, default_config)
        try:
            with open(fn) as fd:
                yamlconfig = yaml.safe_load(fd)
                logger.debug("loading yaml file: %s", fn)
        except IOError:
            logger.debug("Could not find/load yaml file %s", fn)
            yamlconfig = {}
        logger.debug("yamlconfig: %s", yamlconfig)
        logger.debug("args: %s", printdict(args))
        args.update(mergedicts(yamlconfig, args))
        #self.Args = args
        self.set_yaml(yaml.dump(args, default_flow_style=False))


    def load_yaml(self, filepath=None, filepath_is_relative_to_gelfile=True):
        """
        Load content of yaml file into yaml text widget.
        If filepath is provided, should it be relative to gelfile?
        """
        if filepath is None:
            filepath = self.get_yamlfilepath() # get_yamlfilepath returns relative to gelfile.
        if filepath_is_relative_to_gelfile:
            # Obtain absolute path if given path is relative to gelfile:
            gelfile = self.get_gelfilepath()
            filepath = getabsfilepath(gelfile, filepath)
        with open(filepath) as fd:
            #text = yaml.load(fd)
            text = fd.read()
        self.set_yaml(text)

    def save_yaml(self, event=None):     # pylint: disable=W0613
        """ Save content of yaml text widget to yaml file. """
        gelfile = self.get_gelfilepath()
        yamlfile_relative = self.get_yamlfilepath()
        fn = getabsfilepath(gelfile, yamlfile_relative)
        text = self.get_yaml()
        if not fn:
            raise ValueError("Yaml file entry is empty.")
        with open(fn, 'wb') as fd:
            # No! Dont dump, just save.
            #yaml.dump(text, fd, default_flow_style=False)
            fd.write(text)

    def get_annotationsfilepath(self, ):
        """ Returns content of annotations-filepath entry widget. """
        return self.Root.Annotationsfilepath.get()

    def set_annotationsfilepath(self, value):
        """ Sets content of annotations-filepath entry widget. """
        self.Root.Annotationsfilepath.set(value)

    def get_annotations(self):
        """ Returns content of annotations text widget. """
        return self.Root.get_annotations()

    def set_annotations(self, value):
        """ Sets content of annotations text widget. """
        self.Root.set_annotations(value)

    def load_annotations(self, filepath=None, filepath_is_relative_to_gelfile=True):
        """
        Loads the content of <filepath> into annotations text widget.
        filepath defaults to annotations-filepath widget entry.
        """
        logger.debug("Provided filepath: %s", filepath)
        if filepath is None:
            filepath = self.get_annotationsfilepath() # get_yamlfilepath returns relative to gelfile.
            logger.debug("Getting filepath from textentry: %s", filepath)
        if filepath_is_relative_to_gelfile:
            # Obtain absolute path if given path is relative to gelfile:
            gelfile = self.get_gelfilepath()
            logger.debug("gelfile is: %s", gelfile)
            filepath = getabsfilepath(gelfile, filepath)
            logger.debug("Converted relative filepath to absolute using gelfile: %s", filepath)
        with open(filepath) as fd:
            text = fd.read()
        self.set_annotations(text)

    def save_annotations(self, event=None):     # pylint: disable=W0613
        """ Saves the content of annotations text widget to annotations-filepath. """
        gelfile = self.get_gelfilepath()
        filepath_relative = self.get_annotationsfilepath()
        fn = getabsfilepath(gelfile, filepath_relative)
        #fn = self.get_annotationsfilepath()
        text = self.get_annotations()
        if not fn:
            raise ValueError("Annotations file entry is empty.")
        with open(fn, 'wb') as fd:
            fd.write(text)

    def browse_for_gelfile(self):
        """ Browse for gel image file. """
        # This call should probably be moved to tkroot...:
        filename = askopenfilename(filetypes=(("GEL files", "*.gel"),
                                              ("Image files", "*.png;*.jpg"),
                                              ("All supported", "*.gel;*.png;*.jpg"),
                                              ("All files", "*.*")
                                              ),
                                   initialdir=self.getgeldir(),
                                   parent=self.Root,
                                   title="Please select annotations file"
                                   )
        #print("Setting gelfile to:", filename)
        # Issue: after returning, the main UI does not take focus until the user has switched windows. (Win)
        # This may be an issue if the main loop has not been started? http://bytes.com/topic/python/answers/30934-tkinter-focus-text-selection-problem-tkfiledialog
        #gelfilepath = os.path.realpath(gelfilepath)
        #self.set_gelfilepath(gelfilepath)
        self.set_gelfilepath(filename)
        self.reset_aux_files(filename)

    def browse_for_yamlfile(self):
        """
        Browse for yaml file.
        Note that yamlfile, annotationsfile, etc are given relative to the gelfile.
        """
        filename = askopenfilename(filetypes=(("YAML files", "*.yaml;*.yml"),
                                              ("All files", "*.*")
                                              ),
                                   initialdir=self.getgeldir(),
                                   parent=self.Root,
                                   title="Please select yaml settings file"
                                   )
        logger.debug("User selected yamlfile: %s", filename)
        if not filename:
            logger.debug("User did not select a yamlfile (is '%s'), aborting...", filename)
            return
        gelfile = self.get_gelfilepath()
        filename = getrelfilepath(gelfile, filename)
        logger.debug("Setting yamlfile to: %s", filename)
        logger.debug("os.getcwd(): %s", os.getcwd())
        self.set_yamlfilepath(filename)
        self.load_yaml()

    def browse_for_annotationsfile(self):
        """
        Browse for annotations file.
        Note that yamlfile, annotationsfile, etc are given relative to the gelfile.
        """
        filename = askopenfilename(filetypes=(("Text files", "*.txt"),
                                              ("YAML files", "*.yaml;*.yml"),
                                              ("All files", "*.*")
                                              ),
                                   initialdir=self.getgeldir(),
                                   parent=self.Root,
                                   title="Please select annotations file"
                                   )
        logger.debug("User selected annotationsfile: %s", filename)
        if not filename:
            logger.debug("User did not select an annotationsfile (is '%s'), aborting...", filename)
            return
        gelfile = self.get_gelfilepath()
        filename = getrelfilepath(gelfile, filename)
        logger.debug("Setting annotationsfile to: %s", filename)
        logger.debug("os.getcwd(): %s", os.getcwd())
        self.set_annotationsfilepath(filename)
        self.load_annotations() # If you provide filename, it currently should be absolute?



    def mainloop(self):
        """ Starts this App's tk root mainloop. """
        logger.info("Starting tkroot mainloop()...")
        self.Root.mainloop()
        logger.info("<< Tkroot mainloop() complete - (and App start() ) <<")

    def show_help(self, event=None):     # event not used, method could be function pylint: disable=W0613,R0201
        """
        Show some help to the user.
        """
        helpfile = os.path.join(os.path.abspath(os.path.dirname(
            os.path.realpath(__file__))), '..', 'doc', 'GelAnnotator_GUI_help.txt')
        logger.debug("Showing help file: %s", helpfile)
        webbrowser.open(helpfile)

    def update_status(self, newstatus):
        if len(newstatus) > 110:
            newstatus = "..."+newstatus[-115:]
        self.Root.Statustext.set(newstatus)

    def annotate(self, event=None):     # event not used, pylint: disable=W0613
        """
        Performs annotations (typically upon button press).
        """
        # Load/save? Uhm, no, just save
        # and then invoke gelannotator with args.
        # Update yaml when done.
        #args = self.Args # This isn't needed; use
        gelfile = self.get_gelfilepath()
        yamlfile = self.get_yamlfilepath()
        annotationsfile = self.get_annotationsfilepath()
        # yaml and annotationsfile are relative to gelfile.
        self.save_yaml()
        self.save_annotations()
        logger.debug("Annotating gel '%s', using annotationsfile '%s' and yamlfile '%s'",
                     gelfile, annotationsfile, yamlfile)
        self.update_status("Converting and annotating gel...")
        try:
            dwg, svgfilename, args = annotate_gel(gelfile, yamlfile=yamlfile, annotationsfile=annotationsfile)  # pylint: disable=W0612
        except Exception as e:
            logger.info("Error annotate_gel:", e)
            self.update_status("Error: %s" % e)
            return
        else:
            self.update_status("SVG file generated: " + ("...." + svgfilename[-75:] if len(svgfilename) > 80 else svgfilename))
        # updated args are returned.
        if args.get('updateyaml', True):
            # Not sure if this should be done here or in gelannotator:
            logger.debug("Re-loading yaml file")
            self.load_yaml()
        logger.debug("Gel annotation complete!")
        # I wouldn't expect the annotations file to have changed.
        # prevent Tkinter from propagating the event by returning the string "break"
        return "break"



def main(args=None):
    """
    Having a dedicated main() makes it easier to run the GUI interactively
    from a python prompt.
    """
    if args is None:
        argsns = parseargs()
        args = argsns.__dict__
    app = GelAnnotatorApp(args=args)
    app.mainloop()

def get_workdir(args):
    """
    Try to find a working directory in args.
    If none of the path arguments are absolute, return current working directory.
    """
    try:
        next(os.path.dirname(path) for path in (args[k] for k in ('gelfile', 'yamlfile', 'annotationsfile') if k in args)
             if path and os.path.isabs(path))
    except StopIteration:
        logger.debug("No absolute directory found, using cwd.")
        return os.getcwd()

def set_workdir(args):
    """ Change working directory to match args, where args is gelfile or args dict. """
    if isinstance(args, basestring):
        d = os.path.dirname(args)
    else:
        d = get_workdir(args)
    logger.info("Chainging dir: %s", d)
    os.chdir(d)



if __name__ == '__main__':

    # test:
    testing = False
    if testing:
        ap = make_parser()
        argns = ap.parse_args('RS323_Agarose_ScaffoldPrep_550V.gel'.split())
    else:
        argns = parseargs('gui')
    cmdlineargs = argns.__dict__
    # set_workdir(args) Not needed, done by app during set_gelfilepath
    # If you need to have debug log output for arg parsing, put this above parseargs:
    logger.setLevel(logging.DEBUG)      # Set special, log loglevel for this main module
    print("before init_logging...")
    # Initializing logging doesn't cause immediate halt, nor does logging a debug msg.
    # Yet, if I do init_logging, my exe will hang.
    # Manual logging rather than basicConfig - issue persists...
    logging_disabled = cmdlineargs.pop('disable_logging', False)
    if not logging_disabled:
        init_logging(cmdlineargs)
    print("after init_logging...")
    logger.debug("hejsa")
    print("after first debug log msg...")
    main(cmdlineargs)
