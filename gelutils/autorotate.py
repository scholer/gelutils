





def optimize_constant_interval(func, range):
    pass


def minimize_variable_interval(
        fun, startpoint, step, step_min, iteration_window_size=10,
        range_limit=None, iterations_max=1000):
    """Optimize func, find x such that fun(x) is minimal.
    OK, writing good optimizers/minimizers is hard. Please use a function from scipy.optimize instead,
    e.g. scipy.optimize.minimize_scaler:

        minimize_scaler(fun, bracket=(-1, 1), method='brent', disp=True)

    minimize_scalar:
        fun : callable
            Objective function. Scalar function, must return a scalar.
        bracket : sequence, optional
            For methods ‘brent’ and ‘golden’, bracket defines the bracketing interval and can either have three items
            (a, b, c) so that a < b < c and fun(b) < fun(a), fun(c) or two items a and c which are assumed to be a
            starting interval for a downhill bracket search (see bracket);
            it doesn’t always mean that the obtained solution will satisfy a <= x <= c.
        bounds : sequence, optional
            For method ‘bounded’, bounds is mandatory and must have two items corresponding to the optimization bounds.
        args : tuple, optional
            Extra arguments passed to the objective function.
        method : str or callable, optional
            Type of solver. Should be one of
                ‘Brent’ (see here)
                ‘Bounded’ (see here)
                ‘Golden’ (see here)
                custom - a callable object (added in version 0.14.0), see below
        tol : float, optional
            Tolerance for termination. For detailed control, use solver-specific options.
        options : dict, optional
            A dictionary of solver options. Examples:
            maxiter : int
                Maximum number of iterations to perform.
            disp : bool
                Set to True to print convergence messages.
    extra :options: for methods:
        maxiter: Maximum number of iterations to perform. (all)
        xtol:  Relative error in solution `xopt` acceptable for convergence. (brent, golden)
        disp:  Print convergence messages. (bounded)
        xatol:  Absolute error in solution `xopt` acceptable for convergence. (bonded)

    """
    if range_limit is None:
        range_limit = (startpoint - 100*step, startpoint + 100*step)

    data = []
    xvals = set()
    midpoint = startpoint
    iterations_count = 0
    while (step > step_min and iterations_count < iterations_max
           and range_limit[0] < midpoint < range_limit[1]):

        # if len(points_to_calculate) == 0:
        # lower, upper = midpoint - step*, midpoint + step*(iteration_window_size / 2 + 1)
        window_min, window_max = -iteration_window_size//2, iteration_window_size//2 + 1
        points_to_calculate = [midpoint + i * step for i in range(window_min, window_max)]
        points_to_calculate = [x for x in points_to_calculate if x not in xvals]
        if not points_to_calculate:
            print("optimize_constant_interval: points_to_calculate is empty, breaking out...")
            break
        values = [fun(x) for x in points_to_calculate]
        xvals.update(points_to_calculate)
        max_in_search_window = False
        min_value = min(values)
        data.extend(list(zip(points_to_calculate, values)))
        # min_value == values[0] or min_value == values[-1]
        while min_value == values[0] or min_value == values[-1]:
            n_boundary_calcs = 0
            if range_limit[0] < midpoint < range_limit[1]:
                print("range_limit[0] < midpoint < range_limit[1], breaking...")
                break
            # One or both end-points is also a local maxima. Expand the search range without decreasing step size.
            if min_value == values[0]:
                # Extend window to the left:
                points_to_calculate = [midpoint + i * step for i in range(
                    window_min - iteration_window_size//2, window_min)]
                points_to_calculate = [x for x in points_to_calculate if x not in xvals]
                n_boundary_calcs += len(points_to_calculate)
                window_min = window_min - iteration_window_size//2
                xvals.update(points_to_calculate)
                values = [fun(x) for x in points_to_calculate] + values
            if min_value == values[-1]:
                # Extend window to the right:
                points_to_calculate = [midpoint + i * step for i in range(
                    window_max, window_max + iteration_window_size//2+1)]
                points_to_calculate = [x for x in points_to_calculate if x not in xvals]
                n_boundary_calcs += len(points_to_calculate)
                window_max = window_max + iteration_window_size//2+1
                xvals.update(points_to_calculate)
                values = values + [fun(x) for x in points_to_calculate]
            min_value = min(values)
            if n_boundary_calcs == 0:
                print("n_boundary_calcs == 0, breaking...")
                break



