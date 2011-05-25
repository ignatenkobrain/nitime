import numpy as np
import numpy.testing as npt
import nose.tools as nt

from nitime import utils


def test_zscore():

    x = np.array([[1, 1, 3, 3],
                  [4, 4, 6, 6]])

    z = utils.zscore(x)
    yield npt.assert_equal, x.shape, z.shape

    #Default axis is -1
    yield npt.assert_equal, utils.zscore(x), np.array([[-1., -1., 1., 1.],
                                                      [-1., -1., 1., 1.]])

    #Test other axis:
    yield npt.assert_equal, utils.zscore(x, 0), np.array([[-1., -1., -1., -1.],
                                                        [1., 1., 1., 1.]])


def test_percent_change():
    x = np.array([[99, 100, 101], [4, 5, 6]])
    p = utils.percent_change(x)

    yield npt.assert_equal, x.shape, p.shape
    yield npt.assert_almost_equal, p[0, 2], 1.0

    ts = np.arange(4 * 5).reshape(4, 5)
    ax = 0
    yield npt.assert_almost_equal, utils.percent_change(ts, ax), np.array(
        [[-100., -88.23529412, -78.94736842, -71.42857143, -65.2173913],
        [-33.33333333, -29.41176471, -26.31578947, -23.80952381, -21.73913043],
        [33.33333333,   29.41176471,   26.31578947,   23.80952381, 21.73913043],
        [100., 88.23529412, 78.94736842, 71.42857143, 65.2173913]])

    ax = 1
    yield npt.assert_almost_equal, utils.percent_change(ts, ax), np.array(
        [[-100., -50., 0., 50., 100.],
         [-28.57142857, -14.28571429, 0., 14.28571429, 28.57142857],
          [-16.66666667, -8.33333333, 0., 8.33333333, 16.66666667],
          [-11.76470588, -5.88235294, 0., 5.88235294, 11.76470588]])

def test_tridi_inverse_iteration():
    import scipy.linalg as la
    from scipy.sparse import spdiags
    # set up a spectral concentration eigenvalue problem for testing
    N = 2000
    NW = 4
    K = 8
    W = float(NW) / N
    nidx = np.arange(N, dtype='d')
    ab = np.zeros((2, N), 'd')
    # store this separately for tridisolve later
    sup_diag = np.zeros((N,), 'd')
    sup_diag[:-1] = nidx[1:] * (N - nidx[1:]) / 2.
    ab[0, 1:] = sup_diag[:-1]
    ab[1] = ((N - 1 - 2 * nidx) / 2.) ** 2 * np.cos(2 * np.pi * W)
    # only calculate the highest Kmax-1 eigenvalues
    w = la.eigvals_banded(ab, select='i', select_range=(N - K, N - 1))
    w = w[::-1]
    E = np.zeros((K, N), 'd')
    t = np.linspace(0, np.pi, N)
    # make sparse tridiagonal matrix for eigenvector check
    sp_data = np.zeros((3,N), 'd')
    sp_data[0, :-1] = sup_diag[:-1]
    sp_data[1] = ab[1]
    sp_data[2, 1:] = sup_diag[:-1]
    A = spdiags(sp_data, [-1, 0, 1], N, N)
    for j in xrange(K):
        e = utils.tridi_inverse_iteration(
            ab[1], sup_diag, w[j], x0=np.sin((j+1)*t)
            )
        b = A*e
        yield (nt.assert_true,
               np.linalg.norm(np.abs(b) - np.abs(w[j]*e)) < 1e-8,
               'Inverse iteration eigenvector solution is inconsistent with '\
               'given eigenvalue'
               )

def test_debias():
    x = np.arange(64).reshape(4, 4, 4)
    x0 = utils.remove_bias(x, axis=1)
    npt.assert_equal((x0.mean(axis=1) == 0).all(), True)


def ref_crosscov(x, y, all_lags=True):
    "Computes sxy[k] = E{x[n]*y[n+k]}"
    x = utils.remove_bias(x, 0)
    y = utils.remove_bias(y, 0)
    lx, ly = len(x), len(y)
    pad_len = lx + ly - 1
    sxy = np.correlate(x, y, mode='full') / lx
    if all_lags:
        return sxy
    c_idx = pad_len / 2
    return sxy[c_idx:]


def test_crosscov():
    N = 128
    ar_seq1, _, _ = utils.ar_generator(N=N)
    ar_seq2, _, _ = utils.ar_generator(N=N)

    for all_lags in (True, False):
        sxy = utils.crosscov(ar_seq1, ar_seq2, all_lags=all_lags)
        sxy_ref = ref_crosscov(ar_seq1, ar_seq2, all_lags=all_lags)
        err = sxy_ref - sxy
        mse = np.dot(err, err) / N
        yield nt.assert_true, mse < 1e-12, \
               'Large mean square error w.r.t. reference cross covariance'


def test_autocorr():
    N = 128
    ar_seq, _, _ = utils.ar_generator(N=N)
    rxx = utils.autocorr(ar_seq)
    yield nt.assert_true, rxx[0] == rxx.max(), \
          'Zero lag autocorrelation is not maximum autocorrelation'
    rxx = utils.autocorr(ar_seq, all_lags=True)
    yield nt.assert_true, rxx[127] == rxx.max(), \
          'Zero lag autocorrelation is not maximum autocorrelation'


# Should this really be in the tests?
def plot_savings():
    import matplotlib.pyplot as pp
    from IPython.Magic import timings
    f1 = ref_crosscov
    f2 = utils.crosscov
    times1 = []
    times2 = []
    for N in map(lambda x: 2 ** x, range(8, 13)):
        a = np.random.randn(N)
        args = (a, a)
        kws = dict()
        _, t_est1 = timings(1000, f1, *args, **kws)
        _, t_est2 = timings(1000, f2, *args, **kws)
        times1.append(t_est1)
        times2.append(t_est2)
    pp.figure()
    pp.plot(range(8, 13), times1, label='tdomain crosscov')
    pp.plot(range(8, 13), times2, label='fdomain crosscov')
    pp.legend()
    pp.show()



def test_information_criteria():
    """

    Test the implementation of information criteria:

    """
    a1 = np.array([[0.9, 0],
                   [0.16, 0.8]])

    a2 = np.array([[-0.5, 0],
                  [-0.2, -0.5]])

    am = np.array([-a1, -a2])

    x_var = 1
    y_var = 0.7
    xy_cov = 0.4
    cov = np.array([[x_var, xy_cov],
                    [xy_cov, y_var]])

    N = 10
    L = 100

    z = np.empty((N, 2, L))
    nz = np.empty((N, 2, L))
    for i in xrange(N):
        z[i], nz[i] = utils.generate_mar(am, cov, L)

    AIC = []
    BIC = []
    AICc = []
    for i in range(10):
        AIC.append(utils.akaike_information_criterion(z, i))
        AICc.append(utils.akaike_information_criterion_c(z, i))
        BIC.append(utils.bayesian_information_criterion(z, i))

    # The model has order 2, so this should minimize on 2:
    #nt.assert_equal(np.argmin(AIC),2)
    #nt.assert_equal(np.argmin(AICc),2)
    nt.assert_equal(np.argmin(BIC), 2)
