"""


Hey, idea - instead of trying to use fourier transformations,
just use the binary upper rowtrace to find the leftmost and rightmost wells.


"""

# pylint: disable=E1101,W0142
from PIL import Image
import numpy
np = numpy
from matplotlib import pyplot

pngimg = Image.open('RS335e_PAGE_SP-NT-staples_500V_0-100k.png')
npimg = numpy.array(pngimg)
height, width = npimg.shape
upper = npimg[0:int(height*0.1)]

# If the image is already inverted:
extrema = pngimg.getextrema()
invertvec = numpy.vectorize(lambda x: extrema[1]-x)
npimg2 = invertvec(npimg)

#imgplot = pyplot.imshow(upper)
#pyplot.show()

imgmean = npimg2.mean()

# Plot row average:
#pyplot.plot(range(npimg.shape[0]), npimg2.sum(axis=1))
# Edit, use mean()
pyplot.plot(range(npimg.shape[0]), npimg2.mean(axis=1))

#s1 = np.sum(upper, axis=0)  # axis=0 to get per-column sum.
s1 = upper.mean(axis=0) # per-column mean

# Plot column average:
pyplot.plot(range(npimg.shape[1]), npimg2.mean(axis=0))


### Find the upper part of the gel containing the wells ###

# Would it be better to make the whole gel a 1-bit binary image before calculating rowmeans?
# OTOH: Calculating the threshold for the binary might also be difficult...

# The row of pixels where we reach the bottom of the wells.
# The well bottom usually has higher pixel values than the image mean:
wellrow = next(row for row, rowmean in enumerate(npimg2.mean(axis=1)) if rowmean > imgmean)
upper = npimg2[0:int(wellrow*1.5)] # We use a little extra than just the


# Make upper binary, i.e. either above or below gel mean:
binvec = numpy.vectorize(lambda x: imgmean if x > imgmean else (imgmean*0.95 if x > imgmean*0.75 else 0))
binvec = numpy.vectorize(lambda x: imgmean if x > 0.5*imgmean else 0)
upperbin = binvec(upper)

# Plot column average:
pyplot.plot(range(upperbin.shape[1]), upperbin.mean(axis=0))












##### FFT  #######

fft = numpy.fft.rfft(upperbin.mean(axis=0)).real

# The zeroth coefficient is the average in the interval.
# However, all values are multiplied by the number of samples, N (=upperbin.mean(axis=0).size),
# so to get the actual mean you have to do:
avg = fft[0]/upperbin.mean(axis=0).size
# Since this is what we'll be using to a large extend, let's save that:
N = upperbin.mean(axis=0).size
fft_norm = np.abs(fft)/N

# If you plot
pyplot.plot(np.abs(fft)/700)
# and find the first peak (after the zeroth), this would be e.g. fft[9]
# then that means that the first harmonic has length 700/9 = 77 ?
# You can plot this with:  sin(2*pi*x*9/700)
pyplot.plot((numpy.sin(2*np.pi*np.arange(700)*9/700)+1)*imgmean/2)
# Or, more correctly:
h, amp = 9, np.abs(fft[9])/N
pyplot.plot((numpy.sin(2*np.pi*np.arange(N)*h/N))*amp)


def reconstituted_fft(fft_norm, N, cutoff=0.05, cutoffisrelative=True):
    """
    Uh, instead of using this, use np.fft.ifft(fft_norm).
    Oh, and if you have used rfft to compute fft,
    then you need to use irfft to invert.

    And by the way, the code below cannot be used if fft has been computed with rfft.
    """
    maxamp = fft_norm.max()
    if cutoffisrelative:
        cutoff = maxamp*cutoff
    filtered = [(k, amp) for k, amp in enumerate(fft_norm) if amp > cutoff]
    ks, amps = zip(*filtered)
    #ks, amps = np.array(ks), np.array(amps)
    #npfiltered = numpy.array([(k, amp) for k, amp in enumerate(fft_norm) if amp > cutoff])
    #ks = npfiltered[:, 0]
    #amps = npfiltered[:, 1]
    ks, amps = map(np.matrix, (ks, amps))
    xs = np.arange(N)
    #rec = amps*np.sin(ks.T*2*np.pi*xs/N) # Matrix multiplication will multiply and sum.
    #rec = amps*np.cos(ks.T*2*np.pi*xs/N) # Matrix multiplication will multiply and sum.
    # Above doesn't work, nor for cos.
    rec = np.abs(amps*np.exp(1j*ks.T*2*np.pi*xs/N)) # Matrix multiplication will multiply and sum.
    # Return 1-dim array, not matrix:
    return np.squeeze(np.asarray(rec))
