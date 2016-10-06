#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright 2016 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
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

"""


Refs:
* http://matplotlib.org/api/image_api.html
* http://matplotlib.org/api/pyplot_api.html
*

Other resources:
* http://www.openmicroscopy.org/, https://github.com/openmicroscopy
* http://www.losonczylab.org/sima, https://github.com/losonczylab/sima
* https://en.wikibooks.org/wiki/Software_Tools_For_Molecular_Microscopy
* Magni, https://github.com/SIP-AAU/Magni, http://magni.readthedocs.io/

"""
from math import log
from PIL import Image
from PIL import ImageOps
import numpy as np
import scipy as sp
from scipy.optimize import minimize_scalar
# from scipy import ndimage
# from scipy.misc import imrotate


def apply_threshold(image, threshold):
    if threshold == "auto":
        image = ImageOps.autocontrast(image)
    else:
        npimg = np.array(image)
        if threshold < 1:
            # Fractional, either "dark for this percentile" or dark for this fraction of max.
            threshold = float(threshold * npimg.max())
        # This doesn't work...
        # image = Image.eval(image, lambda pixel: pixel if pixel < threshold else threshold)
        npimg = np.clip(npimg, 0, threshold)
        image = Image.fromarray(npimg)
    return image


def optimize_rotation_by_maximizing_cross_sections(image, rotate_func=None,
                                                   method="brent",
                                                   bracket=None, bounds=None,
                                                   solver_opts=None, maxiter=None, **kwargs):
    """Find optimal rotation for gel image such that bands and other features are aligned v/h.

    This seems to be a good function to maximize:
        log(np.sum(npimg.sum(axis=0)**2)) + log(np.sum(npimg.sum(axis=1)**2))

    Notes:
        pyplot.matshow() or pyplot.imshow() can be used to visualize image data.

        Alternatives to PIL.Image.Image.rotate that may be faster:
        * http://docs.scipy.org/doc/scipy/reference/generated/scipy.misc.imrotate.html  (similar to PIL)
        * http://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.rotate.html  (spline interpolation)
        * http://scikit-image.org/docs/dev/api/skimage.transform.html#rotate


    Args:
        image: The gel image to find optimal rotation for.
        rotate_func: Function used to rotate image.
            Must accept two arguments rotate_func(image, angle) and return a 2D numpy array as output.
            Obviously, rotate_func must be able to use the given image data structure.
            If rotate_func is None (default), then a suitable rotate function will be selected.
        method: The optimizer method to use, e.g. "brent", "golden", or "bounded".
        bracket: sequence, optional
            For methods ‘brent’ and ‘golden’, bracket defines the bracketing interval
            and can either have three items (a, b, c) so that a < b < c and fun(b) < fun(a), fun(c)
            or two items a and c which are assumed to be a starting interval for a downhill bracket
            search (see bracket); it doesn’t always mean that the obtained solution will satisfy a <= x <= c.
        bounds: sequence, optional
            For method ‘bounded’, bounds is mandatory and must have two items corresponding to the optimization bounds.
        maxiter: Specify maximum number of iterations. Can also be specified in solver_opts dict.
        solver_opts: dict with extra solver-specific arguments, e.g.:
            e.g. `xtol` for brent and golden, and 'atol' for bounded.
        kwargs: other options, see scipy.optimize.minimize_scalar
        (http://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize_scalar.html)
        e.g. `tol`: float, optional. Tolerance for termination. For detailed control, use solver-specific options,

    Returns:
        opt_result, calculated_values (2-tuple)
        where opt_result is a scipy.optimize.OptimizeResult object,
        and calculated_values is a list of (angle, value) results calculated
        during minimize_scalar optimization.
    """
    if maxiter:
        if solver_opts is None:
            solver_opts = {}
        solver_opts["maxiter"] = maxiter  # "golden" method doesn't seem to support maxiter
    # Set default required bounds parameter, if using bounded method:
    if method.lower() == "bounded" and bounds is None:
        bounds = (-5.0, 5.0)

    if rotate_func is None:
        if isinstance(image, Image.Image):
            def rotate_func(img, angle):
                return np.array(img.rotate(angle))
        else:
            def rotate_func(img, angle):
                # There are a couple of function that can be used to rotate numpy array images:
                # scipy.misc.imrotate, scipy.ndimage.rotate, and skimage.transform.rotate
                return sp.misc.imrotate(img, angle)  # I believe this just uses PIL
                # return sp.ndimage.rotate(img, angle)
            assert isinstance(image, np.ndarray)

    calculated_values = []

    def rotation_cross_section_score(angle):
        """Define closure-function to minimize angle."""
        # Invert image to make dark bands have high intensity and make new areas (from rotation) be zero:
        npimg = rotate_func(image, angle)
        # Normalize pixel values to prevent overflow:
        npimg = npimg / npimg.max()  # binary if using //, consider multiplying with 256 if you want integer operations
        sum_xsq = np.sum(npimg.sum(axis=0)**2)
        sum_ysq = np.sum(npimg.sum(axis=1)**2)
        # Return negative because we are minimizing not maximizing:
        score = -(log(sum_xsq) + log(sum_ysq))
        calculated_values.append((angle, score))
        return score

    opt_result = minimize_scalar(
        rotation_cross_section_score,
        method=method,
        bounds=bounds, bracket=bracket,
        options=solver_opts,
        **kwargs
    )

    return opt_result, calculated_values


def find_optimal_rotation(image):
    opt_result, calculated_values = optimize_rotation_by_maximizing_cross_sections(image)
    return float(opt_result.x)  # cast to python float, otherwise you get a numpy.float64

