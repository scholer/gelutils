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
    # python 3:
    import tkinter as tk                                # pylint: disable=F0401
    from tkinter import ttk                             # pylint: disable=F0401
    #from tkinter.filedialog import askopenfilename      # pylint: disable=F0401
except ImportError:
    # python 2:
    import Tkinter as tk        # pylint: disable=F0401
    import ttk                  # pylint: disable=F0401
    #from tkFileDialog import askopenfilename

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

#from gelannotator import annotate_gel, find_yamlfilepath, find_annotationsfilepath
#from argutils import parseargs, make_parser, mergedicts
#from utils import init_logging


class GelAnnotatorTkRoot(tk.Tk):    # pylint: disable=R0904
    """
    The actual UI.
    """
    def __init__(self, app, title=None):
        tk.Tk.__init__(self) # IMPORTANT FIRST STEP for a Tk root!
        self.App = app          # Needed to bind button function? No, I bind button function in App code instead.

        # Init variables:
        self.Gelfilepath = tk.StringVar()
        self.Gelfiledirectory = tk.StringVar()
        self.Annotationsfilepath = tk.StringVar()
        self.Yamlfilepath = tk.StringVar()
        self.Statustext = tk.StringVar(value="Tip: Use CTRL+ENTER to annotate. (Buffers can be saved with ctrl+s, but that's also done automatically.)")

        self.init_ui()
        if title:
            self.title(title)


    def init_ui(self):  # pylint: disable=R0915
        """
        Initialize the UI widgets. Refactored to separate method,
        since the tkroot UI might be required before
        information on the widgets are available.
         ------------------------------------
        | GEL file:  |____________| |Browse| |
        | Lane file: |____________| |Browse| |
        | YAML file: |____________| |Browse| | << fileinfo frame, column=0, row=0
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
         ------------------------------------


Non-used:

        |  |Save|  |Load| |  |Save|  |Load|  |
        |  Autosave |_|   |  Autosave |_|    |

        |  _________   __________   ______   |
        | |OK (Keep)| |OK (Clear)| |Cancel|  | << buttonbox frame
        |  ¨¨¨¨¨¨¨¨¨   ¨¨¨¨¨¨¨¨¨¨   ¨¨¨¨¨¨   |
         ------------------------------------
        |  Shift-enter=Annotate,             |
        |  Added entry: "<product name>"     | << Info frame
        |  View page in browser              |
         ------------------------------------
        """
        #self.FileinfoFrame = fileframe = ttk.Frame(self)
        #self.YamlFrame = yamlframe = ttk.Frame(self)

        ## .grid column defaults to 0 and row defaults to the first unused row in the grid.

        ### Make sure mainframe expands: ###
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        ### MAINFRAME ###
        mainframe = ttk.Frame(self)
        mainframe.grid(sticky='news', row=0, column=0)          # Defaults to 0
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(2, weight=1)     # Row 2 is textinput frame
        mainframe.rowconfigure(1, minsize=40)   # Button frame.

        ### FILE FRAME -- has filepaths ###
        fileframe = ttk.Frame(mainframe)
        fileframe.grid(sticky='news', row=0, column=0)           # All vertical frames are placed implicitly
        fileframe.columnconfigure(1, weight=1, minsize=30)
        #lbl = tk.Text(self, )

        # Filepath labels:
        lbl = ttk.Label(fileframe, text="Directory: ")
        lbl.grid(sticky='w', row=0, column=0)
        lbl = ttk.Label(fileframe, text="Gel file: ")
        lbl.grid(sticky='w', row=1, column=0)
        lbl = ttk.Label(fileframe, text="Lane file:")
        lbl.grid(sticky='w', row=2, column=0)
        lbl = ttk.Label(fileframe, text="Yaml file:")
        lbl.grid(sticky='w', row=3, column=0)        #self.GelfileEntry = entry = ttk.Entry(fileframe, textvariable=self.Gelfilepath)
        # How to make the right-most text visible? , justify='right' does not have the desired effect...

        # Filepath entries:
        entry = ttk.Entry(fileframe, textvariable=self.Gelfiledirectory, state='readonly')
        entry.grid(row=0, column=1, sticky='ew')
        entry = ttk.Entry(fileframe, textvariable=self.Gelfilepath)     # = self.GelfilepathEntry
        entry.grid(row=1, column=1, sticky='ew')
        entry = ttk.Entry(fileframe, textvariable=self.Annotationsfilepath)
        entry.grid(row=2, column=1, sticky='ew')
        entry = ttk.Entry(fileframe, textvariable=self.Yamlfilepath)
        entry.grid(row=3, column=1, sticky='ew')

        # BROWSE buttons
        btn = ttk.Button(fileframe, text='Help...', command=self.App.show_help)
        btn.grid(row=0, column=2)
        btn = ttk.Button(fileframe, text='Browse', command=self.App.browse_for_gelfile)
        btn.grid(row=1, column=2)
        btn = ttk.Button(fileframe, text='Browse', command=self.App.browse_for_annotationsfile)
        btn.grid(row=2, column=2)
        btn = ttk.Button(fileframe, text='Browse', command=self.App.browse_for_yamlfile)
        btn.grid(row=3, column=2)

        ### BUTTON FRAME ###
        buttonframe = ttk.Frame(mainframe)
        buttonframe.grid(sticky='news', column=0, row=1)
        btn = self.AnnotateBtn = ttk.Button(buttonframe, text="ANNOTATE!", command=self.App.annotate)  # pylint: disable=W0201
        btn.grid(sticky='news', row=1, column=2)
        buttonframe.rowconfigure(1, minsize=40) # mainframe row 1 must also be set to minsize.
        buttonframe.columnconfigure(2, weight=2)
        buttonframe.columnconfigure((1, 3), weight=1)
        #self.ProcessBtn = btn = ttk.Button(fileframe, text="Process!")
        #btn.grid(row=3, column=1, columnspan=2, sticky='news')

        ### textinput FRAME - Contains both annotationsframe and yamlframe. ###
        textinput = ttk.Frame(mainframe)     # Specify starting width and height
        textinput.grid(sticky="news", column=0, row=2)# Make sure it expands
        textinput.rowconfigure(0, weight=1)           # Make sure it expands vertically
        textinput.columnconfigure((0, 1), weight=1)

        def loose_focus(event=None):
            self.AnnotateBtn.focus_set()

        def dont_propagate(event=None):
            # prevent Tkinter from propagating the event by returning the string "break"
            print("dont_propagate called...")
            return "break"

        self.bind_all("<Escape>", loose_focus)
        ### ANNOTATIONS FRAME ##
        annotationsframe = ttk.Frame(textinput)
        annotationsframe.grid(sticky='news', column=0, row=0)
        annotationsframe.rowconfigure(1, weight=1)             # row 1 column 0 has text input
        annotationsframe.columnconfigure(0, weight=1)
        lbl = ttk.Label(annotationsframe, text="Lane annotations file:")
        lbl.grid(sticky='w', column=0, row=0)
        # undo ref: http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/text-undo-stack.html
        # http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/text.html
        text = self.AnnotationsText = tk.Text(annotationsframe, width=40, height=20, undo=True, maxundo=-1) # default: width=80, height=24   # pylint: disable=W0201
        text.grid(sticky='news', column=0, row=1)
        text.bind(sequence='<Control-s>', func=self.App.save_annotations)
        # text.bind("<Control-Return>", dont_propagate)
        # More cheat-sheet: http://stackoverflow.com/questions/16082243/how-to-bind-ctrl-in-python-tkinter

        ### YAML FRAME ##
        yamlframe = ttk.Frame(textinput)
        yamlframe.grid(sticky='news', column=1, row=0)
        yamlframe.rowconfigure(1, weight=1)             # row 1 has text input
        yamlframe.columnconfigure(0, weight=1)
        lbl = ttk.Label(yamlframe, text="Yaml (config) file:")
        lbl.grid(sticky='w', column=0, row=0)
        text = self.YamlText = tk.Text(yamlframe, width=40, height=30, undo=True, maxundo=-1) # pylint: disable=W0201
        text.grid(sticky='news', column=0, row=1)
        text.bind(sequence='<Control-s>', func=self.App.save_yaml)
        #text.bind("<Control-Return>", dont_propagate)

        ### INFO FRAME  - displays some help to the user. ##
        infoframe = tk.Frame(mainframe, bd=1, relief='sunken')     # Specify starting width and height
        infoframe.grid(sticky="news", column=0, row=3)# Make sure it expands
        # standard statusbar style:
        # Using standard tk, don't want to bother with ttk styles for now...
        # anchor='w' ??
        lbl = self.Statusbar = tk.Label(infoframe, textvariable=self.Statustext)#, borderwidth=1, relief='sunken')
                                         #text="Tip: Use CTRL+ENTER to annotate. (Buffers can be saved with ctrl+s, but that's also done automatically.)")
        lbl.grid(sticky='news')
        #lbl = ttk.Label(infoframe, text="(Buffers can be saved with ctrl+s, but you don't have to.)")
        #lbl.grid(sticky='news')
        #l = tk.Label(f, text="( Shift-enter=OK (keep), Enter=OK (clear), Escape=Abort )")
        #infoframe.rowconfigure(0, weight=1)           # Make sure it expands vertically
        #infoframe.columnconfigure(0, weight=1)

        #self.bind(sequence='<Control-Return>', func=self.App.annotate) # Binding at app-level instead with bind_all

        logger.debug("Init ui done.")

    def set_statustext(self, value):
        self.Statustext.set(value)

    def set_gelfilepath(self, filepath):
        self.Gelfilepath.set(filepath)
        # I want to make sure the right part is visible?
        #self.GelfilepathEntry.see(...) # Nope, that only works for a Text entry...

    def get_yaml(self):
        """ Returns content of yaml text widget. """
        return self.YamlText.get('1.0', tk.END)

    def set_yaml(self, value):
        """ Sets content of yaml text widget. """
        if self.YamlText.get('1.0', tk.END):
            self.YamlText.delete('1.0', tk.END)
        if value:
            self.YamlText.insert('1.0', value)

    def get_annotations(self):
        """ Returns content of annotations text widget. """
        return self.AnnotationsText.get('1.0', tk.END)

    def set_annotations(self, value):
        """ Sets content of annotations text widget. """
        if self.AnnotationsText.get('1.0', tk.END):
            self.AnnotationsText.delete('1.0', tk.END)
        if value:
            self.AnnotationsText.insert('1.0', value)
