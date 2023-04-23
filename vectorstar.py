"""
@author: Ziad (zi.hatab@gmail.com)
Script to log raw wave-parameters measurements from Anritsu VectorStar VNA.

The SCPI commands are found on the file:
"Anritsu Programming Manual - VectorStar MS464xB Series Microwave Vector Network Analyzer.pdf"
https://www.anritsu.com/en-us/test-measurement/products/ms4640b-series
"""

import pyvisa
'''
to install pyvisa 
python -m pip install -U pyvisa

Also, you need the backend for pyvisa
python -m pip install -U pyvisa-py

You can read more from here: https://pyvisa.readthedocs.io/en/latest/introduction/getting.html
'''
import numpy as np  # python -m pip install numpy

import time
from datetime import timedelta

def raw_sweep(address='GPIB0::6::INSTR', num_sweeps=1, 
              ifbw=None, fstart=None, fstop=None, fnum=None,
              pw_stnd=None, pw_extd=None, timeout=30000):
    '''
    Parameters
    ----------
    address : str
        The address of the VNA. This can TCP (ethernet) or GPIB. 
        The default is 'GPIB0::6::INSTR'. TCP is in the form "TCPIP::169.254.63.67::INSTR".
    num_sweeps : int
        Number of sweeps. The default is 1.
    ifbw : float or None
        The IF bandwidth in Hz. If None, use the value from the VNA. 
        The default is None.
    fstart : float or None
        The start frequency in Hz. If None, use the value from the VNA. 
        The default is None.
    fstop : float or None
        The stop frequency in Hz (must be > fstart). If None, use the value from the VNA. 
        The default is None.
    fnum : int or None
        The number of frequency points in one sweep (must be >= 2). If None, use the value from the VNA. 
        The default is None.
    pw_stnd : int or None
        Set the power level of stand alone VNA (<54GHz). If None, use the value from the VNA.
        The default is None.
    pw_extd : int or None
        Set the power level of extender (>54GHz). If None, use the value from the VNA. 
        The default is None.
    timeout : int
        Max timeout of the communication link in ms. The default is 30000.

    Returns
    -------
    f : ndarray
        array containing the frequency.
    MCA : ndarray
        array containing all sweeps of the A waves. Index style [sweep,freq,rx-port,tx-port]
    MCB : ndarray
        array containing all sweeps of the B waves. Index style [sweep,freq,rx-port,tx-port].
    timestamps : list
        list of dict, where each dict contain the timestamp and duration of each sweep in seconds.
    settings : dict
        Summery of applied settings. The same as input arguments.
    '''
    
    with pyvisa.ResourceManager().open_resource(address) as vna:
        vna.DefaultBufferSize = 1600000 # Set input buffer size
        vna.timeout = timeout # Set time out duration in ms
        vna.clear()
        vna.write('LANG NATIVE')
        vna.write(':SYSTem:ERRor:CLEar')
        
        # set channel 1 to active (everything is done on channel 1)
        vna.write(':DISPlay:WINDow1:ACTivate 1')
        
        # force source 1 and 2 to be in-sync
        vna.write(':SENSe1:OFFSet:PHASe:SYNChronization ON')
                    
        # backup fab cal state and turn it off
        fabcal_state0 = vna.query_ascii_values('FRCVCALON?', converter='s', separator='\n')[0]
        vna.write('FRCVCALON 0') # turn off
        fabcal_state1 = vna.query_ascii_values('FRFCALON?', converter='s', separator='\n')[0]
        vna.write('FRFCALON 0') # turn off
        
        # backup user cal state and turn it off
        usercal_state = vna.query_ascii_values(':SENSe1:CORRection:STATe?', converter='s', separator='\n')[0]
        vna.write(':SENSe1:CORRection:STATe 0') # turn off
        
        # set source power level
        # standard device
        pw_stnd_old_p1 = vna.query_ascii_values(':SOURce1:POWer:PORT1?', converter='s', separator='\n')[0]
        pw_stnd_old_p2 = vna.query_ascii_values(':SOURce1:POWer:PORT2?', converter='s', separator='\n')[0]
        if pw_stnd is not None:
            vna.write(f':SOURce1:POWer:PORT1 {pw_stnd}')  # standard (in dbm)
            vna.write(f':SOURce1:POWer:PORT2 {pw_stnd}')  # standard (in dbm)
        # extended freq (>54GHz)
        pw_extd_old_p1 = vna.query_ascii_values(':SOURce1:MODBB:POWer:PORT1?', converter='s', separator='\n')[0]
        pw_extd_old_p2 = vna.query_ascii_values(':SOURce1:MODBB:POWer:PORT2?', converter='s', separator='\n')[0]
        if pw_extd is not None:
            vna.write(f':SOURce1:MODBB:POWer:PORT1 {pw_extd}') # extended for freq > 54GHz (in dbm)
            vna.write(f':SOURce1:MODBB:POWer:PORT2 {pw_extd}') # extended for freq > 54GHz (in dbm)
        
        # set frequency parameters
        # IF bandwidth
        ifbw_old = vna.query_ascii_values(':SENSe1:BWIDth?', converter='s', separator='\n')[0]
        if ifbw is not None:
            vna.write(f':SENSe1:BWIDth {ifbw}') # in Hz
        # start frequency
        fstart_old = vna.query_ascii_values(':SENSe1:FREQuency:STARt?', converter='s', separator='\n')[0]
        if fstart is not None:
            vna.write(f':SENSe1:FREQuency:STARt {fstart}') # in Hz      
        # stop frequency
        fstop_old = vna.query_ascii_values(':SENSe1:FREQuency:STOP?', converter='s', separator='\n')[0]
        if fstop is not None:
            vna.write(f':SENSe1:FREQuency:STOP {fstop}') # in Hz        
        # number of frequency points
        fnum_old = vna.query_ascii_values(':SENSe1:SWEep:POINt?', converter='s', separator='\n')[0]
        if fnum is not None:
            vna.write(f':SENSe1:SWEep:POINt {fnum}')

        # backup number of traces and set it to 8 (wave parameters)
        trace_state = vna.query_ascii_values(':CALCulate1:PARameter:COUNt?', converter='s', separator='\n')[0]
        vna.write(':CALCulate1:PARameter:COUNt 8')
        
        old_traces = []
        old_format = []
        new_traces = ['USR,A1,1,PORT1', 'USR,A1,1,PORT2', 'USR,A2,1,PORT1', 'USR,A2,1,PORT2',
                      'USR,B1,1,PORT1', 'USR,B1,1,PORT2', 'USR,B2,1,PORT1', 'USR,B2,1,PORT2']
        # backup traces and their format and change them to wave parameters
        for inx,trace in enumerate(new_traces):
            old_format.append(vna.query_ascii_values(f':CALCulate1:PARameter{inx+1}:FORMat?', converter='s', separator='\n')[0])
            old_traces.append(vna.query_ascii_values(f':CALCulate1:PARameter{inx+1}:DEFine?', converter='s', separator='\n')[0])
            vna.write(f':CALCulate1:PARameter{inx+1}:FORMat REIMaginary')
            vna.write(f':CALCulate1:PARameter{inx+1}:DEFine {trace}')
        
        # used settings (for logging purposes)
        settings = {
            'Power level port1 (standard) [dbm]': vna.query_ascii_values(':SOURce1:POWer:PORT1?', converter='f', separator='\n')[0],
            'Power level port2 (standard) [dbm]': vna.query_ascii_values(':SOURce1:POWer:PORT2?', converter='f', separator='\n')[0],
            'Power level port1 (extended >54GHz) [dbm]': vna.query_ascii_values(':SOURce1:MODBB:POWer:PORT1?', converter='f', separator='\n')[0],
            'Power level port2 (extended >54GHz) [dbm]': vna.query_ascii_values(':SOURce1:MODBB:POWer:PORT2?', converter='f', separator='\n')[0],
            'IF bandwidth [Hz]': vna.query_ascii_values(':SENSe1:BWIDth?', converter='f', separator='\n')[0],
            'Start frequency [Hz]': vna.query_ascii_values(':SENSe1:FREQuency:STARt?', converter='f', separator='\n')[0],
            'Stop frequency [Hz]': vna.query_ascii_values(':SENSe1:FREQuency:STOP?', converter='f', separator='\n')[0],
            'Sweep points': vna.query_ascii_values(':SENSe1:SWEep:POINt?', converter='d', separator='\n')[0],
            }
        # collect sweep measurements
        MCA = []
        MCB = []
        timestamp  = {
            'Timestamp (sweep start) [sec]': 0.0,
            'Sweep duration [sec]': 0.0
            }
        timestamps = []
        vna.write('LSB;FMB')     # set to read in binary
        tic_total = time.time()
        print('Sweep started:')
        try:
            for sweep in range(num_sweeps):  # number of sweeps
                vna.write(':SENSe:HOLD:FUNCtion HOLD') # hold sweep
                vna.write(':TRIG:SING') # run single sweep
                all_data = []
                tic = time.time()
                timestamp['Timestamp (sweep start) [sec]'] = tic
                for inx,trace in enumerate(new_traces):
                    vna.write(f':CALCulate1:PARameter{inx+1}:SELect')  # select active trace
                    data = vna.query_binary_values(':CALCulate1:DATA:FDATa?', datatype='d', container=np.array).reshape((-1,2))
                    data = data[:,0] + data[:,1]*1j   # construct back to complex number
                    all_data.append(data)
                toc = time.time()
                swp_time = toc-tic
                timestamp['Sweep duration [sec]'] = swp_time
                remain_time = timedelta(seconds=(num_sweeps-sweep-1)*swp_time)
                print(f'Sweep {sweep+1:0{len(str(num_sweeps))}d}/{num_sweeps} (sweep time {swp_time:.2f} sec) [est. remaining time: {remain_time}]')
                A = np.reshape(all_data[:4], newshape=(2,2,-1), order='F').T  # A wave parameters matrix
                B = np.reshape(all_data[4:], newshape=(2,2,-1), order='F').T  # B wave parameters matrix
                MCA.append(A)
                MCB.append(B)
                timestamps.append(timestamp.copy())
        except KeyboardInterrupt:
            print('Sweep Canceled!!!')
        toc_total = time.time()
        print(f'Total sweep time {toc_total-tic_total:.2f} sec')
        
        MCA = np.array(MCA)
        MCB = np.array(MCB)
        
        f = vna.query_binary_values(':SENSe1:FREQuency:DATA?', datatype='d', container=np.array)
        
        vna.write('FMA') # set back to read in ascii
        
        # revert stuff back
        for inx,(tr,fm) in enumerate(zip(old_traces, old_format)):
            vna.write(f':CALCulate1:PARameter{inx+1}:FORMat {fm}')
            vna.write(f':CALCulate1:PARameter{inx+1}:DEFine {tr}')
        vna.write(f':CALCulate1:PARameter:COUNt {trace_state}')
        vna.write(f':SENSe1:BWIDth {ifbw_old}')
        vna.write(f':SENSe1:FREQuency:STARt {fstart_old}')
        vna.write(f':SENSe1:FREQuency:STOP {fstop_old}')
        vna.write(f':SENSe1:SWEep:POINt {fnum_old}')
        vna.write(f':SOURce1:MODBB:POWer:PORT1 {pw_extd_old_p1}') # extended for freq > 54GHz (in dbm)
        vna.write(f':SOURce1:MODBB:POWer:PORT2 {pw_extd_old_p2}') # extended for freq > 54GHz (in dbm)
        vna.write(f':SOURce1:POWer:PORT1 {pw_stnd_old_p1}')  # standard (in dbm)
        vna.write(f':SOURce1:POWer:PORT2 {pw_stnd_old_p2}')  # standard (in dbm)
        vna.write(f':SENSe1:CORRection:STATe {usercal_state}')
        vna.write(f'FRCVCALON {fabcal_state0}')
        vna.write(f'FRFCALON {fabcal_state1}')
        
        vna.write(':SENSe:HOLD:FUNCtion CONTinuous')
        vna.write('RTL') # exit remote mode
        
        return f, MCA, MCB, timestamps, settings

if __name__=='__main__':
    pass

# EOF
