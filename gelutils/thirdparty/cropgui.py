#!/usr/bin/python
#    cropgui, a graphical front-end for lossless jpeg cropping
#    Copyright (C) 2009 Jeff Epler <jepler@unpythonic.net>
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os
# import signal
import math
import subprocess
import time
from PIL import ImageFilter
from PIL import ImageDraw
from PIL import Image
try:
    # import Tkinter as tkinter
    from Tkinter import Tk, Label, Button, IntVar
    from tkFileDialog import askopenfilename
    # from Tkinter import Image
    from Tkinter.ImageTk import PhotoImage
except ImportError:
    # python 3:
    # import tkinter
    from tkinter import Tk, Label, Button, IntVar
    from tkinter.filedialog import askopenfilename
    # from tkinter import Image
    from tkinter import PhotoImage

# Constants:
(
    DRAG_NONE,
    DRAG_TL, DRAG_T, DRAG_TR,
    DRAG_L,  DRAG_C, DRAG_R,
    DRAG_BL, DRAG_B, DRAG_BR
) = range(10)


def clamp(value, low, high):
    if value < low:
        return low
    if high < value:
        return high
    return value


class DragManager(object):
    def __init__(self, app, w, b=None, inf=None):
        self.render_flag = 0
        self.l = w
        self.app = app
        if b:
            b.configure(command=self.done)
        self.inf = inf
        self._image = None
        self.tkimage = None
        self.top = 0
        self.left = 0
        self.right = 0
        self.bottom = 0
        self.blurred = None
        self.xor = None
        self.x0 = None
        self.y0 = None
        w.bind("<Button-1>", self.start)
        w.bind("<Double-Button-1>", self.start)
        w.bind("<Button1-Motion>", self.motion)
        w.bind("<ButtonRelease-1>", self.end)
        dummy_image = Image.frombytes('RGB', (1, 1), '\0\0\0')
        self.dummy_tkimage = PhotoImage(dummy_image)
        self.state = DRAG_NONE
        self.round = 1
        self.image = None
        w.configure(image=self.dummy_tkimage)
        self.v = IntVar(app)

    def get_w(self):
        return self.image.size[0]
    w = property(get_w)

    def get_h(self):
        return self.image.size[1]
    h = property(get_h)

    def set_image(self, image):
        if image is None:
            if hasattr(self, 'left'):
                del self.left
            if hasattr(self, 'right'):
                del self.right
            if hasattr(self, 'bottom'):
                del self.bottom
            if hasattr(self, 'blurred'):
                del self.blurred
            if hasattr(self, 'xor'):
                del self.xor
            if hasattr(self, 'tkimage'):
                del self.tkimage
            self._image = None
        else:
            self._image = image.copy()
            self.top = 0
            self.left = 0
            self.right = self.w
            self.bottom = self.h
            mult = len(self.image.mode)
            self.blurred = image.copy().filter(
                ImageFilter.SMOOTH_MORE).point([x/2 for x in range(256)] * mult)
            self.xor = image.copy().point([x ^ 128 for x in range(256)] * mult)
        self.render()

    def fix(self, a, b, lim, round_to_int):
        a, b = sorted((b, a))
        a = clamp(a, 0, lim)
        b = clamp(b, 0, lim)
        if round_to_int:
            a = int(math.floor(a * 1. / self.round)*self.round)
        return a, b

    def set_crop(self, top, left, right, bottom, round_to_int=False):
        self.top, self.bottom = self.fix(top, bottom, self.h, round_to_int)
        self.left, self.right = self.fix(left, right, self.w, round_to_int)
        self.render()

    def get_image(self):
        return self._image
    image = property(get_image, set_image, None, "change the target of this DragManager")

    def render(self):
        if not self.render_flag:
            self.render_flag = True
            self.app.after_idle(self.do_render)

    def do_render(self):
        if not self.render_flag:
            return
        self.render_flag = False
        if self.image is None:
            self.l.configure(image=self.dummy_tkimage)
            return

        mask = Image.new('1', self.image.size, 0)
        mask.paste(1, (self.left, self.top, self.right, self.bottom))
        image = Image.composite(self.image, self.blurred, mask)

        t, l, r, b = self.top, self.left, self.right, self.bottom
        dx = (r - l) / 4
        dy = (b - t) / 4

        if self.inf:
            self.inf.configure(
                text=(
                    "Left:  %4d  Top:    %4d\n"
                    "Right: %4d  Bottom: %4d\n"
                    "Width: %4d  Height: %4d\n"
                    "State: %s") % (l, t, r, b, r-l, b-t, self.state),
                font="fixed")

        mask = Image.new('1', self.image.size, 1)
        draw = ImageDraw.Draw(mask)

        draw.line([l, t, r, t], fill=0)
        draw.line([l, b, r, b], fill=0)
        draw.line([l, t, l, b], fill=0)
        draw.line([r, t, r, b], fill=0)

        draw.line([l+dx, t, l+dx, t+dy, l, t+dy], fill=0)
        draw.line([r-dx, t, r-dx, t+dy, r, t+dy], fill=0)
        draw.line([l+dx, b, l+dx, b-dy, l, b-dy], fill=0)
        draw.line([r-dx, b, r-dx, b-dy, r, b-dy], fill=0)

        image = Image.composite(image, self.xor, mask)
        self.tkimage = PhotoImage(image)
        self.l.configure(image=self.tkimage)

    def enter(self, event):
        pass

    def leave(self, event):
        pass

    def classify(self, x, y):
        t, l, r, b = self.top, self.left, self.right, self.bottom
        dx = (r - l) / 4
        dy = (b - t) / 4

        if x < l:
            return DRAG_NONE
        if x > r:
            return DRAG_NONE
        if y < t:
            return DRAG_NONE
        if y > b:
            return DRAG_NONE

        if x < l+dx:
            if y < t+dy:
                return DRAG_TL
            if y < b-dy:
                return DRAG_L
            return DRAG_BL
        if x < r-dx:
            if y < t+dy:
                return DRAG_T
            if y < b-dy:
                return DRAG_C
            return DRAG_B
        else:
            if y < t+dy:
                return DRAG_TR
            if y < b-dy:
                return DRAG_R
            return DRAG_BR

    def start(self, event):
        self.x0 = event.x
        self.y0 = event.y
        self.state = self.classify(event.x, event.y)

    def motion(self, event):
        dx = event.x - self.x0
        self.x0 = event.x
        dy = event.y - self.y0
        self.y0 = event.y
        new_top, new_left, new_right, new_bottom = \
            self.top, self.left, self.right, self.bottom
        if self.state == DRAG_C:
            # A center drag bumps into the edges
            if dx > 0:
                dx = min(dx, self.w - self.right - 1)
            else:
                dx = max(dx, -self.left)
            if dy > 0:
                dy = min(dy, self.h - self.bottom - 1)
            else:
                dy = max(dy, -self.top)
        if self.state in (DRAG_TL, DRAG_T, DRAG_TR, DRAG_C):
            new_top = self.top + dy
        if self.state in (DRAG_TL, DRAG_L, DRAG_BL, DRAG_C):
            new_left = self.left + dx
        if self.state in (DRAG_TR, DRAG_R, DRAG_BR, DRAG_C):
            new_right = self.right + dx
        if self.state in (DRAG_BL, DRAG_B, DRAG_BR, DRAG_C):
            new_bottom = self.bottom + dy
        # A drag never moves left past right and so on
        new_top = min(self.bottom, new_top)
        new_left = min(self.right, new_left)
        new_right = max(self.left, new_right)
        new_bottom = max(self.top, new_bottom)

        self.set_crop(new_top, new_left, new_right, new_bottom)

    def end(self, event):
        self.set_crop(self.top, self.left, self.right, self.bottom, True)
        self.state = DRAG_NONE

    def close(self):
        self.v.set(-1)

    def done(self):
        self.v.set(1)

    def double(self, event):
        self.done()

    def wait(self):
        self.app.wait_variable(self.v)
        value = self.v.get()
        if value == -1:
            raise SystemExit
        return value


def test():

    app = Tk()
    app.wm_title("CropGUI -- lossless cropping and rotation of jpeg files")
    app.wm_iconname("CropGUI")

    preview = Label(app)
    do_crop = Button(app, text="Crop")
    info = Label(app)
    preview.pack(side="bottom")
    do_crop.pack(side="left")
    info.pack(side="left")

    max_h = app.winfo_screenheight() - 64 - 32
    max_w = app.winfo_screenwidth() - 64

    drag = DragManager(app, preview, do_crop, info)
    app.wm_protocol('WM_DELETE_WINDOW', drag.close)

    def image_names():
        if len(sys.argv) > 1:
            for i in sys.argv[1:]:
                yield i
        else:
            while 1:
                names = askopenfilename(
                    master=app,
                    defaultextension=".jpg", multiple=1, parent=app,
                    filetypes=(
                        ("JPEG Image Files", ".jpg .JPG .jpeg .JPEG"),
                        ("All files", "*"),
                    ),
                    title="Select images to crop")
                if not names:
                    break
                for name in names:
                    yield name

    pids = set()

    def reap():
        global pids
        pids = set(p for p in pids if p.poll() is None)

    for image_name in image_names():
        img = Image.open(image_name)
        iw, ih = img.size
        scale = 1
        while iw > max_w or ih > max_h:
            iw /= 2
            ih /= 2
            scale *= 2
        img.thumbnail((iw, ih))
        drag.image = img
        drag.round = max(1, 8/scale)
        if not drag.wait():
            continue  # user hit "next" (tba) without cropping

        base, ext = os.path.splitext(image_name)
        t, l, r, b = drag.top, drag.left, drag.right, drag.bottom
        t *= scale
        l *= scale
        r *= scale
        b *= scale
        cropspec = "%dx%d+%d+%d" % (r-l, b-t, l, t)
        target = base + "-crop" + ext
        target = open(target, "wb")
        pids.add(subprocess.Popen(
            ['jpegtran', '-optimize', '-progressive', '-crop', cropspec, image_name],
            stdout=target))
        target.close()

    while pids:
        reap()
        sys.stdout.write("Waiting for %d children to exit.   \r" % len(pids))
        sys.stdout.flush()
        time.sleep(.1)
    sys.stdout.write(" "*79 + "\r")


# 1. open image
# 2. choose 1/2, 1/4, 1/8 scaling so that resized image fits onscreen
# 3. load image at requested size
# 4. run GUI to get desired crop settings
# 5. write output file

if __name__ == '__main__':
    test()
