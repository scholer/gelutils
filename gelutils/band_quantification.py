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
# from scipy import cluster
# from scipy.cluster import hierarchy
# from scipy.cluster.hierarchy import fcluster, fclusterdata, linkage
from scipy.cluster.hierarchy import fclusterdata
# from scipy.cluster.hierarchy import median, average  # various standard linkage calls
from collections import Counter, defaultdict, OrderedDict
from pprint import pprint
from pandas import DataFrame

from scipy.signal import convolve2d  # 2d convolution, convolve2d(in1, in2)
from scipy.signal import savgol_filter

from scipy.ndimage import convolve  # multi-dimensional convolve(input, kernel, ...)
from scipy.ndimage import gaussian_gradient_magnitude
from scipy.ndimage import gaussian_filter
from scipy.ndimage import gaussian_laplace
from scipy.ndimage import median_filter
from scipy.ndimage import minimum_filter
from scipy.ndimage import percentile_filter

from scipy.ndimage.morphology import grey_opening

from skimage import morphology
from skimage.morphology import opening
from skimage.morphology.selem import disk, diamond, rectangle, square

from skimage.feature import peak_local_max


from .plot_utils import show_image, show_plot


def draw_rectangle(img, center, width, height=None, val=0, border=0, border_val=None, center_val=None):
    if height is None:
        height = width
    if border:
        if border_val is None:
            border_val = np.max(img)
        # hmm...
        img[center[0]-height//2-border:center[0]+height//2+border+1,
            center[1]-width//2-border:center[1]+width//2+border+1] = border_val # row, col
    img[center[0]-height//2:center[0]+height//2+1,
        center[1]-width//2:center[1]+width//2+1] = val # row, col
    if center_val:
        img[center] = center_val
    return img


def subtract_row_col_percentile(img, percentile=20, row_window=10, col_window=30,
                                show_plots=False, show_data=False, verbose=0,
                                filters=None, window_length=17, polyorder=2):
    """
    window_size: row_height, col_width
    window_length must be odd
    """
    if filters is None:
        filters = ()
    elif isinstance(filters, type(savgol_filter)):
        filters = (filters,)

    print("img.shape:", img.shape)
    org_min, org_max = np.min(img), np.max(img)
    # subtract global min
    img = img - org_min
    ploti = 0
    global_max = np.max(img)  # global_min should always be 0
    global_mean = np.mean(img)
    global_median = np.median(img)
    global_10percentile = np.percentile(img, 10)
    # img = opened = opening(img, selem=np.ones(3, 29))
    # 20-percentile seems like a good background level:

    data = []
    # First do column-wise subtraction to remove smears:
    column_percentiles = np.percentile(img, percentile, axis=0)  # [row, col], axis=0 means along all rows
    data.append(('column_percentiles', column_percentiles))
    for filter_1d in filters:
        column_percentiles = filter_1d(column_percentiles, window_length=window_length, polyorder=polyorder)
        column_percentiles = np.clip(column_percentiles, 0, column_percentiles.max())
        data.append((filter_1d.__name__+"_col", column_percentiles))
#     print("column_percentiles.shape:", column_percentiles.shape)
    column_background = column_percentiles.reshape(1, column_percentiles.size)
#     print("column_background.shape:", column_background.shape)
    column_background = np.vstack([column_background for _ in range(img.shape[0])])  # shape = (rows, cols)
#     print("column_background.shape:", column_background.shape)
#     ploti = show_image(column_background, plotidx=ploti, clim=(0, 255))

    # clip to avoid negative values:
    img = np.clip(img - column_background, 0, global_max)
    if show_plots:
        ploti = show_image(img, title="column-subtracted", plotidx=ploti) #, clim=(0, 255))

    # Then subtract row-wise:
    row_percentiles = np.percentile(img, percentile, axis=1)  # [row, col], axis=0 means along all rows
    data.append(('row_percentiles', row_percentiles))
#     print("row_percentiles.shape:", row_percentiles.shape)
    row_percentiles = row_percentiles.reshape(row_percentiles.size, 1)
#     print("row_percentiles.shape:", row_percentiles.shape)
    row_percentiles = np.hstack([row_percentiles for _ in range(img.shape[1])])  # shape = (rows, cols)
#     print("row_percentiles.shape:", row_percentiles.shape)
#     ploti = show_image(row_percentiles, plotidx=ploti, clim=(0, 255))

    for filter_1d in filters:
        row_percentiles = filter_1d(row_percentiles, window_length=window_length, polyorder=polyorder)
        row_percentiles = np.clip(row_percentiles, 0, row_percentiles.max())
        data.append((filter_1d.__name__+"_row", row_percentiles))

    img = np.clip(img - row_percentiles, 0, global_max)
#     if show_plots:
#         ploti = show_image(img, title="row-subtracted", plotidx=ploti) #, clim=(0, 255))

    ploti = 0

#     fig = pyplot.figure(figsize=(9, 4))  # width, height // unlike [row, col]
#     pyplot.subplot(121)
#     pyplot.plot(column_percentiles)
#     pyplot.subplot(122)
#     pyplot.plot(row_percentiles)
    if show_data:
        for title, vals in data:
            ploti = show_plot(vals, title=title, plotidx=ploti)

    return img


def ellipse_binary(size, dtype=int):
    """Make an ellipse-shaped binary structuring element / mask.
    Similar to skimage.morphology.selem.disk() function, but for elliptical rather than just circular.
    See also disk, diamond, rectangle, square in skimage.morphology.selem module.

    :param size: int or 2-tuple of (height, width)
    :return: 2d np array / matrix of shape = size.

    Notes:
        The general formula describing an ellipse with the center at the origin is:
            (x/a)^2 + (y/b)^2 == 1

        If a == b, the expression reduces to:
            x^2/a^2 + y^2/a^2 = 1  <=>  x^2 + y^2 == a^2, that is a is the radius.

        In our case the ellipse is not at the origin, but we can simply translate from index-coordinates
        to a coordinate system where the array's midpoint is at the origin:
            y, x = row - mid_y, col - mid_y

        Since (mid_y, mix_x) is same as (b, a), we get:
            ((x-a)/a)^2 + ((y-b)/b)^2 == 1
    """
    if isinstance(size, int):
        size = (size, size)
    assert all(val % 2 == 1 for val in size)

    selem = np.ones(size, dtype=dtype)
    b, a = [val//2 for val in size]  # midpoint AND radius
    for row, col in np.ndindex(*selem.shape):
        selem[row, col] = ((col-a)/a)**2 + ((row-b)/b)**2 <= 1
    return selem
    # selem = ellipse_gray(size=size, dtype=float, only_positive=False) >= 0
    # if dtype is None or dtype is np.bool:
    #     return selem
    # else:
    #     return selem.astype(dtype)


def ellipse_gray(size, dtype=float, only_positive=True, invert=False):
    """

    :param size: int or 2-tuple of (height, width)
    :return:

    """
    if isinstance(size, int):
        size = (size, size)
    assert all(val % 2 == 1 for val in size)

    selem = np.ones(size, dtype=dtype)
    b, a = [val//2 for val in size]  # midpoint AND radius
    for row, col in np.ndindex(*selem.shape):
        selem[row, col] = 1 - (((col-a)/a)**2 + ((row-b)/b)**2)
    if invert:
        selem = -selem
    if only_positive:
        return selem * (selem > 0)
    else:
        return selem


def rolling_minimum_background(img, size=(31, 51), kernel=None,
                               geometry='rectangular', topography='flat',
                               percentile=0):
    """
    Instead of calculating the resulting image, just calculate the background and apply with
        img -= rolling_minimum_background(img)

    That way you can apply any amount of pre-filters without complex logic:
        img -= rolling_minimum_background(gaussian_filter(img, sigma=2))

    Notes:
        This doesn't work well with images with sharp boundaries, e.g. the edge of a gel.
        For best result, apply AFTER opening() and col+row leveling.

    Args:
        img:
        size: int or 2-tuple with (height, width),
                     should be higher than the thickest band and wider than the widest smear. Square is usually OK.
        kernel: specify kernel / footprint / structuring element manually.
        geometry:
        topography:
        percentile: Use percentile_filter with this percentile instead of minimum_filter (equivalent to percentile=0)

    Returns:
        background image

    """
    if kernel is None:
        if isinstance(size, int):
            size = (size, size)
        if geometry in ('round', 'disk', 'ellipse'):
            # multiply with round binary kernel with ones round/elliptical shape.
            kernel = ellipse_binary(size)
        elif geometry == 'rectangular' or geometry is None:
            kernel = np.ones(size)
        if topography == 'ball':
            # topography generally doesn't work because ndimage filters takes boolean footprints.
            # I could probalby do it with a generic filter, or by some other means.
            pass

    if percentile:
        # percentile_filter; footprint must be boolean array; size=(n,m) is equivalent to footprint=np.ones((n,m))
        background = percentile_filter(img, percentile=percentile, footprint=kernel)
    else:
        background = minimum_filter(img, footprint=kernel)

    return background


def subtract_global_percentile(img, percentile):
    """Reference function, how to globally subtract a value for which a percentile of the population is lower.
    Should generally be applied early to have any effect.
    """
    bg_val = np.percentile(img, percentile)  # percentile returns float
    if isinstance(img[0, 0], np.integer):
        bg_val = np.int(bg_val)
    img -= bg_val
    img = np.clip(img, 0, None)  # using amax=None is equivalent to amax=img.max()
    return img


def apply_and_save(func, img, title, history, history_as_str=True):
    funcname = func.__name__
    if history_as_str:
        history = "%s(%s)" % (func.__name__, history)
    else:
        history = (history, func.__name__)
    img = func(img)
    return img, title, history


def find_peaks(img, band_shape=(3, 25), show_images=False, save_images=False):
    """

    :param img:
    :param band_shape:  (height, width) akak (y, x)
    :param show_images:
    :param save_images:
    :return:
    """

    # Fixed: peaks are shifted, probably because opening() makes a shift from the structuring element.
    # Edit, no it is the convolution that does it...
    #
    img_org = img
    img = img.astype('f')  # cast to float, otherwise all calculations become inaccurate

    images = []
    band_selem = np.ones((3, 29))

    ploti = 0  # start at zero, and show_image will deal with it.
    if show_images:
        ploti = show_image(img, title="original", plotidx=ploti)

    title = "original"
    descr = "img"  # aka "history"
    images.append((img, title, descr))

    # #
    # # opening - small:
    # title, descr = "opening-3x21", "opening(%s)" % descr
    # print(title)
    # opened = opening(img, selem=np.ones((3, 21)))
    # # images.append((img, title, descr))
    # if show_images:
    #     ploti = show_image(opened, title=title, plotidx=ploti)
    #
    # #
    # # opening - medium:
    # title, descr = "opening-3x25", "opening(%s)" % descr
    # print(title)
    # opened = opening(img, selem=np.ones((3, 25)))
    # # images.append((img, title, descr))
    # if show_images:
    #     ploti = show_image(opened, title=title, plotidx=ploti)
    #
    #
    # opening - larger:
    title, descr = "opening-3x23", "opening(%s)" % descr
    print(title)
    img = opened1 = opening(img, selem=np.ones((3, 23)))
    images.append((img, title, descr))
    if show_images:
        ploti = show_image(img, title=title, plotidx=ploti)

    #
    # subtract global percentile:
    title = "subtract_global_percentile"
    descr = "%s(%s)" % (title, descr)
    print(title)
    img = minus_global_pct_bg = subtract_global_percentile(img, percentile=30)
    images.append((img, title, descr))
    if show_images:
        ploti = show_image(img, title=title, plotidx=ploti)



    #
    # rolling-minimum background subtraction with large ellipse:
    title = "rolling_5percentile_bg_el"
    descr = "%s(%s)" % (title, descr)
    print(title)
    rol_min_el = rolling_minimum_background(gaussian_filter(img, sigma=2), percentile=5,
                                             size=(71, 71),  # height, width (should be odd integers)
                                             geometry='ellipse')
    if show_images:
        ploti = show_image(rol_min_el, title=title, plotidx=ploti, clim_percentile=99.9)
    # subtract the background:
    title = "minus-rol_min_el"
    descr = "%s(%s)" % (title, descr)
    print(title)
    img = np.clip(img - rol_min_el, 0, None)  # remember to clip at zero
    images.append((img, title, descr))
    if show_images:
        ploti = show_image(img, title=title, plotidx=ploti)

    #
    # rolling-minimum background subtraction
    title = "rolling_5percentile_bg"
    descr = "%s(%s)" % (title, descr)
    print(title)
    rol_min_bg = rolling_minimum_background(gaussian_filter(img, sigma=2), percentile=5)
    if show_images:
        ploti = show_image(rol_min_bg, title=title, plotidx=ploti, clim_percentile=99.9)
    # subtract the background:
    title = "minus-rol_min_bg"
    descr = "%s(%s)" % (title, descr)
    print(title)
    img = np.clip(img - rol_min_bg, 0, None)  # remember to clip at zero
    images.append((img, title, descr))
    if show_images:
        ploti = show_image(img, title=title, plotidx=ploti)
    print("np.all(rol_min_bg == rol_min_el):", np.all(rol_min_bg == rol_min_el))

    # #
    # # subtract_row_col_percentile background subtraction:
    # title = "subtract_row_col_percentile"
    # descr = "%s(%s)" % (title, descr)
    # print(title)
    # img = background_subtracted_rcp = subtract_row_col_percentile(
    #     img, percentile=30, filters=savgol_filter, window_length=11, polyorder=1
    # )
    # images.append((img, title, descr))
    # if show_images:
    #     ploti = show_image(img, title=title, plotidx=ploti)

    #
    # opening, again:
    title, descr = "opening-%sx%s" % band_shape, "opening(%s)" % descr
    print(title)
    img = opened2 = opening(img, selem=np.ones(band_shape))
    images.append((img, title, descr))
    if show_images:
        ploti = show_image(img, title=title, plotidx=ploti)

    #
    # convolve:
    # default mode='full' will shift output, use mode='same' to prevent shifting
    title, descr = "convolved", "convolved(%s)" % descr
    print(title)
    img = convolved = convolve2d(img, band_selem/band_selem.sum(), mode='same')
    images.append((img, title, descr))
    if show_images:
        ploti = show_image(img, title=title, plotidx=ploti)

    #
    # low-percentile filter to narrow the bands:
    # (don't apply further openings or band-shape specific convolutions after narrowing the bands!)
    size = (3, 21)
    title = "pct_filtered-%sx%s" % size
    descr = "%s(%s)" % (title, descr)
    print(title)
    img = pct_filtered = percentile_filter(img, percentile=10, size=size)
    images.append((img, title, descr))
    if show_images:
        ploti = show_image(img, title=title, plotidx=ploti)

    #
    # gaussian:
    title, descr = "gaussian_filter", "gaussian_filter(%s)" % descr
    print(title)
    img = gaussianed = gaussian_filter(img, sigma=1)
    images.append((img, title, descr))
    # if show_images:
    #     ploti = show_image(img, title="gaussianed", plotidx=ploti)

    # Peaks!
    print("Finding peaks...")
    peak_pos = peak_local_max(img,
                              min_distance=10,
                              # threshold_abs=3,
                              # threshold_rel=0.01  # values must be 0.01 * maximum_value
                             )
    print("peak_pos.shape", peak_pos.shape)

    #
    # Draw peaks on a copy of the image:
    img = img.copy()  # otherwise we will write on convolved
    for pos in peak_pos:
        draw_rectangle(img, pos, width=2, val=255, border=0, center_val=None)
    ploti = show_image(img, title="peaks", plotidx=ploti)

    #
    # Other visualizations:
    ggm_filtered = gaussian_gradient_magnitude(convolved, sigma=1.0)
    ploti = show_image(ggm_filtered, title="gaussian_gradient_magnitude",
                       plotidx=ploti, clim=(0, np.percentile(ggm_filtered, 99.9)))

    title, descr = "glaplace of convolved", "laplace of convolved"
    # laplaced = laplace(convolved)
    laplaced = gaussian_laplace(convolved, sigma=2)
    ploti = show_image(laplaced, title=title, plotidx=ploti,
                       cmap="gray_r",
                       clim_percentile=(1, 99))

    lggm = laplaced*(ggm_filtered-3)
    ploti = show_image(lggm, title="laplaced*(ggm_filtered-3)", plotidx=ploti,
                       cmap="gray_r",
                       clim_percentile=(1, 99))

    title, descr = "glaplace of opened1", "laplace of opened1"
    # laplaced = laplace(convolved)
    laplaced = gaussian_laplace(opened1, sigma=2)
    ploti = show_image(laplaced, title=title, plotidx=ploti,
                       cmap="gray_r",
                       clim_percentile=(10, 90))

    if save_images:
        return peak_pos, images
    else:
        return peak_pos


def filter_pos_in_area(pos, area):
    """

    :param peak_pos:  (n,2) array
    :param area:
    :return:
    """
    xmin, xmax, ymin, ymax = area
    y, x = pos[:, 0], pos[:, 1]
    # use &/bitwise_and, not python's builtin and-operator:
    return pos[(y >= ymin) & (y <= ymax) & (x >= xmin) & (x <= xmax)]


def printarr(v, name):
    print("%s.shape: %s" % (name, v.shape))
    print(v[:30])
    if len(v) > 30:
        print("... (%s more entries in %s)" % (len(v) - 30, name))


def cluster_peaks_by_lane(peak_pos, hdist=8.0, return_sorted=True):
    """
    :param peak_pos:
    :param hdist:
    :param return_sorted:
    :return:

    Refs:
        http://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.fclusterdata.html
        http://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.fcluster.html
        http://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html
        https://web.archive.org/web/20100619134310/http://www.plantbio.ohiou.edu/epb/instruct/multivariate/Week7Lectures.PDF

    Linkage methods:
        single linkage - produces "chains"
        complete linkage - produces "sperical" clusters
        intermediate linkage -
    Other clustering methods:
        UPGMA -
        WPGMA -
        UPGMC -
        WPGMC -
        K-means - cluster into exactly K number of clusters

    """

    hdist = float(hdist)  # ensure float/numeric input
    if hdist is None:
        hdist = 8.0
    xpos = np.array([[pos[1]] for pos in peak_pos])
    # printarr(xpos, "xpos")

    # maybe add a little bit of y-position to the mix?
    # xpos = np.array([[pos[1], pos[0]/100] for pos in peak_pos])

    lane_clusters = fclusterdata(xpos, t=0.2)  # fclusterdata(X, t) is for N observations each with M variables.
    lane_clusters = fclusterdata(xpos, t=hdist, criterion='distance', metric='euclidean', depth=2, method='single')
    # lane_clusters = linkage(xpos)  # defaults to 'single', 'euclidean'

    # group lane-clustered peaks: lane_id -> array of peak pos.
    peaks_by_lane = defaultdict(list)
    for lane_id, pos in zip(lane_clusters, peak_pos):
        peaks_by_lane[lane_id].append(list(pos))
    # convert
    for lane_id in peaks_by_lane:
        peaks_by_lane[lane_id] = np.array(peaks_by_lane[lane_id])

    # pprint(peaks_by_lane)
    if return_sorted:
        # sort by mean x-position (indexing as [y, x] aka [row, col])
        peaks_by_lane = OrderedDict(sorted(peaks_by_lane.items(), key=lambda kv: kv[1][:, 1].mean()))
    # pprint(list(peaks_by_lane.values()))

    return peaks_by_lane


def cluster_lane_peaks_to_bands(lane_peaks, vdist=5.0, img=None):
    vdist = float(vdist)  # ensure float/numeric input
    # Special case, lane only has a single peak, nothing to cluster:
    if len(lane_peaks) < 2:
        this_lane_bands_peaks = {0: lane_peaks}  # ensure we have a dict of peaks
        # print("lane_id %s has only %s peaks" % (lane_id, len(lane_peaks)))
    else:
        # sort by row (y-coordinate):
        # print("sorting bands in lane_id %s by y position (pos[0])" % lane_id)
        band_clusters = fclusterdata(lane_peaks, t=vdist, criterion='distance', metric='euclidean', depth=2, method='single')
        # lane_band_cluster_ids[lane_id] = band_clusters
        # print("lane_id", lane_id)
        # print("lane_peaks", lane_peaks)
        # print("band_clusters", band_clusters)
        # group, method (1) using defaultdict:
        # cannot use dict.fromkeys, because it only takes static default values, not types/functions.
        this_lane_bands_peaks = defaultdict(list)
        for band_id, pos in zip(band_clusters, lane_peaks):
            this_lane_bands_peaks[band_id].append(pos)
        # alternative grouping methods: (2) zip, sort, then groupby;
        # print("this_lane_bands_peaks", this_lane_bands_peaks)
        # convert to nparray and take mean:
    # convert the list of peaks for each band to ndarray:
    for band_id in this_lane_bands_peaks:
        this_lane_bands_peaks[band_id] = np.array(this_lane_bands_peaks[band_id])
    return this_lane_bands_peaks


def bands_peaks_weighted_centers(bands_peaks, img=None):

    lane_bands_centers = OrderedDict()
    for band_id, band_peaks in bands_peaks.items():
        # lane_bands_centers[lane_id] = bands_peaks_center(band_peaks)
        # print("band %s peaks:" % band_id, bands_peaks[band_id], sep="\n")
        # band_peaks = np.array(bands_peaks[band_id])
        if img is None:
            # No image, so treat all the band's peaks equally:
            lane_bands_centers[band_id] = np.mean(band_peaks, axis=0)
        else:
            # cast pos to tuple before using it as index to get expected img[(rowidx, colidx)] behaviour
            band_peak_vals = np.array([img[tuple(pos)] for pos in band_peaks])
            # print("band_peak_vals: %s" % (band_peak_vals.shape,), band_peak_vals, sep="\n")
            max_band_peak_val = band_peak_vals.max()
            # remove peaks with values significantly lower than the max of the bands cluster:
            band_peak_mask = band_peak_vals > (0.95 * max_band_peak_val)
            band_peak_weights = band_peak_vals*band_peak_mask
            # print("band_peak_weights: %s" % (band_peak_weights.shape,), band_peak_weights, sep="\n")
            # use band_peak_vals and band_peak_mask to calculate weighted average for the band's center:
            lane_bands_centers[band_id] = np.average(band_peaks, axis=0, weights=band_peak_weights)
        # print("bands_peaks[%s]: " % band_id, bands_peaks[band_id])
        assert lane_bands_centers[band_id].size == 2

    return OrderedDict(sorted(lane_bands_centers.items(), key=lambda kv: kv[1][0]))


def cluster_peaks_to_lanes_bands(peak_pos, hdist=8.0, vdist=5.0, img=None):
    """
    sp.cluster.hierarchy.fclusterdata(
            X, t, criterion=criterion, metric=metric, depth=depth, method=method, R=R)
    """

    peaks_by_lane = cluster_peaks_by_lane(peak_pos, hdist=hdist, return_sorted=True)
    # We use OrderedDict to preserve lane order (from left to right)
    lanes_bands_peaks = OrderedDict()
    lanes_bands_centers = OrderedDict()
    for lane_id, lane_peaks in peaks_by_lane.items():
        lanes_bands_peaks[lane_id] = cluster_lane_peaks_to_bands(lane_peaks, vdist=vdist, img=img)
        lanes_bands_centers[lane_id] = bands_peaks_weighted_centers(lanes_bands_peaks[lane_id])
    return peaks_by_lane, lanes_bands_peaks, lanes_bands_centers


def flatten_band_centers_to_dataframe(lanes_bands_centers, product_bands_dist=5.0):
    """

    Args:
        lanes_bands_centers: band centers, grouped by [lane_id][band_id]

    Returns:
        A flattened DataFrame, one row for each band, with rows:
            lane_id, band_id, product_id, etc.
    """
    df = DataFrame(
        [
            {
                'lane_id': lane_id,
                'band_id': band_id,
                'center': band_center,
                'ypos': band_center[0],  # [row, col] aka [y, x]
                'xpos': band_center[1]
            }
            for lane_id, lane_bands in lanes_bands_centers.items()
            for band_id, band_center in lane_bands.items()
        ],
        columns=('lane_id', 'band_id', 'xpos', 'ypos', 'center')
    )
    if product_bands_dist:
        add_band_product_id_annotation(df, vdist=product_bands_dist)
    return df


def cluster_bands_by_size(peak_pos):
    pass


def add_band_product_id_annotation(df, vdist=5.0):

    # maybe use fcluster instead of fclusterdata? - nope, fcluster(Z) takes a pre-calculated linkage matrix Z.
    # manually calculate Z?
    # ypos = [[ypos] for df.]
    # ypos = df.ypos[:, np.newaxis]
    product_clusters_ids = fclusterdata(
        df.ypos[:, np.newaxis], t=vdist,
        criterion='distance', metric='euclidean', depth=2, method='single'
    )
    df['product_id'] = product_clusters_ids


