"""
This file generates simple spice cards for simulation.  There are
various functions that can be be used to generate stimulus for other
simulations as well.
"""

import tech
import debug
import subprocess
import os
import sys
import numpy as np
from globals import OPTS

vdd_voltage = tech.spice["supply_voltage"]
gnd_voltage = tech.spice["gnd_voltage"]
vdd_name = tech.spice["vdd_name"]
gnd_name = tech.spice["gnd_name"]
pmos_name = tech.spice["pmos_name"]
nmos_name = tech.spice["nmos_name"]
tx_width = tech.spice["minwidth_tx"]
tx_length = tech.spice["channel"]

def inst_sram(stim_file, abits, dbits, sram_name):
    """ Function to instatiate an SRAM subckt. """
    stim_file.write("Xsram ")
    for i in range(dbits):
        stim_file.write("D[{0}] ".format(i))
    for i in range(abits):
        stim_file.write("A[{0}] ".format(i))
    for i in tech.spice["control_signals"]:
        stim_file.write("{0} ".format(i))
    stim_file.write("{0} ".format(tech.spice["clk"]))
    stim_file.write("{0} {1} ".format(vdd_name, gnd_name))
    stim_file.write("{0}\n".format(sram_name))


def inst_model(stim_file, pins, model_name):
    """ Function to instantiate a generic model with a set of pins """
    stim_file.write("X{0} ".format(model_name))
    for pin in pins:
        stim_file.write("{0} ".format(pin))
    stim_file.write("{0}\n".format(model_name))


def create_inverter(stim_file, size=1, beta=2.5):
    """ Generates inverter for the top level signals (only for sim purposes) """
    stim_file.write(".SUBCKT test_inv in out {0} {1}\n".format(vdd_name, gnd_name))
    stim_file.write("mpinv out in {0} {0} {1} w={2}u l={3}u\n".format(vdd_name,
                                                                      pmos_name,
                                                                      beta * size * tx_width,
                                                                      tx_length))
    stim_file.write("mninv out in {0} {0} {1} w={2}u l={3}u\n".format(gnd_name,
                                                                      nmos_name,
                                                                      size * tx_width,
                                                                      tx_length))
    stim_file.write(".ENDS test_inv\n")


def create_buffer(stim_file, buffer_name, size=[1,3], beta=2.5):
    """
    Generates buffer for top level signals (only for sim
    purposes). Size is pair for PMOS, NMOS width multiple. 
    """

    stim_file.write(".SUBCKT test_{2} in out {0} {1}\n".format(vdd_name, 
                                                                   gnd_name,
                                                                   buffer_name))
    stim_file.write("mpinv1 out_inv in {0} {0} {1} w={2}u l={3}u\n".format(vdd_name,
                                                                           pmos_name,
                                                                           beta * size[0] * tx_width,
                                                                           tx_length))
    stim_file.write("mninv1 out_inv in {0} {0} {1} w={2}u l={3}u\n".format(gnd_name,
                                                                           nmos_name,
                                                                           size[0] * tx_width,
                                                                           tx_length))
    stim_file.write("mpinv2 out out_inv {0} {0} {1} w={2}u l={3}u\n".format(vdd_name,
                                                                                pmos_name,
                                                                                beta * size[1] * tx_width,
                                                                                tx_length))
    stim_file.write("mninv2 out out_inv {0} {0} {1} w={2}u l={3}u\n".format(gnd_name,
                                                                                nmos_name,
                                                                                size[1] * tx_width,
                                                                                tx_length))
    stim_file.write(".ENDS test_{0}\n\n".format(buffer_name))


def inst_buffer(stim_file, buffer_name, signal_list):
    """ Adds buffers to each top level signal that is in signal_list (only for sim purposes) """
    for signal in signal_list:
        stim_file.write("X{0}_buffer {0} {0}_buf {1} {2} test_{3}\n".format(signal,
                                                                            "test"+vdd_name,
                                                                            "test"+gnd_name,
                                                                            buffer_name))


def inst_inverter(stim_file, signal_list):
    """ Adds inv for each signal that needs its inverted version (only for sim purposes) """
    for signal in signal_list:
        stim_file.write("X{0}_inv {0} {0}_inv {1} {2} test_inv\n".format(signal,
                                                                         "test"+vdd_name,
                                                                         "test"+gnd_name))


def inst_accesstx(stim_file, dbits):
    """ Adds transmission gate for inputs to data-bus (only for sim purposes) """
    stim_file.write("* Tx Pin-list: Drain Gate Source Body\n")
    for i in range(dbits):
        pmos_access_string="mp{0} DATA[{0}] acc_en D[{0}] {1} {2} w={3}u l={4}u\n"
        stim_file.write(pmos_access_string.format(i,
                                                  "test"+vdd_name,
                                                  pmos_name,
                                                  2 * tx_width,
                                                  tx_length))
        nmos_access_string="mn{0} DATA[{0}] acc_en_inv D[{0}] {1} {2} w={3}u l={4}u\n"
        stim_file.write(nmos_access_string.format(i,
                                                  "test"+gnd_name,
                                                  nmos_name,
                                                  2 * tx_width,
                                                  tx_length))

def gen_pulse(stim_file, sig_name, v1=gnd_voltage, v2=vdd_voltage, offset=0, period=1, t_rise=0, t_fall=0):
    """ 
    Generates a periodic signal with 50% duty cycle and slew rates. Period is measured
    from 50% to 50%.
    """
    stim_file.write("* PULSE: period={0}\n".format(period))
    pulse_string="V{0} {0} 0 PULSE ({1} {2} {3}n {4}n {5}n {6}n {7}n)\n"
    stim_file.write(pulse_string.format(sig_name, 
                                        v1,
                                        v2,
                                        offset,
                                        t_rise,
                                        t_fall, 
                                        0.5*period-0.5*t_rise-0.5*t_fall,
                                        period))


def gen_pwl(stim_file, sig_name, clk_times, data_values, period, slew, setup):
    """ 
    Generate a PWL stimulus given a signal name and data values at each period.
    Automatically creates slews and ensures each data occurs a setup before the clock
    edge. The first clk_time should be 0 and is the initial time that corresponds
    to the initial value.
    """
    # the initial value is not a clock time
    debug.check(len(clk_times)==len(data_values),"Clock and data value lengths don't match.")
    
    # shift signal times earlier for setup time
    times = np.array(clk_times) - setup*period
    values = np.array(data_values) * vdd_voltage
    half_slew = 0.5 * slew
    stim_file.write("* (time, data): {}\n".format(zip(clk_times, data_values)))
    stim_file.write("V{0} {0} 0 PWL (0n {1}v ".format(sig_name, values[0]))
    for i in range(1,len(times)):
        stim_file.write("{0}n {1}v {2}n {3}v ".format(times[i]-half_slew,
                                                      values[i-1],
                                                      times[i]+half_slew,
                                                      values[i]))
    stim_file.write(")\n")

def gen_constant(stim_file, sig_name, v_val):
    """ Generates a constant signal with reference voltage and the voltage value """
    stim_file.write("V{0} {0} 0 DC {1}\n".format(sig_name, v_val))

def get_inverse_voltage(value):
    if value > 0.5*vdd_voltage:
        return gnd_voltage
    elif value <= 0.5*vdd_voltage:
        return vdd_voltage
    else:
        debug.error("Invalid value to get an inverse of: {0}".format(value))

def get_inverse_value(value):
    if value > 0.5:
        return 0
    elif value <= 0.5:
        return 1
    else:
        debug.error("Invalid value to get an inverse of: {0}".format(value))
        

def gen_meas_delay(stim_file, meas_name, trig_name, targ_name, trig_val, targ_val, trig_dir, targ_dir, trig_td, targ_td):
    """ Creates the .meas statement for the measurement of delay """
    measure_string=".meas tran {0} TRIG v({1}) VAL={2} {3}=1 TD={4}n TARG v({5}) VAL={6} {7}=1 TD={8}n\n\n"
    stim_file.write(measure_string.format(meas_name,
                                          trig_name,
                                          trig_val,
                                          trig_dir,
                                          trig_td,
                                          targ_name,
                                          targ_val,
                                          targ_dir,
                                          targ_td))
    
def gen_meas_power(stim_file, meas_name, t_initial, t_final):
    """ Creates the .meas statement for the measurement of avg power """
    # power mea cmd is different in different spice:
    if OPTS.spice_name == "hspice":
        power_exp = "power"
    else:
        power_exp = "par('(-1*v(" + str(vdd_name) + ")*I(v" + str(vdd_name) + "))')"
    stim_file.write(".meas tran {0} avg {1} from={2}n to={3}n\n\n".format(meas_name,
                                                                        power_exp,
                                                                        t_initial,
                                                                        t_final))
    
def write_control(stim_file, end_time):
    """ Write the control cards to run and end the simulation """
    # UIC is needed for ngspice to converge
    stim_file.write(".TRAN 5p {0}n UIC\n".format(end_time))
    if OPTS.spice_name == "ngspice":
        # ngspice sometimes has convergence problems if not using gear method
        # which is more accurate, but slower than the default trapezoid method
        # Do not remove this or it may not converge due to some "pa_00" nodes
        # unless you figure out what these are.
        stim_file.write(".OPTIONS POST=1 RUNLVL=4 PROBE method=gear\n")
    else:
        stim_file.write(".OPTIONS POST=1 RUNLVL=4 PROBE\n")

    # create plots for all signals
    stim_file.write("* probe is used for hspice/xa, while plot is used in ngspice\n")
    if OPTS.debug_level>0:
        if OPTS.spice_name in ["hspice","xa"]:
            stim_file.write(".probe V(*)\n")
        else:
            stim_file.write(".plot V(*)\n")
    else:
        stim_file.write("*.probe V(*)\n")
        stim_file.write("*.plot V(*)\n")

    # end the stimulus file
    stim_file.write(".end\n\n")


def write_include(stim_file, models):
    """Writes include statements, inputs are lists of model files"""
    for item in list(models):
        if os.path.isfile(item):
            stim_file.write(".include \"{0}\"\n".format(item))
        else:
            debug.error("Could not find spice model: {0}\nSet SPICE_MODEL_DIR to over-ride path.\n".format(item))


def write_supply(stim_file):
    """ Writes supply voltage statements """
    stim_file.write("V{0} {0} 0.0 {1}\n".format(vdd_name, vdd_voltage))
    stim_file.write("V{0} {0} 0.0 {1}\n".format(gnd_name, gnd_voltage))
    # This is for the test power supply
    stim_file.write("V{0} {0} 0.0 {1}\n".format("test"+vdd_name, vdd_voltage))
    stim_file.write("V{0} {0} 0.0 {1}\n".format("test"+gnd_name, gnd_voltage))


def run_sim():
    """ Run hspice in batch mode and output rawfile to parse. """
    temp_stim = "{0}stim.sp".format(OPTS.openram_temp)
    import datetime
    start_time = datetime.datetime.now()
    debug.check(OPTS.spice_exe!="","No spice simulator has been found.")
    
    if OPTS.spice_name == "xa":
        # Output the xa configurations here. FIXME: Move this to write it once.
        xa_cfg = open("{}xa.cfg".format(OPTS.openram_temp), "w")
        xa_cfg.write("set_sim_level -level 7\n")
        xa_cfg.write("set_powernet_level 7 -node vdd\n")
        xa_cfg.close()
        cmd = "{0} {1} -c {2}xa.cfg -o {2}xa -mt 2".format(OPTS.spice_exe,
                                               temp_stim,
                                               OPTS.openram_temp)
        valid_retcode=0
    elif OPTS.spice_name == "hspice":
        # TODO: Should make multithreading parameter a configuration option
        cmd = "{0} -mt 2 -i {1} -o {2}timing".format(OPTS.spice_exe,
                                                     temp_stim,
                                                     OPTS.openram_temp)
        valid_retcode=0
    else:
        cmd = "{0} -b -o {2}timing.lis {1}".format(OPTS.spice_exe,
                                                   temp_stim,
                                                   OPTS.openram_temp)
        # for some reason, ngspice-25 returns 1 when it only has acceptable warnings
        valid_retcode=1

        
    spice_stdout = open("{0}spice_stdout.log".format(OPTS.openram_temp), 'w')
    spice_stderr = open("{0}spice_stderr.log".format(OPTS.openram_temp), 'w')

    debug.info(3, cmd)
    retcode = subprocess.call(cmd, stdout=spice_stdout, stderr=spice_stderr, shell=True)

    spice_stdout.close()
    spice_stderr.close()
    
    if (retcode > valid_retcode):
        debug.error("Spice simulation error: " + cmd, -1)
    else:
        end_time = datetime.datetime.now()
        delta_time = round((end_time-start_time).total_seconds(),1)
        debug.info(2,"*** Spice: {} seconds".format(delta_time))

    
