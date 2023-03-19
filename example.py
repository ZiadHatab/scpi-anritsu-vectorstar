# standard library
import os
import json
from datetime import datetime

# install via pip
import numpy as np  # python -m pip install numpy
import matplotlib.pyplot as plt  # python -m pip install matplotlib
import skrf as rf   # python -m pip install scikit-rf

# my code
import vectorstar as vna

def write2touchstone(mat, f, folder_path, filename, par_type, settings, timestamps, skip_dir=False):
    '''
    Write 2-port data to an .s2p file.
    '''
    # mat: array of multiple iteration. index [iter, freq, rx port, tx port]
    # f: array of the frequency (common to all data)
    if not skip_dir:
        os.mkdir(folder_path + '\\' + filename)
        
    freq = rf.Frequency.from_f(f, unit='Hz')
    freq.unit = 'GHz'
    comments = {'Parameter type': par_type} | settings.copy()
    N = len(timestamps)
    for inx,(x,tms) in enumerate(zip(mat, timestamps)):
        timestamp = {'Timestamp formatted (sweep start)': str(datetime.fromtimestamp(tms['Timestamp (sweep start) [sec]']))}
        NW = rf.Network(s=x, frequency=freq, name=f'{par_type}_{inx+1:0{len(str(N))}d}', 
                   comments=json.dumps(timestamp | tms | comments, indent=4))
        NW.write_touchstone(filename=filename+f'_{par_type}_{inx+1:0{len(str(N))}d}', 
                            dir=folder_path + '\\' + filename + '\\',
                            skrf_comment=False)
        
if __name__=='__main__':
    folder_path = os.path.dirname(os.path.realpath(__file__))
    filename = 'test_data'
    os.mkdir(folder_path + '\\' + filename)
    
    f, MCA, MCB, timestamps, settings = vna.raw_sweep(address='TCPIP::169.254.63.67::INSTR', 
                                     num_sweeps=100, ifbw=1000, fnum=299,
                                     fstart=1e9, fstop=150e9,
                                     pw_stnd=-10, pw_extd=-10)
    
    write2touchstone(MCA, f, folder_path=folder_path, filename=filename, par_type='A',
                     settings=settings, timestamps=timestamps, skip_dir=True)
    write2touchstone(MCB, f, folder_path=folder_path, filename=filename, par_type='B',
                     settings=settings, timestamps=timestamps, skip_dir=True)
    
    # switch-term corrected S-parameters (the proper way)
    MCS = np.array([ [b@np.linalg.inv(a) for a,b in zip(A,B)] for A,B in zip(MCA,MCB) ])
    
    # compute the mean value of the S-parameters from all iteration
    NW = rf.Network(s=MCS.mean(axis=0), f=f, f_unit='Hz')
    NW.frequency.unit = 'GHz'
    
    # plot the S-parameters in dB
    plt.figure()
    NW.plot_s_db()

    plt.show()