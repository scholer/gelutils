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

"""

import Tkinter as tk
#import tkMessageBox
#import ttk

#import os
import yaml

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

from gelannotator import find_yamlfilepath, parseargs, makePNG, makeSVG

class GelAnnotatorTkRoot(tk.Tk):
    """
    """
    def __init__(self, app, title=None):
        tk.Tk.__init__(self) # IMPORTANT FIRST STEP for a Tk root!
        #self.App = app
        self.init_variables()
        self.init_ui()
        if title:
            self.title(title)

    def init_variables(self):
        self.Gelfilepath = tk.StringVar()
        self.Yamlfilepath = tk.StringVar()


    def init_ui(self, ):
        """
        Initialize the UI widgets. Refactored to separate method,
        since the tkroot UI might be required before
        information on the widgets are available.
         ------------------------------------
        | Gel file: |_____________________|  |
        | YAML file:|_____________________|  | << buttonbox frame
        |                                    |
         ------------------------------------
        |                                    |
        |                                    |
        |                                    |
        |                                    | << yaml frame
        |                                    |
        |                                    |
        |                                    |
        |                                    |
         ------------------------------------
        |  _________   __________   ______   |
        | |OK (Keep)| |OK (Clear)| |Cancel|  | << buttonbox frame
        |  ¨¨¨¨¨¨¨¨¨   ¨¨¨¨¨¨¨¨¨¨   ¨¨¨¨¨¨   |
         ------------------------------------
        |  Enter=OK, Shift-enter=OK (keep),  |
        |  Added entry: "<product name>"     | << Info frame
        |  View page in browser              |
         ------------------------------------
        """
        #self.FileinfoFrame = fileframe = tk.Frame(self)
        #self.YamlFrame = yamlframe = tk.Frame(self)
        fileframe = tk.Frame(self)
        fileframe.grid(sticky='news')
        #fileframe.rowconfigure()
        fileframe.columnconfigure(2, weight=1)
        yamlframe = tk.Frame(self)
        yamlframe.grid(sticky='news')
        yamlframe.rowconfigure(1, weight=1)
        yamlframe.columnconfigure(1, weight=1)
        #lbl = tk.Text(self, )
        lbl = tk.Label(fileframe, text="Gel file: ")
        lbl.grid(row=1, column=1)
        lbl = tk.Label(fileframe, text="Yaml file:")
        lbl.grid(row=2, column=1)
        #self.GelfileEntry = entry = tk.Entry(fileframe, textvariable=self.Gelfilepath)
        entry = tk.Entry(fileframe, textvariable=self.Gelfilepath)
        entry.grid(row=1, column=2, sticky='ew')
        self.YamlfileEntry = entry = tk.Entry(fileframe, textvariable=self.Yamlfilepath)
        entry.grid(row=2, column=2, sticky='ew')
        self.ProcessBtn = btn = tk.Button(fileframe, text="Process!")
        btn.grid(row=3, column=1, columnspan=2, sticky='news')
        #tk.Text(self.journalwikiframe, state='disabled', height=14, )
        #body.grid(sticky="news") # row=1, column=0, - now implicit...
        self.YamlText = text = tk.Text(yamlframe)
        text.grid(sticky='news')
        print "Init ui done."

    def get_yaml(self):
        return self.YamlText.get('1.0', tk.END)

    def set_yaml(self, value):
        if self.YamlText.get('1.0', tk.END):
            self.YamlText.delete('1.0', tk.END)
        if value:
            self.YamlText.insert('1.0', value)



class GelAnnotatorApp(object):
    """
    Main gel annotator App object.
    Encapsulates Tk root object.
    """
    def __init__(self, gelfilepath, yamlfilepath=None, argns=None):
        self.Root = tkroot = GelAnnotatorTkRoot()
        self.set_gelfilepath(gelfilepath)
        if yamlfilepath is None:
            if getattr(argns, 'yamlfile', None):
                yamlfilepath = argns.yamlfile
            else:
                yamlfilepath = find_yamlfilepath(gelfilepath)
        self.set_yamlfilepath(yamlfilepath)
        try:
            self.load_yaml()
        except (IOError, OSError) as e:
            print str(e) + "-- No problem."

    def get_gelfilepath(self, ):
        return self.Root.Gelfilepath.get()

    def set_gelfilepath(self, value):
        return self.Root.Gelfilepath.set(value)

    def get_yamlfilepath(self, ):
        return self.Root.Yamlfilepath.get()

    def set_yamlfilepath(self, value):
        return self.Root.Yamlfilepath.set(value)

    def get_yaml(self):
        return self.Root.get_yaml()

    def set_yaml(self, value):
        return self.Root.set_yaml(value)

    def load_yaml(self, filepath=None):
        fn = filepath or self.get_yamlfilepath()
        with open(fn) as fd:
            text = yaml.load(fd)
        self.set_yaml(text)

    def save_yaml(self):
        fn = self.get_yamlfilepath()
        text = self.get_yaml()
        if not fn:
            raise ValueError("Yaml file entry is empty.")
        with open(fn, 'w') as fd:
            yaml.dump(text, fd)

    def mainloop(self):
        logger.info("Starting tkroot mainloop()...")
        self.Root.mainloop()
        logger.info("<< Tkroot mainloop() complete - (and App start() ) <<")


    def procss(self):
        conf = self.load_yaml()
        



if __name__ == '__main__':
    argns = parseargs()
    app = GelAnnotatorApp(argns.gelfile, argns=argns)
    app.mainloop()

