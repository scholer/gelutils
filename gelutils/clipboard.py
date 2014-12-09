#!/usr/bin/env python3
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

"""

Module for interacting with the OS clipboard.

Possible options for working with the clipboard:

* tkinter       cross-platform, starts a brief GUI
* Qt            cross-platform, starts a brief GUI
* pygtk         Linux
* pyperclip     cross-platform  Uses Ctypes. https://github.com/asweigart/pyperclip
* Xerox         cross-platform  Requires win32 module. https://github.com/kennethreitz/xerox
* clipboard     cross-platform  https://pypi.python.org/pypi/clipboard  -- exactly the same as pyperclip
* win32clipboard    windwos

# from https://www.daniweb.com/software-development/python/threads/422292/getclipboarddata#post1802945
from PySide.QtGui import QApplication
app = QApplication([])
clipboard = app.clipboard()
text = clipboard.text() # gets clipboard
app.processEvents() # Is required to avoid hanging...

"""
from __future__ import print_function
from six import string_types # python 2*3 compatability
import os
import sys

try:
    from Tkinter import Tk
except ImportError:
    from tkinter import Tk

## Clipboard in GTK:
try:
    import pygtk
    pygtk.require('2.0')
    import gtk # gtk provides clipboard access:
    # clipboard = gtk.clipboard_get()
    # text = clipboard.wait_for_text()
except ImportError:
    # Will happen on Windows/Mac:
    pass

## win32clipboard:
try:
    import win32clipboard
    #print "win32clipboard is available."
except ImportError:
    pass

## pyperclip:
try:
    import pyperclip
    #print "pyperclip is available."
except ImportError:
    # check for import with
    # globals(), locals(), vars() or sys.modules.keys()
    #>>> if 'pyperclip' in sys.modules.keys()
    pass

## xerox:
try:
    import xerox
except ImportError:
    pass


def set_clipboard(text, datatype=None):
    """
    Arg datatype currently not used. Will generally assumed to be unicode text.
    From http://stackoverflow.com/questions/579687/how-do-i-copy-a-string-to-the-clipboard-on-windows-using-python
    """
    if 'xerox' in sys.modules.keys():
        xerox.copy(text)
    elif 'pyperclip' in sys.modules.keys():
        pyperclip.copy(text)
    elif 'gtk' in sys.modules.keys():
        clipboard = gtk.clipboard_get()
        text = clipboard.set_text(text)
    elif 'win32clipboard' in sys.modules.keys():
        wcb = win32clipboard
        wcb.OpenClipboard()
        wcb.EmptyClipboard()
        # wcb.SetClipboardText(text)  # doesn't work
        # SetClipboardData Usage:
        # >>> wcb.SetClipboardData(<type>, <data>)
        # wcb.SetClipboardData(wcb.CF_TEXT, text.encode('utf-8')) # doesn't work
        wcb.SetClipboardData(wcb.CF_UNICODETEXT, unicode(text)) # works
        wcb.CloseClipboard() # User cannot use clipboard until it is closed.
    else:
        # If code is run from within e.g. an ipython qt console, invoking Tk root's mainloop() may hang the console.
        tkroot = Tk()
        # r.withdraw()
        tkroot.clipboard_clear()
        tkroot.clipboard_append(text)
        tkroot.mainloop() # the Tk root's mainloop() must be invoked.
        tkroot.destroy()

def get_clipboard():
    """
    Get content of OS clipboard.
    """
    if 'xerox' in sys.modules.keys():
        print("Returning clipboard content using xerox...")
        return xerox.paste()
    elif 'pyperclip' in sys.modules.keys():
        print("Returning clipboard content using pyperclip...")
        return pyperclip.paste()
    elif 'gtk' in sys.modules.keys():
        print("Returning clipboard content using gtk...")
        clipboard = gtk.clipboard_get()
        return clipboard.wait_for_text()
    elif 'win32clipboard' in sys.modules.keys():
        wcb = win32clipboard
        wcb.OpenClipboard()
        try:
            data = wcb.GetClipboardData(wcb.CF_TEXT)
        except TypeError as err:
            print(err)
            print("No text in clipboard.")
        wcb.CloseClipboard() # User cannot use clipboard until it is closed.
        return data
    else:
        print("locals.keys() is: ", sys.modules.keys().keys())
        print("falling back to Tk...")
        tkroot = Tk()
        tkroot.withdraw()
        result = tkroot.selection_get(selection="CLIPBOARD")
        tkroot.destroy()
        print("Returning clipboard content using Tkinter...")
        return result


# Aliases:
copy = set_clipboard
paste = get_clipboard

def addToClipBoard_windows(text):
    """
    This uses the external 'clip' program to add content to the windows clipboard by invoking:
        >>> echo <text> | clip
    Example:
        >>> addToClipBoard('penny lane')

    """
    command = 'echo ' + text.strip() + '| clip'
    os.system(command)


def copy_file_to_clipboard(file):
    """
    Copies the content of open file <fd> to clipboard.
    If fd is a string it is assumed that you want to
    open that file and read its content into the clipboard.
    Usage:
    >>> myfd = open('/path/to/a/textfile.txt')
    >>> copy_file_to_clipboard(myfd)
    Shortcut:
    >>> copy_file_to_clipboard('/path/to/a/textfile.txt')
    >>> content = get_clipboard() # returns content of file.
    """
    if isinstance(file, string_types):
        file = open(file)
    set_clipboard(file.read())
