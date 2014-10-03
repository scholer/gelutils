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

import Tkinter as tk
import ttk
try:
    from tkFileDialog import askopenfilename
except ImportError:
    # python 3:
    from tkinter.filedialog import askopenfilename
#import tkMessageBox
#import ttk

import os
import yaml
import webbrowser

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

from gelannotator import annotate_gel, find_yamlfilepath, find_annotationsfilepath
from argutils import parseargs, make_parser, mergedicts
from utils import init_logging


class GelAnnotatorTkRoot(tk.Tk):
    """
    The actual UI.
    """
    def __init__(self, app, title=None):
        tk.Tk.__init__(self) # IMPORTANT FIRST STEP for a Tk root!
        self.App = app          # Needed to bind button function? No, I bind button function in App code instead.
        self.init_variables()
        self.init_ui()
        if title:
            self.title(title)

    def init_variables(self):
        self.Gelfilepath = tk.StringVar()
        self.Annotationsfilepath = tk.StringVar()
        self.Yamlfilepath = tk.StringVar()


    def init_ui(self, ):
        """
        Initialize the UI widgets. Refactored to separate method,
        since the tkroot UI might be required before
        information on the widgets are available.
         ------------------------------------
        | GEL file:  |_____________________| |
        | Lane file: |_____________________| |
        | YAML file: |_____________________| | << fileinfo frame, column=0, row=0
         ------------------------------------
        |          |  ANNOTATE!  |           | << button frame, column=0, row=0
         ------------------------------------
        | Lane names:     | YAML config:     |
        |  -------------  |  --------------  | << text input frame
        | |             | | |              | |
        | |             | | |              | | << lanenames frame
        | |             | | |              | | << yaml frame
        | |             | | |              | |
        | |             | | |              | |
        |  -------------  |  --------------  |
        |  |Save|  |Load| |  |Save|  |Load|  |
        |  Autosave |_|   |  Autosave |_|    |
         ------------------------------------
        |  _________   __________   ______   |
        | |OK (Keep)| |OK (Clear)| |Cancel|  | << buttonbox frame
        |  ¨¨¨¨¨¨¨¨¨   ¨¨¨¨¨¨¨¨¨¨   ¨¨¨¨¨¨   |
         ------------------------------------
        |  Shift-enter=Annotate,             |
        |  Added entry: "<product name>"     | << Info frame
        |  View page in browser              |
         ------------------------------------
        """
        #self.FileinfoFrame = fileframe = tk.Frame(self)
        #self.YamlFrame = yamlframe = tk.Frame(self)

        ## .grid column defaults to 0 and row defaults to the first unused row in the grid.

        ### Make sure mainframe expands: ###
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        ### MAINFRAME ###
        mainframe = tk.Frame(self)
        mainframe.grid(sticky='news', row=0, column=0)          # Defaults to 0
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(2, weight=1)     # Row 2 is textinput frame

        ### FILE FRAME -- has filepaths ###
        fileframe = tk.Frame(mainframe)
        fileframe.grid(sticky='news', row=0, column=0)           # All vertical frames are placed implicitly
        fileframe.columnconfigure(1, weight=1, minsize=30)
        #lbl = tk.Text(self, )
        lbl = tk.Label(fileframe, text="Gel file: ")
        lbl.grid(sticky='w', row=1, column=0)
        lbl = tk.Label(fileframe, text="Lane file:")
        lbl.grid(sticky='w', row=2, column=0)
        lbl = tk.Label(fileframe, text="Yaml file:")
        lbl.grid(sticky='w', row=3, column=0)        #self.GelfileEntry = entry = tk.Entry(fileframe, textvariable=self.Gelfilepath)
        entry = tk.Entry(fileframe, textvariable=self.Gelfilepath)
        entry.grid(row=1, column=1, sticky='ew')
        entry = tk.Entry(fileframe, textvariable=self.Annotationsfilepath)
        entry.grid(row=2, column=1, sticky='ew')
        entry = tk.Entry(fileframe, textvariable=self.Yamlfilepath)
        entry.grid(row=3, column=1, sticky='ew')

        ### BUTTON FRAME ###
        buttonframe = tk.Frame(mainframe)
        buttonframe.grid(sticky='news', column=0, row=1)
        btn = self.AnnotateBtn = tk.Button(buttonframe, text="ANNOTATE!", command=self.App.annotate)
        btn.grid(sticky='news', row=1, column=2)
        buttonframe.columnconfigure(2, weight=2)
        buttonframe.columnconfigure((1, 3), weight=1)
        #self.ProcessBtn = btn = tk.Button(fileframe, text="Process!")
        #btn.grid(row=3, column=1, columnspan=2, sticky='news')

        ### textinput FRAME - Contains both annotationsframe and yamlframe. ###
        textinput = tk.Frame(mainframe)     # Specify starting width and height
        textinput.grid(sticky="news", column=0, row=2)# Make sure it expands
        textinput.rowconfigure(0, weight=1)           # Make sure it expands vertically
        textinput.columnconfigure((0,1), weight=1)

        ### ANNOTATIONS FRAME ##
        annotationsframe = tk.Frame(textinput)
        annotationsframe.grid(sticky='news', column=0, row=0)
        annotationsframe.rowconfigure(1, weight=1)             # row 1 column 0 has text input
        annotationsframe.columnconfigure(0, weight=1)
        lbl = tk.Label(annotationsframe, text="Lane annotations file:")
        lbl.grid(sticky='w', column=0, row=0)
        text = self.AnnotationsText = tk.Text(annotationsframe, width=40, height=20) # default: width=80, height=24
        text.grid(sticky='news', column=0, row=1)

        ### YAML FRAME ##
        yamlframe = tk.Frame(textinput)
        yamlframe.grid(sticky='news', column=1, row=0)
        yamlframe.rowconfigure(1, weight=1)             # row 1 has text input
        yamlframe.columnconfigure(0, weight=1)
        lbl = tk.Label(yamlframe, text="Yaml (config) file:")
        lbl.grid(sticky='w', column=0, row=0)
        text = self.YamlText = tk.Text(yamlframe, width=40, height=20)
        text.grid(sticky='news', column=0, row=1)



        print("Init ui done.")


    def get_yaml(self):
        return self.YamlText.get('1.0', tk.END)

    def set_yaml(self, value):
        if self.YamlText.get('1.0', tk.END):
            self.YamlText.delete('1.0', tk.END)
        if value:
            self.YamlText.insert('1.0', value)

    def get_annotations(self):
        return self.AnnotationsText.get('1.0', tk.END)

    def set_annotations(self, value):
        if self.AnnotationsText.get('1.0', tk.END):
            self.AnnotationsText.delete('1.0', tk.END)
        if value:
            self.AnnotationsText.insert('1.0', value)



class GelAnnotatorApp(object):
    """
    Main gel annotator App object.
    Encapsulates Tk root GUI object.
    """
    def __init__(self, args):
        #self.Args = args
        print("args: ", args)
        self.Root = tkroot = GelAnnotatorTkRoot(self, title="Gel Annotator GUI")

        ## We generally do not want gelfile to be in args after this point:
        gelfilepath = args.pop('gelfile', '')
        if not gelfilepath:
            gelfilepath = self.browse_for_gelfile()
        gelfilepath = os.path.realpath(gelfilepath)
        self.set_gelfilepath(gelfilepath)
        # Desired location for yaml file, either input or based on gel file:
        yamlfilepath = args.pop('yamlfile', '')
        if not yamlfilepath:
            yamlfilepath = find_yamlfilepath(gelfilepath)
        annotationsfilepath = args.pop('annotationsfile', '')
        # Desired location for annotations file, either input or based on gel file:
        if not annotationsfilepath:
            annotationsfilepath = find_annotationsfilepath(gelfilepath)

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
            print(str(e), "-- No problem, will save to default when annotating.")


    def get_gelfilepath(self, ):
        return self.Root.Gelfilepath.get()

    def set_gelfilepath(self, value):
        self.Root.Gelfilepath.set(value)
        set_workdir(value)

    def get_yamlfilepath(self, ):
        return self.Root.Yamlfilepath.get()

    def set_yamlfilepath(self, value):
        self.Root.Yamlfilepath.set(value)

    def get_yaml(self):
        return self.Root.get_yaml()

    def set_yaml(self, value):
        """ Set content of yaml text widget. """
        #print("Setting content of yaml widget to:", value)
        self.Root.set_yaml(value)

    def init_yaml(self, args, filepath=None):
        """
        Merge args with yaml file (args take precedence).
        """
        #if args is None:
        #    args = self.Args
        fn = filepath or self.get_yamlfilepath()
        try:
            with open(fn) as fd:
                yamlconfig = yaml.load(fd)
                logger.debug("loading yaml file: %s", fn)
        except IOError:
            logger.debug("Could not find/load yaml file %s", fn)
            yamlconfig = {}
        logger.debug("yamlconfig: %s", yamlconfig)
        logger.debug("args: %s", args)
        args.update(mergedicts(yamlconfig, args))
        #self.Args = args
        self.set_yaml(yaml.dump(args, default_flow_style=False))


    def load_yaml(self, filepath=None):
        """ Load content of yaml flie into yaml text widget. """
        fn = filepath or self.get_yamlfilepath()
        with open(fn) as fd:
            #text = yaml.load(fd)
            text = fd.read()
        self.set_yaml(text)

    def save_yaml(self):
        """ Save content of yaml text widget to yaml file. """
        fn = self.get_yamlfilepath()
        text = self.get_yaml()
        if not fn:
            raise ValueError("Yaml file entry is empty.")
        with open(fn, 'wb') as fd:
            # No! Dont dump, just save.
            #yaml.dump(text, fd, default_flow_style=False)
            fd.write(text)

    def get_annotationsfilepath(self, ):
        return self.Root.Annotationsfilepath.get()

    def set_annotationsfilepath(self, value):
        self.Root.Annotationsfilepath.set(value)

    def get_annotations(self):
        return self.Root.get_annotations()

    def set_annotations(self, value):
        self.Root.set_annotations(value)

    def load_annotations(self, filepath=None):
        fn = filepath or self.get_annotationsfilepath()
        with open(fn) as fd:
            text = fd.read()
        self.set_annotations(text)

    def save_annotations(self):
        fn = self.get_annotationsfilepath()
        text = self.get_annotations()
        if not fn:
            raise ValueError("Annotations file entry is empty.")
        with open(fn, 'wb') as fd:
            fd.write(text)

    def browse_for_gelfile(self):
        filename = askopenfilename(filetypes=(("GEL files", "*.gel"),
                                              ("Image files", "*.png;*.jpg"),
                                              ("All supported", "*.gel;*.png;*.jpg"),
                                              ("All files", "*.*")
                                              ))
        print("Setting gelfile to:", filename)
        self.set_gelfilepath(filename)

    def browse_for_yamlfile(self):
        filename = askopenfilename(filetypes=(("YAML files", "*.yaml;*.yml"),
                                              ("All files", "*.*")
                                              ))
        print("Setting yamlfile to:", filename)
        self.set_yamlfilepath(filename)

    def browse_for_annotationsfile(self):
        filename = askopenfilename(filetypes=(("Text files", "*.txt"),
                                              ("YAML files", "*.yaml;*.yml"),
                                              ("All files", "*.*")
                                              ))
        print("Setting yamlfile to:", filename)
        self.set_yamlfilepath(filename)



    def mainloop(self):
        logger.info("Starting tkroot mainloop()...")
        self.Root.mainloop()
        logger.info("<< Tkroot mainloop() complete - (and App start() ) <<")


    def annotate(self):
        # Load/save? Uhm, no, just save
        # and then invoke gelannotator with args.
        # Update yaml when done.
        #args = self.Args # This isn't needed; use
        gelfile = self.get_gelfilepath()
        yamlfile = self.get_yamlfilepath()
        annotationsfile = self.get_annotationsfilepath()
        self.save_yaml()
        self.save_annotations()
        logger.debug("Annotating gel, using args: %s", args)
        dwg, svgfilename = annotate_gel(gelfile, yamlfile=yamlfile, annotationsfile=annotationsfile)
        if args.get('updateyaml', True):
            # Not sure if this should be done here or in gelannotator:
            logger.debug("Re-loading yaml file")
            self.load_yaml()
        logger.debug("Gel annotation complete!")
        # I wouldn't expect the annotations file to have changed.



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
        print("No absolute directory found, using cwd.")
        return os.getcwd()

def set_workdir(args):
    d = get_workdir(args)
    print("Chainging dir:", d)
    os.chdir(d)



if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    init_logging()
    # test:
    testing = False
    if testing:
        ap = make_parser()
        argns = ap.parse_args('RS323_Agarose_ScaffoldPrep_550V.gel'.split())
    else:
        argns = parseargs()
    args = argns.__dict__
    # set_workdir(args) Not needed, done by app during set_gelfilepath
    main(args)
