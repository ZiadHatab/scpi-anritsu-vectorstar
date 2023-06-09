# Python SCPI for Anritsu Vectorstar

Python SCPI script to collect complex-valued trace data from an Anritsu VectorStar VNA. It also includes an additional function for collecting raw (uncalibrated) wave parameters from the 2-port Anritsu VectorStar VNA.

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

## Code snippet

With the code below you can collect complex-valued traces on the screen without changing any settings. Simply define the channel and number of sweeps to collect.

```python
    import numpy as np
    import vectorstar as vna # my code

    frequencies, measurements, trace_definitions = vna.read_traces(address='GPIB0::6::INSTR', num_sweeps=10, channels=[1])
    # trace_definitions gives the definition of the collected data in the same order as stored in the 'measurements' variable
    # the variable frequencies holds the frequency grid for each selected channel.
```

Here, you can collect all eight wave parameters when the VNA operates as a two-port system. Additionally, you can change the stimulus settings. After collecting the data, the VNA's settings return to whatever they were before running the script. Currently only data collection from channel 1 is supported. Alternatively, you set the wave parameters manually on the screen and use the function `vna.read_traces()` to read the traces from any channel.

```python
    import numpy as np
    import vectorstar as vna # my code

    f, MCA, MCB, timestamps, settings = vna.raw_waves_sweep(address='GPIB0::6::INSTR', 
                                                      num_sweeps=10, ifbw=1000, fnum=299, 
                                                      fstart=1e9, fstop=150e9, 
                                                      pw_stnd=-10, pw_extd=-10)
    # MCA contain all 4 a-waves
    # MCB contain all 4 b-waves
```

## Computing S-parameters from wave parameters

In the example file [`example.py`](https://github.com/ZiadHatab/scpi-anritsu-vectorstar/blob/main/example.py) the measurements are wave parameters stored in `.s2p` touchstone file type. For each measurement sweep there are two files associated to it. The file with the suffix `_A_xx.s2p` contain the a-waves and the file with suffix `_B_xx.s2p` contain the b-waves.

As `.s2p` files store 4 complex-valued parameters, the formate for the a-waves and b-waves are given as below:

$$
\mathbf{A} = \begin{bmatrix} a_{11} & a_{12}\\\ a_{21} & a_{22}\end{bmatrix}; \qquad \mathbf{B} = \begin{bmatrix} b_{11} & b_{12}\\\ b_{21} & b_{22}\end{bmatrix},
$$

where the indices _ij_ for both wave parameters indicate the _i_-th receiver, when excited by the _j_-th port. Remember, there are two ports, and two receivers for each wave parameter.

The S-parameters are calculated as follows:

$$
\mathbf{S} = \mathbf{B}\mathbf{A}^{-1}
$$

<!-- EOF -->