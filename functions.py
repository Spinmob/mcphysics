import numpy as _n
from scipy.special import wofz as _wofz
from scipy.special import erf  as _erf
import scipy.stats as _stats


# Code speedup
_ROOT2   = 2.0**0.5 
_ROOT2PI = (2.0*_n.pi)**0.5


def gaussian(x, sigma=1):
    """
    Gaussian probability distribution normalized so that the area is 1, and 
    the standard deviation is sigma. Specifically:
        
        exp(-0.5*(x/sigma)**2)/(sigma*sqrt(2*pi))
    
    Parameters
    ----------
    x:
        Distance from the center of the peak.
    sigma:
        Standard deviation of the Gaussian distribution.
    """
    return _n.exp(-0.5*(x/sigma)**2)/(sigma*_ROOT2PI)

def gaussian_cdf(x, sigma=1):
    """
    Cumulative distribution function of a Gaussian distribution having area
    1 and standard deviation sigme (i.e., the running integral of gaussian(x,sigma)).
    
    Parameters
    ----------
    x:
        Distance from the center of the peak.
    sigma:
        Standard deviation of the underlying Gaussian distribution.
    
    """
    return 0.5*_erf(x/(_ROOT2*sigma)) + 0.5


def em_gaussian(x, sigma=1, tau=1):
    """
    Returns an exponentially modified Gaussian (a convolution of an exponential
    cutoff at x=0 and Gaussian) having standard deviation sigma and exponential
    decay length tau. This function is normalized to have unity area.

    Parameters
    ----------
    x:
        Distance from the center of the peak.
    sigma:
        Standard deviation of Gaussian ~ exp(-x**2/(2*sigma**2))
    tau:
        Length scale of exponential ~ exp(x/tau). Positive tau skews the peak
        to higher values and negative tau skews to lower values.
    """
    t = abs(tau)
    s = sigma

    if tau >= 0: return 0.5/t*_n.exp(-0.5*( x/s)**2)*erfcx((s/t - x/s)*0.5**0.5)
    else:        return 0.5/t*_n.exp(-0.5*(-x/s)**2)*erfcx((s/t + x/s)*0.5**0.5)

def voigt(x, sigma=1, gamma=1):
    """
    Returns a Voigt function (a convolution of a Lorentzian and Gaussian)
    centered at x=0 with Gaussian standard deviation sigma and Lorentzian
    half-width gamma. The function is normalized to have unity area.

    Parameters
    ----------
    x:
        Distance from center of peak.
    sigma = 1:
        Standard deviation of Gaussian ~ exp(-x**2/(2*sigma**2))
    gamma = 1:
        Halfwidth of Lorentzian ~ 1/(1+x**2/gamma**2)
    """
    return _n.real(_wofz((x + 1j*gamma)/sigma/_ROOT2)) / sigma / (2*_n.pi)**0.5

def reduced_chi2(x, dof):
    """
    Returns the reduced chi^2 probability density function for the specified
    degrees of freedom (dof).

    Parameters
    ----------
    x
        Value of reduced chi^2.

    dof
        Degrees of freedom.
    """
    return dof*_stats.chi2.pdf(x*dof,dof)

