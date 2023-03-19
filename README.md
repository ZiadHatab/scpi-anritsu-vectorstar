# Python SCPI for Anritsu Vectorstar

SCPI python script for collecting raw (uncalibrated) wave parameters from the 2-port Anritsu VectorStar VNA.

The script has been tested exclusively on the MS4647B VNA (10 MHz to 70 GHz) and in extended mode on the ME7838D VNA (up to 145 GHz). The implemented SCPI commands are taken from the file [__Anritsu Programming Manual - VectorStar MS464xB Series Microwave Vector Network Analyzer.pdf__](https://www.anritsu.com/en-us/test-measurement/support/downloads?model=MS4640B%20Series).

## Code requirement

You need two packages installed in your python environment [`pyvisa`](https://pyvisa.readthedocs.io/en/latest/index.html) and [`numpy`](https://numpy.org/install/), both which can be installed as follows:

```powershell
python -m pip install -U pyvisa numpy
```

You also need to install a VISA [backend](https://pyvisa.readthedocs.io/en/latest/introduction/getting.html):

```powershell
python -m pip install -U pyvisa-py
```

You basically load the file [`vectorstar.py`](https://github.com/ZiadHatab/scpi-anritsu-vectorstar/blob/main/vectorstar.py) in your main script and start collecting data. For the example file [`example.py`](https://github.com/ZiadHatab/scpi-anritsu-vectorstar/blob/main/example.py), please check its dependency directly in the file.

## Sample code

```python
    import numpy as np
    import vectorstar as vna # my code

    f, MCA, MCB, timestamps, settings = vna.raw_sweep(address='TCPIP::169.254.63.67::INSTR', 
                                                      num_sweeps=100, ifbw=1000, fnum=299, 
                                                      fstart=1e9, fstop=150e9, 
                                                      pw_stnd=-10, pw_extd=-10)
```

## Computing S-parameters from wave parameters

In the example file [`example.py`](https://github.com/ZiadHatab/scpi-anritsu-vectorstar/blob/main/example.py) the measurements are wave parameters stored in `.s2p` touchstone file type. For each measurement sweep there are two files associated to it. The file with the suffix `_A_xx.s2p` contain the a-waves and the file with suffix `_B_xx.s2p` contain the b-waves.

As `.s2p` files store 4 complex-valued parameters, the formate for the a-waves and b-waves are given as below:

$$
\mathbf{A} = \begin{bmatrix} a_{11} & a_{12}\\ a_{21} & a_{22}\end{bmatrix}; \qquad \mathbf{B} = \begin{bmatrix} b_{11} & b_{12}\\ b_{21} & b_{22}\end{bmatrix},
$$
where the indices _ij_ for both wave parameters indicate the _i_-th receiver, when excited by the _j_-th port. Remember, there are two ports, and two receivers for each wave parameter.

The S-parameters are calculated as follows:
$$
\mathbf{S} = \mathbf{B}\mathbf{A}^{-1}
$$

$$
\ell = \sum_{i}^{N}(y_i - \hat{y}_i)^2 - ||w||_2^2
$$

<!-- EOF -->