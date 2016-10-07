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
import locale
import yaml
import webbrowser
from datetime import datetime
from six import string_types
import logging

# Local imports:
# Note: doing local imports means you cannot execute ```python gelannotator_gui.py``` directly any more,
# you have to either invoke it from a bootstrap script, or do ```python -m gelutils.gelannotator_gui```.
from .gelannotator import annotate_gel, find_yamlfilepath, find_annotationsfilepath
from .argutils import parseargs, make_parser
from .utils import init_logging, getrelfilepath, getabsfilepath, printdict, mergedicts
from .tkui.gelannotator_tkroot import GelAnnotatorTkRoot
from .config import DEFAULT_CONFIG_FILEPATHS, gel_exts, img_exts, cfg_exts
from .config import filename_is_yaml

# flush keyword only supported for python 3.3+, so create custom print function:
# Edit: Instead of modifying print to accept flush keyword, just make sure to use line-buffering for file objects
try:
    from tkFileDialog import askopenfilename
except ImportError:
    # python 3:
    from tkinter.filedialog import askopenfilename      # pylint: disable=F0401
logging.addLevelName(4, 'SPAM')  # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

# Configure global GelAnnotator app defaults:
CONFIG_APP_DEFAULTS = {
    "saveyamlto": "{yamlfile_fnroot}.final{config_ext}",  # Always make a backup with the final parameters used
    "stdout_mode": "w",
    "stderr_mode": "w",
}


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
    * cropgui : tkinter python crop gui application,
                http://emergent.unpythonic.net/01235516977, https://github.com/jepler/cropgui/
    * photo_splitter : Splits a photo into several smaller pieces, very nice python tkinter gui app,
                https://github.com/dnouri/photo_splitter
    * cropy   : No GUI, but tries to guess the optimal cropping parameters/content provided a given size,
                https://github.com/mapado/cropy
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
    * scipy functions: fftpack  # http://docs.scipy.org/docs/scipy-0.14.0/reference/tutorial/fftpack.html


    rotation: adjusted using the bottom of the wells. These can usually be identified from the sharp vertical peak.
    * Only use the top 10% of the gel.
    * For each column of pixels, determine if there is one that stands out.
      Use the derivative and find the first significant peak.
    * Filter for badly identified pixels (where the position "jumps").
    * "Plot" the pixels that stands out vs the column and make a linear fit. [Figuratively]
    * Use the slope of the linear fit to determine rotation.
    """
    def __init__(self, config, primary_file=None):           # pylint: disable=W0621
        # TODO: Rename "args" to "config".
        self.Args = config                # only saved to make init easier.
        self._primary_file = None
        logger.debug("GelAnnotatorApp initializing with args=%s", printdict(config))
        self.Root = tkroot = GelAnnotatorTkRoot(self, title="Gel Annotator GUI")
        # self.AnnotationsText, self.YamlText
        self.Root.bind_all("<Control-Return>", self.annotate)
        self.Root.AnnotationsText.bind("<Control-Return>", self.annotate)
        self.Root.YamlText.bind("<Control-Return>", self.annotate)
        self.helpfile = os.path.join(os.path.abspath(os.path.dirname(
            os.path.realpath(__file__))), '..', 'docs', 'GelAnnotator_GUI_help.md')

        # We generally do not want gelfile to be in args after this point:
        if primary_file is None:
            primary_file = config.pop('file')

        # Should the app use the yaml file as the root/base, or the gel file?
        # (1) We may want to re-use the same yaml file for multiple gel files.
        # (2) But we may also want to use different yaml files for the same gel file, e.g. if the gel file
        #     includes several actual gels.
        # Resolve:
        #   IF the yaml file includes a gelfilepath entry, then the app is oriented around the yaml file.
        #   Otherwise, the app is oriented around the gel file (current behaviour).

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

        # TODO: Improve how GEL-VS-CONFIG primary file mode is defined and used throughout the app's lifetime
        if primary_file:
            # self.reset_aux_files()
            self.set_primary_file(primary_file)
        else:  # if not self.get_gelfilepath():
            tkroot.after_idle(self.browse_for_primary_file)

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
        annotationsfilepath = args.get('annotationsfile', '')

        logger.info("Resetting UI using primary file: %s", self._primary_file)
        if not self._primary_file:
            print("Error: Primary file not set, cannot continue.")
            logger.error("Error: Primary file not set, cannot continue.")
            return
        basedir = os.path.dirname(os.path.abspath(self._primary_file))
        self.set_directory(basedir)
        # The simplest thing is to just change the working directory.
        # That, however, means that all files must be in the same directory...
        basenames = [self._primary_file]

        # At this point: yaml file may not have been loaded;
        # is only loaded if given with --yamlfile, not if given as primary file.
        # Perhaps move the logic below to main() outside the GUI class?

        if self.primary_file_is_yaml():
            args['_primary_file_mode'] = "yaml"
            yamlfilepath = os.path.relpath(self._primary_file, start=basedir)
            logger.debug("Primary file is a yaml configuration: %s", yamlfilepath)
            self.set_yamlfilepath(yamlfilepath)
            logger.debug("args keys: %s", args.keys())
            logger.debug("args.get('gelfile'): %s", args.get('gelfile'))
            gelfilepath = args.get('gelfile', '')
            if gelfilepath:
                logger.debug("Using gelfile from args/config: %s", gelfilepath)
                # basenames is a list of filenames used when searching for annotationsfile.
                basenames.append(os.path.join(basedir, gelfilepath))  # needs to be absolute.
            elif args.get('gelfile_last_used'):
                gelfilepath = args.get('gelfile_last_used')
                basenames.append(os.path.join(basedir, gelfilepath))  # needs to be absolute.
            else:
                # Search for gelfile matching the primary file name:
                fnroot, fnext = os.path.splitext(self._primary_file)
                logger.debug("No gelfile specified in config, searching for files starting with %s and ending with %s",
                             fnroot, gel_exts)
                for gelext in gel_exts:
                    if os.path.isfile(fnroot+gelext):
                        # Make gelfilepath relative, not absolute.
                        basenames.append(fnroot+gelext)
                        gelfilepath = os.path.relpath(fnroot+gelext, start=basedir)
                        logger.debug("Gelfile found matching filename of primary file: %s", gelfilepath)
                        break
                else:
                    logger.debug("No gelfile found matching yamlfile, gelfilepath is: '%s'", gelfilepath)
            self.set_gelfilepath(gelfilepath)
            args['gelfile'] = gelfilepath
            self.init_yaml(args)
        else:
            # _primary_file is GEL or None:
            gelfilepath = os.path.relpath(self._primary_file, start=basedir)
            self.set_gelfilepath(gelfilepath)
            logger.debug("Primary file is a GEL file: %s", gelfilepath)
            yamlfilepath = args.pop('yamlfile', '')
            # Desired location for yaml file, either input or based on gel file:
            if not yamlfilepath:
                yamlfilepath = find_yamlfilepath(self._primary_file)
                yamlfilepath = os.path.relpath(yamlfilepath, start=basedir)  # getrelfilepath is just that.
            logger.debug("Using yamlfilepath: %s", yamlfilepath)
            self.set_yamlfilepath(yamlfilepath)
            self.init_yaml(args)

        # Desired location for annotations file, either input or based on gel file:
        if not annotationsfilepath:
            annotationsfilepath = os.path.relpath(find_annotationsfilepath(basenames), start=basedir)
        logger.debug("Using annotationsfilepath: %s", annotationsfilepath)
        self.set_annotationsfilepath(annotationsfilepath)
        try:
            self.load_annotations()
        except (IOError, OSError) as e:
            logger.debug("%s -- No problem, will save to default when annotating.", e)

    def get_gelfilepath(self):
        """Returns content of gel-filepath entry widget."""
        filename = self.Root.Gelfilepath.get()
        if not filename:
            config = self.parse_config_from_yaml_widget()
            if 'gelfile' in config:
                return config['gelfile']
        return filename

    def set_gelfilepath(self, filepath):
        """Sets content of gel-filepath entry widget."""
        logger.debug("Setting gelfilepath to %s", filepath)
        self.Root.Gelfilepath.set(filepath)
        # Update self.Args and yaml text widget when setting gelfile when primary_file_is_yaml?
        # Edit: Right now set_gelfilepath is intended to just set the widget text and not have side-effects,
        # so better not do that.

    def get_directory(self):
        """Return the current directory."""
        return self.Root.Gelfiledirectory.get() or os.getcwd()

    def set_directory(self, directory):
        """Set the current directory."""
        logger.debug("Setting base directory to %s", directory)
        os.chdir(directory)
        self.Root.Gelfiledirectory.set(directory)

    def getgeldir(self):
        """Returns directory of gel-filepath entry widget, if not empty else user home dir."""
        gelfilepath = self.get_gelfilepath()
        if gelfilepath:
            return os.path.dirname(gelfilepath)
        elif self.get_directory():
            return self.get_directory()
        else:
            return os.path.expanduser('~')

    def get_yamlfilepath(self):
        """Returns content of yaml-filepath entry widget."""
        return self.Root.Yamlfilepath.get()

    def set_yamlfilepath(self, filepath):
        """Sets content of yaml-filepath entry widget."""
        logger.debug("Setting yaml filepath to %s", filepath)
        self.Root.Yamlfilepath.set(filepath)

    def get_yaml(self):
        """Returns content of yaml text widget."""
        return self.Root.get_yaml()

    def set_yaml(self, value):
        """Set content of yaml text widget."""
        # print("Setting content of yaml widget to:", value)
        self.Root.set_yaml(value)

    def init_yaml(self, args, filepath=None):       # pylint: disable=W0621
        """Merge args with yaml file (args take precedence)."""
        # TODO: Rename to
        if filepath is None:
            filepath = getabsfilepath(self.get_gelfilepath(), self.get_yamlfilepath())
            logger.debug("init yaml filepath wasn't given, extracting from yaml widget value")
        logger.debug("Initializing yaml text widget using args and yaml filepath %s", filepath)
        # if args is None:
        #     args = self.Args
        # default_config_file = args.pop('default_config', None)
        # default_config = yaml_get(default_config_file, {}) if default_config_file else {}
        # yamlconfig = yaml_get(fn, default_config)
        try:
            with open(filepath, encoding="utf-8") as fd:
                yamlconfig = yaml.safe_load(fd)  # returns None if file/string is empty
                logger.debug("loading yaml file: %s", filepath)
        except IOError:
            logger.debug("Could not find/load yaml file %s", filepath)
        else:
            logger.debug("yamlconfig loaded from %s: %s", filepath, yamlconfig)
            if yamlconfig:  # If loading empty file, the result may be None.
                args.update(mergedicts(yamlconfig, args))  # get merged dict, then update in-place.
        logger.debug("args: %s", printdict(args))
        self.set_yaml(yaml.dump(args, default_flow_style=False))

    def load_yaml(self, filepath=None, filepath_is_relative_to_gelfile=True):
        """Load content of yaml file into yaml text widget.

        If filepath is provided, should it be relative to gelfile?
        """
        logger.debug("Loading yaml from user-selected filepath: %s", filepath)
        if filepath is None:
            filepath = self.get_yamlfilepath()  # get_yamlfilepath returns relative to gelfile.
        if filepath_is_relative_to_gelfile:
            # Obtain absolute path if given path is relative to gelfile:
            gelfile = self.get_gelfilepath()
            filepath = getabsfilepath(gelfile, filepath)
        with open(filepath, encoding="utf-8") as fd:
            text = fd.read()
        self.set_yaml(text)

    def save_yaml(self, event=None):     # pylint: disable=W0613
        """Save content of yaml text widget to yaml file. """
        # TODO: Consider adding gelfile and annotationfile to the yaml config before saving file.
        gelfile = self.get_gelfilepath()
        yamlfile_relative = self.get_yamlfilepath()
        fn = getabsfilepath(gelfile, yamlfile_relative)
        text = self.get_yaml()
        logger.debug("Saving content of yaml text widget (%s chars) to file given by yaml filepath %s (event=%s)",
                     len(text), fn, event)
        if not fn:
            raise ValueError("Yaml file entry is empty.")

        with open(fn, 'w', encoding="utf-8") as fd:  # if using 'wb' then input must be buffered (which 'str' is not)
            # No need to dump as yaml, just save.
            logger.debug("file descriptor, fd: %s", fd)
            logger.debug("text: %s, %s chars", type(text), len(text))
            logger.debug("open function: %s", open)
            fd.write(text)

    def get_annotationsfilepath(self):
        """Returns content of annotations-filepath entry widget. """
        filename = self.Root.Annotationsfilepath.get()
        if not filename:
            config = self.parse_config_from_yaml_widget()
            if 'annotationsfile' in config:
                return config['annotationsfile']
        return filename

    def set_annotationsfilepath(self, filepath):
        """Sets content of annotations-filepath entry widget. """
        logger.debug("Setting annotations filepath to %s", filepath)
        self.Root.Annotationsfilepath.set(filepath)

    def get_annotations(self):
        """Return content of annotations text widget. """
        return self.Root.get_annotations()

    def set_annotations(self, value):
        """Set content of annotations text widget. """
        self.Root.set_annotations(value)

    def load_annotations(self, filepath=None, filepath_is_relative_to_gelfile=True):
        """Load the content of <filepath> into annotations text widget.

        filepath defaults to annotations-filepath widget entry.
        """
        if filepath is None:
            filepath = self.get_annotationsfilepath()  # get_yamlfilepath returns relative to gelfile.
            logger.debug("Getting annotationsfilepath from textentry: %s", filepath)
        logger.debug("Loading annotations from user-selected filepath: %s", filepath)
        if filepath_is_relative_to_gelfile:
            # Obtain absolute path if given path is relative to gelfile:
            gelfile = self.get_gelfilepath()
            logger.debug("gelfile is: %s", gelfile)
            filepath = getabsfilepath(gelfile, filepath)
            logger.debug("Converted relative filepath to absolute using gelfile: %s", filepath)
        with open(filepath, encoding="utf-8") as fd:
            text = fd.read()
        self.set_annotations(text)

    def save_annotations(self, event=None):     # pylint: disable=W0613
        """Saves the content of annotations text widget to annotations-filepath."""
        gelfile = self.get_gelfilepath()
        filepath_relative = self.get_annotationsfilepath()
        fn = getabsfilepath(gelfile, filepath_relative)
        text = self.get_annotations()
        logger.debug("Saving content of annotations text widget (%s chars) to file given by annotations filepath '%s'"
                     " (event=%s)", len(text), fn, event)
        if not fn:
            raise ValueError("Annotations file entry is empty.")
        with open(fn, 'w', encoding="utf-8") as fd:  # only use 'b' for byte/buffered input; 'str' is not byte/buffered.
            logger.debug("Saving annotations (%s chars) to file %s", len(text), fd)
            fd.write(text)

    def parse_config_from_yaml_widget(self):
        """Return parsed config dict of the yaml-formatted text of config widget."""
        return yaml.safe_load(self.get_yaml())

    def dump_config_to_yaml_widget(self, config):
        """Set yaml-formatted text of config widget using config dict."""
        self.set_yaml(yaml.dump(config, default_flow_style=False))

    def update_entry_in_yaml(self, key, value):
        """Update a single keyword value in the yaml config text widget."""
        config = self.parse_config_from_yaml_widget()
        config[key] = value
        self.dump_config_to_yaml_widget(config)

    def update_gelfile(self, gelfilename):
        """Update gelfile keyword value in the yaml text widget."""
        self.update_entry_in_yaml('gelfile', gelfilename)

    def browse_for_primary_file(self):
        """Invoked only if app is started without any FILE argument.
        This will set _primary_file_mode.
        """
        logger.debug("Browsing for GEL file using askopenfilename dialog...")
        filename = askopenfilename(
            filetypes=(
                ("GEL files", gel_exts),
                ("Image files", img_exts),
                ("Config files", cfg_exts),
                ("All supported", gel_exts+img_exts+cfg_exts),
                ("All files", "*.*")),
            initialdir=self.get_directory(),  # self.getgeldir(),
            parent=self.Root,
            title="Please select a file to use (gel image or config file)"
        )
        # TODO: This isn't properly implemented yet:
        self.set_primary_file(filename)

    def browse_for_gelfile(self):
        """Browse for gel image file.

        Open a GUI dialog and allow the user to select the gel file.
        """
        # This call should probably be moved to tkroot...:
        logger.debug("Browsing for GEL file using askopenfilename dialog...")
        filename = askopenfilename(filetypes=(("GEL files", gel_exts),
                                              ("Image files", img_exts),
                                              ("YAML config", cfg_exts),
                                              ("All supported", gel_exts+img_exts+cfg_exts),
                                              ("All files", "*.*")
                                              ),
                                   initialdir=self.get_directory(),  # self.getgeldir(),
                                   parent=self.Root,
                                   title="Please select GEL image file"
                                   )
        # print("Setting gelfile to:", filename)
        #  Issue: after returning, the main UI does not take focus until the user has switched windows. (Win)
        #  This may be an issue if the main loop has not been started?
        #  http://bytes.com/topic/python/answers/30934-tkinter-focus-text-selection-problem-tkfiledialog
        # gelfilepath = os.path.realpath(gelfilepath)
        # self.set_gelfilepath(gelfilepath)
        logger.info("User selected gel file: %s", filename)
        print("Gel file selected:", filename)
        if filename:
            logger.debug("Setting gelfile to: %s", filename)
            logger.debug("os.getcwd(): %s", os.getcwd())
            if self.primary_file_is_yaml():
                # Only set gelfile (text widget). Do not reset yaml or annotations file:
                filename = os.path.relpath(filename, self.get_directory())
                self.set_gelfilepath(filename)
                self.update_gelfile(filename)
                # self.Args['gelfile'] = filename  # Not optimal: User may have edited yaml panel.
            else:
                # Set selected gelfile as primary file and reset yaml+annotations files:
                self.set_primary_file(filename)
                self.reset_aux_files()

    def browse_for_yamlfile(self):
        """Browse for yaml file.

        Note that yamlfile, annotationsfile, etc are given relative to the gelfile.
        """
        logger.debug("Browsing for YAML file using askopenfilename dialog...")
        filename = askopenfilename(filetypes=[("YAML files", cfg_exts), ("All files", ".*")],
                                   initialdir=self.get_directory(),  # self.getgeldir(),
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
        """Browse for annotations file.

        Note that yamlfile, annotationsfile, etc are given relative to the gelfile.
        """
        logger.debug("Browsing for ANNOTATIONS file using askopenfilename dialog...")
        filename = askopenfilename(filetypes=(("Text files", ".txt"),
                                              ("YAML files", cfg_exts),
                                              ("All files", "*.*")
                                              ),
                                   initialdir=self.get_directory(),  # self.getgeldir(),
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
        self.load_annotations()  # If you provide filename, it currently should be absolute?

    def mainloop(self):
        """Start this App's tk root mainloop."""
        logger.info("Starting tkroot mainloop()...")
        self.Root.mainloop()
        logger.info("<< Tkroot mainloop() complete, GelAnnotator app started OK. <<")

    def show_help(self, event=None):
        """Show some help to the user.

        # event not used, method could be function pylint: disable=W0613,R0201
        # but, it is easier to bind buttons if we can pass App instance when initializing GelAnnotatorTkRoot
        """
        logger.debug("Showing help file: %s (event=%s)", self.helpfile, event)
        # OS X needs "file://" to open files with webbrowser module:
        webbrowser.open("file://" + self.helpfile)

    def update_status(self, newstatus):
        if len(newstatus) > 110:
            newstatus = "..."+newstatus[-115:]
        self.Root.Statustext.set(newstatus)

    def annotate(self, event=None):  # event not used, pylint: disable=W0613
        """Perform annotations (typically upon button press)."""
        # Load/save? Uhm, no, just save
        # and then invoke gelannotator with args.
        # Update yaml when done.
        # args = self.Args # This isn't needed; use
        gelfile = self.get_gelfilepath()
        yamlfile = self.get_yamlfilepath()
        annotationsfile = self.get_annotationsfilepath()
        # yaml and annotationsfile are relative to base directory, or self._primary_file.
        self.save_yaml()         # Saves content of yaml config text widget to file
        self.save_annotations()  # Saves content of annotations text widget to file
        logger.debug("Annotating gel '%s', using annotationsfile '%s' and yamlfile '%s' (event=%s)",
                     gelfile, annotationsfile, yamlfile, event)
        self.update_status("Converting and annotating gel...")
        # TODO: Instead of passing yamlfile to annotate_gel, load config from yaml text widget here
        # TODO: and pass config/"args" to annotate_gel.
        # TODO: This will allow you to inject updated 'gelfile' value from the gelfile text widget.
        try:
            dwg, svgfilename, args = annotate_gel(gelfile, yamlfile=yamlfile, annotationsfile=annotationsfile)
        except Exception as e:
            logger.info("Error annotate_gel: %s", e)
            self.update_status("ERROR: %s" % e)
            raise
        else:
            self.update_status("SVG file generated: " +
                               (svgfilename if len(svgfilename) < 80 else "...." + svgfilename[-75:]))

        # updated args/config is returned (with e.g. result of auto-calculated dynamic range)
        # TODO: Rename 'updateyaml' to 'updateyamlfile' and make new 'updateyamlwidget' keyword.
        if args.get('updateyaml', True):
            # Not sure if this should be done here or in gelannotator:
            # logger.debug("Re-loading yaml file")
            # self.load_yaml()    # Loads content of yaml file (given by yaml-filename widget) into config text widget.
            logger.debug("Updating yaml config widget to display final config parameters...")
            self.dump_config_to_yaml_widget(args)
        logger.info("Gel annotation complete!")
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
    """Get working directory based on values in args.

    Try to find a working directory in args.
    If none of the path arguments are absolute, return current working directory.
    """
    try:
        next(os.path.dirname(path)
             for path in (args[k] for k in ('gelfile', 'yamlfile', 'annotationsfile') if k in args)
             if path and os.path.isabs(path))
    except StopIteration:
        logger.debug("No absolute directory found, using cwd.")
        return os.getcwd()


def set_workdir(args):
    """Change working directory to match args, where args is gelfile or args dict. """
    if isinstance(args, string_types):
        d = os.path.dirname(args)
    else:
        d = get_workdir(args)
    logger.info("Chainging dir: %s", d)
    os.chdir(d)


def get_default_config(fncands=None):
    """Find default user config.

    Locate and load default user config from file.
    The "system default" config is created by the argument parser).

    Arguments:
        fncands: Sequence of potential filenames to search for user config.

    Returns:
        2-Tuple with (filename, config), where:
            filename is the config file that was found first, and
            config is a dict with user config or None if no default config files were found.
    """
    # Load default user config
    if fncands is None:
        fncands = DEFAULT_CONFIG_FILEPATHS

    for fn in fncands:
        try:
            with open(os.path.expanduser(fn), encoding="utf-8") as fp:
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


def get_config(scheme=1, defaults=None):

    # In all schemes, defaults is our starting point:
    config = defaults or {}

    if scheme == 0:
        # old, from commit 2d0be77c
        # Cons: Default values different from None CANNOT be overridden by system_config or config template :O
        argsns = parseargs(prog='gui', defaults=config)
        config = argsns.__dict__

        # 2. Config template:
        config_template_fn = config.pop("config_template", None)
        if config_template_fn:
            print("Loading explicitly-specififed config_template from file: %s" % config_template_fn)
            try:
                template_config = yaml.load(open(config_template_fn, encoding="utf-8"))
            except FileNotFoundError as e:
                print("Error loading default config: %s" % e)
            else:
                config = mergedicts(template_config, config)  # latter takes precedence except None-valued entries

        # 3. Load system-level config, unless deactivated by command line arguments:
        if config.pop('load_system_config', True):  # incl if config is None
            print("Trying to load default config from file paths:", DEFAULT_CONFIG_FILEPATHS)
            system_config_fn, system_config = get_default_config()
            if system_config:
                print(" - Loaded system config/settings from file %s," % (system_config_fn, ),
                      "merging with main config.")
                config = mergedicts(system_config, config)  # latter takes precedence (except None-values)
            else:
                print(" - Could not find any default configuration file.")

    if scheme == 1:
        # 1+2: Extract --no-load-system-config and --config-template from sys.argv,
        # 3. parseargs using merged (CONFIG_APP_DEFAULTS, template_config, system_config) as defaults
        # 4. then load and merge yamlfile.
        # Priority is:
        # yamlfile, user-specified command line args, template_config, system_config, CONFIG_APP_DEFAULTS
        # 1. Load system_config (from standard locations):
        if "--no-load-system-config" not in sys.argv:
            print("Trying to load default config from file paths:", DEFAULT_CONFIG_FILEPATHS)
            system_config_fn, system_config = get_default_config()
            if system_config:
                print(" - Loaded system config/settings from file %s," % (system_config_fn, ),
                      "merging with main config.")
                config = mergedicts(config, system_config)  # latter takes precedence (except None-values)
            else:
                print(" - Could not find any default configuration file.")
        # 2. Load template_config (specified from command line):
        if "--template-config" in sys.argv:
            config_template_fn = sys.argv[sys.argv.index("--template-config")+1]
            try:
                template_config = yaml.load(open(config_template_fn, encoding="utf-8"))
            except FileNotFoundError as e:
                print("Error loading default config: %s" % e)
            else:
                config = mergedicts(template_config, config)  # latter takes precedence except None-valued entries

        # 3. parseargs using merged (CONFIG_APP_DEFAULTS, template_config, system_config) as defaults
        argsns = parseargs(prog='gui', defaults=config)
        config = argsns.__dict__

    elif scheme == 2:
        # Almost like 0, but determine user_specified_args and override defaults with system_config values
        # 1. config = parseargs(), then determine user_specified_args
        # 2+3. then load and merge system_config and config_template,
        # 4. then merge user_specified_args,
        # then load and merge yamlfile.
        # priority is:
        # yamlfile, user-specified command line args, template config, system_config, CONFIG_APP_DEFAULTS.
        argsns = parseargs(prog='gui', defaults=config)
        user_specified_args = {k: v for k, v in vars(argsns).items()
                               if v is not None and v != CONFIG_APP_DEFAULTS.get(k)}
        config = argsns.__dict__
        # 2. Load system-level config, unless deactivated by command line arguments:
        if config.pop('load_system_config', True):  # incl if config is None
            print("Trying to load default config from file paths:", DEFAULT_CONFIG_FILEPATHS)
            system_config_fn, system_config = get_default_config()
            if system_config:
                print(" - Loaded system config/settings from file %s," % (system_config_fn, ),
                      "merging with main config.")
                config = mergedicts(config, system_config)  # latter takes precedence (except None-values)
            else:
                print(" - Could not find any default configuration file.")
        # 3. Config template:
        config_template_fn = config.pop("config_template", None)
        if config_template_fn:
            print("Loading explicitly-specififed config_template from file: %s" % config_template_fn)
            try:
                template_config = yaml.load(open(config_template_fn, encoding="utf-8"))
            except FileNotFoundError as e:
                print("Error loading default config: %s" % e)
            else:
                config = mergedicts(config, template_config)  # latter takes precedence except None-valued entries
        # 4. merge user_specified_args to make sure they take precedence:
        if user_specified_args:
            config = mergedicts(config, user_specified_args)

    elif scheme == 3:
        # Conceptually simplest, just let system_config and config_template ALWAYS override command line flags.
        # Cons: You override system_config by specifying ad-hoc command line arguments for debugging.
        # 1. config = parseargs(), (without determing user_specified_args)
        # 2+3. then load and merge system_config and config_template,
        # 4. then load and merge yamlfile.
        # priority is (highest-to-lowest):
        # yamlfile, template config, system_config, command line args, CONFIG_APP_DEFAULTS.
        argsns = parseargs(prog='gui', defaults=config)
        config = argsns.__dict__
        # 2. Load system-level config, unless deactivated by command line arguments:
        if config.pop('load_system_config', True):  # incl if config is None
            print("Trying to load default config from file paths:", DEFAULT_CONFIG_FILEPATHS)
            system_config_fn, system_config = get_default_config()
            if system_config:
                print(" - Loaded system config/settings from file %s," % (system_config_fn, ),
                      "merging with main config.")
                config = mergedicts(config, system_config)  # latter takes precedence (except None-values)
            else:
                print(" - Could not find any default configuration file.")
        # 3. Config template:
        config_template_fn = config.pop("config_template", None)
        if config_template_fn:
            print("Loading explicitly-specififed config_template from file: %s" % config_template_fn)
            try:
                template_config = yaml.load(open(config_template_fn, encoding="utf-8"))
            except FileNotFoundError as e:
                print("Error loading default config: %s" % e)
            else:
                config = mergedicts(config, template_config)  # latter takes precedence except None-valued entries

    # 4. Load yamlfile (takes precedence over everything else)
    yamlfile = config.get("yamlfile")
    # TODO: This also needs to take precedense when yaml_is_primary.
    if yamlfile is None and config.get('file') and filename_is_yaml(config.get('file')):
        yamlfile = config.get('file')  # evt. pop() here?
    if yamlfile:
        # If config file  is explicitly specified, do not try to catch errors:
        with open(os.path.expanduser(yamlfile), encoding="utf-8") as fp:
            print("Using yaml-formatted configuration file:", yamlfile)
            yaml_config = yaml.load(fp)
            config = mergedicts(config, yaml_config)  # latter takes precedence except None-valued entries

    return config


def main(config=None):
    """main driver for launching GUI Application.

    Having a dedicated main() makes it easier to run the GUI interactively
    from a python prompt.

    Arguments:
        :args:  dict with arguments/configuration.

    Examples:
        >>> main()
    """

    print("\nApp main() started {:%Y-%m-%d %H:%M}".format(datetime.now()))
    print("- default encoding:", locale.getpreferredencoding(False))
    try:
        import matplotlib
        logger.info("matplotlib library is available, setting tkagg as backend.")
        matplotlib.use('tkagg')
    except ImportError:
        matplotlib = None
        logger.info("matplotlib library is NOT available, setting matplotlib=%s." % matplotlib)

    # Note: It might be a good idea to load the system-level default config (e.g. ~/.gelannotator.yaml)
    # BEFORE parsing args, and passing the default config to parseargs.

    # What is the priority of configs?
    # 1. yamlfile (loaded from disk)  (HIGHEST)
    # 2. command line args
    # 3. config template
    # 4. system config.
    # 5. CONFIG_APP_DEFAULTS          (LOWEST)

    # Note that for 2. command line args, it should preferably only entries that differs from CONFIG_APP_DEFAULTS.
    # Example: Right now, svgfnfmt defaults to "{pngfnroot}_annotated{ext}" in argparser. So values in the
    # system_config can never override this default value.
    # It would be nice to just use the merge of (CONFIG_APP_DEFAULTS, template_config, system_config) to
    # specify defaults for parseargs(), but I also want to be able to disable system-level config using
    # --no-load-system-config command line argument.
    # Alternative 1: Use ```if "no-load-system-config" in sys.argv``` to disable loading of system_config
    #       (and config_template) before parsing command line args and pass merged config as defaults to parseargs()
    # Alternative 2: Make a dict with user-specified args and use that to override system_config/etc:
    #       ```user_specified_args = {k: v for k, v in args if v is not None and v != CONFIG_APP_DEFAULTS.get(k)}```
    # Alternative 3: Just let system_config and config_template ALWAYS override command line flags.
    #        This is probably the simplest, but it would make it impossible to change the config from command line
    #        as-needed, e.g. for debugging.

    # However, this is not the order in which args are loaded, which is:
    # 1. CONFIG_APP_DEFAULTS and command line args (merged, cmd args taking precedence)
    # 2. config template (may be given by cmd args or system config)
    # 3. system config
    # 4. yamlfile (may be given by cmd args).

    # 1. Parse command line arguments, if config is not provided:
    if config is None:
        config = get_config(scheme=1, defaults=CONFIG_APP_DEFAULTS)

    print("Config after parsing cmd args, and loading system_config, yamlfile/config_template_fn:")
    print(config)

    # stdout and stderr redirection, if requested...
    # I wanted to have this at the top, but I also would like to load system config first.
    # But, maybe just repeat what you said above not, after you've redirected stdout?
    stdout_fn = config.pop('stdout', None)
    stdout_mode = config.pop('stdout_mode', 'w')
    stderr_fn = config.pop('stderr', None)
    stderr_mode = config.pop('stderr_mode', 'w')
    if stdout_fn is not None:
        # buffering=1 (text-mode line buffering), replacing bad characters with '?' if encoding fails.
        stdout_fd = open(stdout_fn, mode=stdout_mode, encoding='utf-8', errors='replace', buffering=1)
        print("Redirecting stdout to file:", stdout_fd)
        sys.stdout = stdout_fd  # backups are available as sys.__stdout__, sys.__stderr__
        print("stdout redirected to file:", stdout_fd)
        print("Note - date = {:%Y-%m-%d %H:%M}".format(datetime.now()))
        # print('Note - config files: system_config_fn="%s", config_template_fn="%s", yamlfile="%s"'
        #       % (system_config_fn, config_template_fn, yamlfile))
        print('Note - config: "%s"' % (config, ))
        if stderr_fn is None:
            print(" - Also redirecting stderr to same file as stdout (%s)" % (stdout_fd, ))
            sys.stderr = stdout_fd
    if stderr_fn is not None:
        # buffering=1 (text-mode line buffering), replacing bad characters with '?' if encoding fails.
        stderr_fd = open(stderr_fn, mode=stderr_mode, encoding='utf-8', errors='replace', buffering=1)
        print("Redirecting stderr to file:", stderr_fd)
        sys.stderr = stderr_fd

    if not config.pop('disable_logging', False):
        print("Initializing logging system using:",
              ", ".join("%s=%s" % (k, v) for k, v in config.items() if k.startswith("log")))
        logger.debug("Initializing logging system...")
        init_logging(config)
        logger.info("logging system started, locale.getpreferredencoding(False) = %s",
                    locale.getpreferredencoding(False))
    else:
        print("Logging disabled (disable_logging=True)...")

    print("\n\nApp config loaded, logging and stdout/stderr output configured, preferred encoding:",
          locale.getpreferredencoding(False))

    # For debugging:
    # logger.setLevel(logging.DEBUG)      # Set special loglevel for this main module
    # Global logging behaviour is adjusted by config['loglevel'] and config['logtofile']

    logger.debug("Creating GelAnnotatorApp with args/config=%s", config)
    preferredencoding = locale.getpreferredencoding(False)
    if "utf-8" not in preferredencoding.lower():
        # Avoid encoding errors by always using the same locale and encoding:
        # (alternatively always specify encoding keyword to open() files)
        print("Resetting locale to ('en_US', 'UTF-8') - was originally %s..." % (preferredencoding, ))
        try:
            locale.setlocale(locale.LC_ALL, ('en_US', 'UTF-8'))
        except Exception as e:
            print("Failed to set locale: %s" % e)
            logger.info("Failed to set locale: %s",  e)
        else:
            logger.info("Locale reset to %s; preferred encoding is now '%s'",
                        ('en_US', 'UTF-8'), locale.getpreferredencoding(False))
    app = GelAnnotatorApp(config=config)
    logger.debug("GelAnnotatorApp created, starting mainloop()...")
    app.mainloop()

    logger.debug("App mainloop() finished, exiting...\n\n\n\n")


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
