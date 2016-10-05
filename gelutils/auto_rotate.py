
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


def optimize_rotation_by_maximizing_cross_sections(
    image, do_invert=False, threshold=None, method="brent", solver_opts=None, bounds=None, maxiter=None, **kwargs):
    """

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
        do_invert: Image should be inverted; bands should appear white (high pixel values).
        bracket: sequence, optional
            For methods ‘brent’ and ‘golden’, bracket defines the bracketing interval
            and can either have three items (a, b, c) so that a < b < c and fun(b) < fun(a), fun(c)
            or two items a and c which are assumed to be a starting interval for a downhill bracket
            search (see bracket); it doesn’t always mean that the obtained solution will satisfy a <= x <= c.
        bounds: sequence, optional
            For method ‘bounded’, bounds is mandatory and must have two items corresponding to the optimization bounds.
        tol: float, optional. Tolerance for termination. For detailed control, use solver-specific options,
            e.g. `xtol` for brent and golden, and 'atol' for bounded.
        other options: See scipy.optimize.minimize_scalar,
            http://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize_scalar.html
    Returns:
        opt_result, calculated_values (2-tuple)
        where opt_result is a scipy.optimize.OptimizeResult object,
        and calculated_values is a list of (angle, value) results calculated
        during minimize_scalar optimization.
    """
    if maxiter:
        if solver_opts is None:
            solver_opts = {}
        solver_opts = {"maxiter": maxiter}  # "golden" doesn't seem to support maxiter
    # Set default required bounds parameter, if using bounded method:
    if method.lower() == "bounded" and bounds is None:
        bounds = (-5.0, 5.0)

    if isinstance(image, Image.Image):
        def rotate(img, angle):
            return np.array(img.rotate(angle))
    else:
        def rotate(img, angle):
            return sp.misc.imrotate(image, angle)
            # return sp.ndimage.rotate(image, angle)
        assert isinstance(image, np.ndarray)

    calculated_values = []

    def rotation_cross_section_score(angle):
        """Define closure-function to minimize angle."""
        # Invert image to make dark bands have high intensity and make new areas (from rotation) be zero:
        npimg = rotate(image, angle)
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
        bounds=bounds,
        options=solver_opts,
        **kwargs
    )

    return opt_result, calculated_values


def find_optimal_rotation(image):
    opt_result, calculated_values = optimize_rotation_by_maximizing_cross_sections(image)
    return float(opt_result.x)  # cast to python float, otherwise you get a numpy.float64

