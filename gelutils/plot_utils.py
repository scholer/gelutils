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


import numpy as np
from matplotlib import pyplot
from math import ceil


def show_image(img, title=None,
               area=None, xlim=None, ylim=None,
               plotidx=None, plotrows=1, plotcols=2,
               figsize=None, use_matshow=False,
               clim=None, cmap="gray_r", clim_percentile=None):
    if clim is None:
        if clim_percentile:
            if isinstance(clim_percentile, (int, float, np.number)):
                clim = (0, np.percentile(img, clim_percentile))
            else:
                clim = (np.percentile(img, clim_percentile[0]), np.percentile(img, clim_percentile[1]))
        else:
            clim = [np.min(img), np.max(img)]
    elif isinstance(clim, int):
        clim = [0, clim]
    elif clim[0] is None or clim[1] is None:
        clim = (0 if clim[0] is None else clim[0], np.max(img) if clim[1] is None else clim[1])
    if plotidx is not None:
        if plotidx < 1 or plotidx > plotrows*plotcols:
            # create new figure and reset plotidx to 1:
            plotidx = 1
            if figsize is None:
                figsize = (12, 4*plotrows)
            pyplot.figure(figsize=figsize)
            pyplot.subplot(plotrows, plotcols, plotidx)  # nrows
        else:
            pyplot.subplot(plotrows, plotcols, plotidx)
        plotidx += 1
    if area:
        # area is xmin, xmax, ymin, ymax; indexing is [row, col] = [y, x]
        xmin, xmax, ymin, ymax = area
        img = img[ymin:ymax+1, xmin:xmax+1]
    if use_matshow:
        # imshow applies interpolation, so you may want to use matshow to get an un-interpolated view:
        # however, matshow is really weird and will *always* create a new figure, unless fignum is zero or False.
        pyplot.matshow(img, cmap=cmap, clim=clim, fignum=False)
    else:
        pyplot.imshow(img, cmap=cmap, clim=clim)
    if title:
        pyplot.title(title)
    if xlim:
        pyplot.xlim(xlim)
    if ylim:
        # reverse ylimits because images are displayed with origin in upper-left corner not lower-left.
        if ylim[0] < ylim[1]:
            ylim = ylim[::-1]
        pyplot.ylim(ylim)
    pyplot.colorbar()
    return plotidx


def show_plot(x, y=None, title=None, plotidx=None, plotrows=1, plotcols=2, figsize=None, c=None):
    if plotidx is not None:
        if plotidx < 1 or plotidx > plotrows*plotcols:
            # create new figure and reset plotidx to 1:
            plotidx = 1
            if figsize is None:
                figsize = (12, 4*plotrows)
            pyplot.figure(figsize=figsize)
            pyplot.subplot(plotrows, plotcols, plotidx)  # nrows
        else:
            pyplot.subplot(plotrows, plotcols, plotidx)
        plotidx += 1
    if y:
        pyplot.plot(x, y, c=c)
    else:
        pyplot.plot(x, c=c)
    if title:
        pyplot.title(title)
    return plotidx


def show_images(images):

    for ploti, tup in enumerate(images, 1):
        if isinstance(tup, tuple):
            img = tup[0]
        else:
            img = tup
            tup = ()
        if len(tup) > 1:
            title = tup[1]
        if len(tup) > 2:
            descr = tup[2]
        show_image(img, title=title, plotidx=ploti, plotcols=2, plotrows=ceil(len(images)/2))

