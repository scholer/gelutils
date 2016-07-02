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

from __future__ import print_function, absolute_import
import sys
import os
import yaml
import webbrowser
from six import string_types

try:
    from tkFileDialog import askopenfilename
except ImportError:
    # python 3:
    from tkinter.filedialog import askopenfilename      # pylint: disable=F0401

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

# Local imports:
# Note: doing local imports means you cannot execute ```python gelannotator_gui.py``` directly any more,
# you have to either invoke it from a bootstrap script, or do ```python -m gelutils.gelannotator_gui```.
from .gelannotator import annotate_gel, find_yamlfilepath, find_annotationsfilepath
from .argutils import parseargs, make_parser, mergedicts
from .utils import init_logging, getrelfilepath, getabsfilepath, printdict
from .tkui.gelannotator_tkroot import GelAnnotatorTkRoot
from .utils import open_utf  # unicode writer. # TODO: Is this only needed for python2?
open = open_utf     # overwrite built-in, yes that's the point: pylint: disable=W0622


gel_exts = (".gel", ".tiff", ".tif")
img_exts = (".png", ".jpg", ".tiff", ".tif") #"*.png;*.jpg"
cfg_exts = (".yaml", ".yml", ".gaml") #"*.gel;*.png;*.jpg"),

def filename_is_yaml(fn):
    base, ext = os.path.splitext(fn)
    return ext in cfg_exts

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
        # TODO: Rename "args" to "config".
        self.Args = args                # only saved to make init easier.
        logger.debug("GelAnnotatorApp initializing with args=%s", printdict(args))
        self.Root = tkroot = GelAnnotatorTkRoot(self, title="Gel Annotator GUI")
        # self.AnnotationsText, self.YamlText
        self.Root.bind_all("<Control-Return>", self.annotate)
        self.Root.AnnotationsText.bind("<Control-Return>", self.annotate)
        self.Root.YamlText.bind("<Control-Return>", self.annotate)

        ## We generally do not want gelfile to be in args after this point:
        self._primary_file = args.pop('file')

        ## Should the app use the yaml file as the root/base, or the gel file?
        ## (1) We may want to re-use the same yaml file for multiple gel files.
        ## (2) But we may also want to use different yaml files for the same gel file, e.g. if the gel file
        ##     includes several actual gels.
        ## Resolve:
        ##   IF the yaml file includes a gelfilepath entry, then the app is oriented around the yaml file.
        ##   Otherwise, the app is oriented around the gel file (current behaviour).

        # It may be nice to have a "primary" file. If the primary file ends with ".yaml" or ".gaml",
        # then obviously it is a yaml file, and we are in "yaml_mode"

        # if not self._primary_file:
        #     # Better to allow tkinter to fully initialize before making user prompts:
        #     self.Lastuseddir = os.path.expanduser('~')
        #     tkroot.after_idle(self.browse_for_gelfile)
        # else:
        #     #gelfilepath = os.path.realpath(gelfilepath) # no reason to do this?
        #     self.Lastuseddir = os.path.dirname(self._primary_file)
        #     self.reset_aux_files()

        if self._primary_file:
            self.reset_aux_files()
        if not self.get_gelfilepath():
            tkroot.after_idle(self.browse_for_gelfile)


    def set_primary_file(self, file):
        """ Set the primary file, either gel file or yaml/gaml file. """
        logger.info("Setting primary file to: %s", file)
        self._primary_file = file
        self.reset_aux_files()

    def primary_file_is_yaml(self):
        return filename_is_yaml(self._primary_file)

    def reset_aux_files(self):
        """
        Resets yaml and annotation files after changing the gelfile.
        Remember that all filepaths except gelfile should be given relative to gelfile.
        """
        args = self.Args    # pylint: disable=W0621
        annotationsfilepath = args.pop('annotationsfile', '')

        logger.info("Resetting UI using primary file: %s", self._primary_file)
        if not self._primary_file:
            print("Error: Primary file not set, cannot continue.")
            return
        basedir = os.path.dirname(os.path.abspath(self._primary_file))
        # The simplest thing is to just change the working directory.
        # That, however, means that all files must be in the same directory...

        if self.primary_file_is_yaml():
            args['_primary_file_mode'] = "yaml"
            yamlfilepath = os.path.relpath(self._primary_file, start=basedir)
            logger.debug("Primary file is a yaml configuration: %s", yamlfilepath)
            gelfilepath = args.pop('gelfile', '')
            if not gelfilepath:
                fnroot, fnext = os.path.splitext(self._primary_file)
                logger.debug("No gelfile specified in config, searching for files starting with %s and ending with %s",
                             fnroot, gel_exts)
                for gelext in gel_exts:
                    if os.path.isfile(fnroot+gelext):
                        # Make gelfilepath relative, not absolute.
                        gelfilepath = os.path.relpath(fnroot+gelext, start=basedir)
                        logger.debug("Gelfile found matching filename of primary file: %s", gelfilepath)
                        break
            else:
                logger.debug("Using gelfile from args: %s", gelfilepath)
        else:
            gelfilepath = os.path.relpath(self._primary_file, start=basedir)
            logger.debug("Primary file is a GEL file: %s", gelfilepath)
            yamlfilepath = args.pop('yamlfile', '')
            # Desired location for yaml file, either input or based on gel file:
            if not yamlfilepath:
                yamlfilepath = os.path.relpath(find_yamlfilepath(self._primary_file),
                                               start=basedir)  # getrelfilepath is just that.
            logger.debug("Using yamlfilepath: %s", yamlfilepath)
        # Desired location for annotations file, either input or based on gel file:
        if not annotationsfilepath:
            annotationsfilepath = os.path.relpath(find_annotationsfilepath(self._primary_file), start=basedir)
        logger.debug("Using annotationsfilepath: %s", annotationsfilepath)

        # Update GUI text widgets:
        self.set_directory(basedir)
        self.set_gelfilepath(gelfilepath)
        self.set_yamlfilepath(yamlfilepath)
        self.set_annotationsfilepath(annotationsfilepath)

        self.init_yaml(args)
        try:
            self.load_annotations()
        except (IOError, OSError) as e:
            logger.debug("%s -- No problem, will save to default when annotating.", e)


    def get_gelfilepath(self):
        """ Returns content of gel-filepath entry widget. """
        return self.Root.Gelfilepath.get()

    def set_gelfilepath(self, filepath):
        """ Sets content of gel-filepath entry widget. """
        logger.debug("Setting gelfilepath to %s", filepath)
        self.Root.Gelfilepath.set(filepath)

    def get_directory(self):
        return self.Root.Gelfiledirectory.get() or os.getcwd()

    def set_directory(self, directory):
        logger.debug("Setting base directory to %s", directory)
        os.chdir(directory)
        self.Root.Gelfiledirectory.set(directory)


    def getgeldir(self):
        """ Returns directory of gel-filepath entry widget, if not empty else user home dir. """
        gelfilepath = self.get_gelfilepath()
        if gelfilepath:
            return os.path.dirname(gelfilepath)
        elif self.get_directory():
            return self.get_directory()
        else:
            return os.path.expanduser('~')

    def get_yamlfilepath(self):
        """ Returns content of yaml-filepath entry widget. """
        return self.Root.Yamlfilepath.get()

    def set_yamlfilepath(self, filepath):
        """ Sets content of yaml-filepath entry widget. """
        logger.debug("Setting yaml filepath to %s", filepath)
        self.Root.Yamlfilepath.set(filepath)

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
        logger.debug("Initializing yaml text widget using args and yaml filepath %s", filepath)
        #if args is None:
        #    args = self.Args
        gelfile = self.get_gelfilepath()
        yamlfile_relative = self.get_yamlfilepath()
        fn = filepath or getabsfilepath(gelfile, yamlfile_relative)
        #default_config_file = args.pop('default_config', None)
        #default_config = yaml_get(default_config_file, {}) if default_config_file else {}
        #yamlconfig = yaml_get(fn, default_config)
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
        logger.debug("Loading yaml from user-selected filepath: %s", filepath)
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
        # TODO: Consider adding gelfile and annotationfile to the yaml config before saving file.
        gelfile = self.get_gelfilepath()
        yamlfile_relative = self.get_yamlfilepath()
        fn = getabsfilepath(gelfile, yamlfile_relative)
        text = self.get_yaml()
        logger.debug("Saving content of yaml text widget (%s chars) to file given by yaml filepath %s",
                     len(text), fn)
        if not fn:
            raise ValueError("Yaml file entry is empty.")
        with open(fn, 'wb') as fd:
            # No need to dump as yaml, just save.
            fd.write(text)

    def get_annotationsfilepath(self):
        """ Returns content of annotations-filepath entry widget. """
        return self.Root.Annotationsfilepath.get()

    def set_annotationsfilepath(self, filepath):
        """ Sets content of annotations-filepath entry widget. """
        logger.debug("Setting annotations filepath to %s", filepath)
        self.Root.Annotationsfilepath.set(filepath)

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
        if filepath is None:
            filepath = self.get_annotationsfilepath() # get_yamlfilepath returns relative to gelfile.
            logger.debug("Getting annotationsfilepath from textentry: %s", filepath)
        logger.debug("Loading annotations from user-selected filepath: %s", filepath)
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
        logger.debug("Saving content of annotations text widget (%s chars) to file given by annotations filepath %s",
                     len(text), fn)
        if not fn:
            raise ValueError("Annotations file entry is empty.")
        with open(fn, 'wb') as fd:
            fd.write(text)

    def browse_for_gelfile(self):
        """ Browse for gel image file. """
        # This call should probably be moved to tkroot...:
        logger.debug("Browsing for GEL file using askopenfilename dialog...")
        filename = askopenfilename(filetypes=(("GEL files", gel_exts),
                                              ("Image files", img_exts),
                                              ("YAML config", cfg_exts),
                                              ("All supported", gel_exts+img_exts+cfg_exts),
                                              ("All files", "*.*")
                                              ),
                                   initialdir=self.get_directory(), #self.getgeldir(),
                                   parent=self.Root,
                                   title="Please select annotations file"
                                   )
        #print("Setting gelfile to:", filename)
        # Issue: after returning, the main UI does not take focus until the user has switched windows. (Win)
        # This may be an issue if the main loop has not been started? http://bytes.com/topic/python/answers/30934-tkinter-focus-text-selection-problem-tkfiledialog
        #gelfilepath = os.path.realpath(gelfilepath)
        #self.set_gelfilepath(gelfilepath)
        logger.info("User selected gel file: %s", filename)
        print("Gel file selected:", filename)
        if filename:
            logger.debug("Setting gelfile to: %s", filename)
            logger.debug("os.getcwd(): %s", os.getcwd())
            self.set_primary_file(filename)
            self.reset_aux_files(filename)

    def browse_for_yamlfile(self):
        """
        Browse for yaml file.
        Note that yamlfile, annotationsfile, etc are given relative to the gelfile.
        """
        logger.debug("Browsing for YAML file using askopenfilename dialog...")
        filename = askopenfilename(filetypes=[("YAML files", cfg_exts), ("All files", ".*")],
                                   initialdir=self.get_directory(), # self.getgeldir(),
                                   parent=self.Root,
                                   title="Please select yaml settings file"
                                   )
        logger.debug("User selected yamlfile: %s", filename)
        if not filename:
            logger.debug("User did not select a yamlfile (is '%s'), aborting...", filename)
            return
        gelfile = self.get_gelfilepath()
        filename = getrelfilepath(gelfile, filename)
        print("Yaml file selected:", filename)
        logger.debug("Setting yamlfile to: %s", filename)
        logger.debug("os.getcwd(): %s", os.getcwd())
        self.set_yamlfilepath(filename)
        self.load_yaml()

    def browse_for_annotationsfile(self):
        """
        Browse for annotations file.
        Note that yamlfile, annotationsfile, etc are given relative to the gelfile.
        """
        logger.debug("Browsing for ANNOTATIONS file using askopenfilename dialog...")
        filename = askopenfilename(filetypes=(("Text files", ".txt"),
                                              ("YAML files", cfg_exts),
                                              ("All files", "*.*")
                                              ),
                                   initialdir=self.get_directory(), # self.getgeldir(),
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
        logger.info("<< Tkroot mainloop() complete, GelAnnotator app started OK. <<")

    def show_help(self, event=None):     # event not used, method could be function pylint: disable=W0613,R0201
        """
        Show some help to the user.
        """
        helpfile = os.path.join(os.path.abspath(os.path.dirname(
            os.path.realpath(__file__))), '..', 'doc', 'GelAnnotator_GUI_help.txt')
        logger.debug("Showing help file: %s", helpfile)
        # OS X needs "file://" to open files with webbrowser module:
        webbrowser.open("file://" + helpfile)

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
        # yaml and annotationsfile are relative to base directory, or self._primary_file.
        self.save_yaml()        # Saves content of yaml config text widget to file
        self.save_annotations() # Saves content of annotations text widget to file
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

        # updated args/config is returned (with e.g. auto dynamic range)
        if args.get('updateyaml', True):
            # Not sure if this should be done here or in gelannotator:
            logger.debug("Re-loading yaml file")
            self.load_yaml()    # Loads content of yaml file (given by yaml-filename widget) into config text widget.
        logger.debug("Gel annotation complete!")
        # I wouldn't expect the annotations file to have changed.
        # prevent Tkinter from propagating the event by returning the string "break"

        # check if we have switched from "yaml" to "gel" mode:
        if (args.get('_primary_file_mode') == "yaml") != self.primary_file_is_yaml():
            if args.get('_primary_file_mode') == "yaml":
                self.set_primary_file(self.get_yamlfilepath())
            if args.get('_primary_file_mode') == "gel":
                self.set_primary_file(self.get_gelfilepath())
        print("\nAnnotation and conversion complete!\n")
        return "break"



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
    if isinstance(args, string_types):
        d = os.path.dirname(args)
    else:
        d = get_workdir(args)
    logger.info("Chainging dir: %s", d)
    os.chdir(d)


def get_default_config(fncands=None):
    """
    Find default user config. (The "system default" config is created by the argument parser).
    Arguments:
        :fncands: Sequence of potential filenames to search for user config.
    :return: tuple with (filename, config)
    where
     filename is the config file that was found first, and
     config is a dict with user config or None if no default config files were found.
    """
    # Load default user config
    if fncands is None:
        fncands = ('gelannotator.yaml', '~/.gelannotator.yaml', '~/.config/gelannotator.yaml',
                   '~/.config/gelannotator/default_config.yaml', '~/.config/gelannotator/gelannotator.yaml')

    for fn in fncands:
        try:
            with open(os.path.expanduser(fn)) as fp:
                default_config = yaml.load(fp)
        except (IOError, FileNotFoundError):
            # Note: logging is not initialized, so won't print anything, this is for dev debug..
            logger.debug("Config cand not found (continuing search): %s", fn)
            continue
        except yaml.error.YAMLError:
            logger.info("YAMLError, could not parse file content (continuing search): %s", fn)
            print("WARNING: YAML could not parse the content of default config file %s." % fn)
            continue
        else:
            return fn, default_config
    return None, None


def main(config=None):
    """
    Having a dedicated main() makes it easier to run the GUI interactively
    from a python prompt.
    Arguments:
        :args:  dict with arguments/configuration.
    """
    # Note: It might be a good idea to load the system-level default config (e.g. ~/.gelannotator.yaml)
    # BEFORE parsing args, and passing the default config to parseargs.
    if config is None or config.get('load_system_config', True):
        fn, default_config = get_default_config()
        print("Loaded initial system config/settings from file: %s" % fn)
    else:
        default_config = None
    if config is None:
        argsns = parseargs(prog='gui', defaults=default_config)
        config = argsns.__dict__
        if default_config:
            config = mergedicts(default_config, config) # latter takes presidence except None-valued entries

    if config.get("yamlfile"):
        # If config file  is explicitly specified, do not try to catch errors:
        with open(os.path.expanduser(config["yamlfile"])) as fp:
            print("Using yaml-formatted configuration file:", config["yamlfile"])
            default_config = yaml.load(fp)
            config = mergedicts(default_config, config)
    elif config.get("config_template"):
        print("Loading explicitly-specififed config_template from file: %s" % config.get("default_config"))
        try:
            default_config = yaml.load(open(config.pop("config_template")))
        except FileNotFoundError as e:
            print("Error loading default config: %s" % e)
        else:
            config = mergedicts(default_config, config)


    if not config.pop('disable_logging', False):
        print("Initializing logging system using:",
              ", ".join("%s=%s" % (k, v) for k, v in config.items() if k.startswith("log")))
        init_logging(config)
        logger.debug("Logging system initialized...")
    else:
        print("Logging disabled (disable_logging=True)...")

    # For debugging:
    # logger.setLevel(logging.DEBUG)      # Set special loglevel for this main module
    # Global logging behaviour is adjusted by config['loglevel'] and config['logtofile']

    app = GelAnnotatorApp(args=config)
    app.mainloop()


def test():

    ap = make_parser()
    argns = ap.parse_args('RS323_Agarose_ScaffoldPrep_550V.gel'.split())
    main(argns.__dict__)



if __name__ == '__main__':

    # # test:
    # testing = False
    # if testing:
    #     sys.exit(test())

    main()
