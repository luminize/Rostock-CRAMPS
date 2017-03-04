from machinekit import hal
from machinekit import rtapi as rt
from machinekit import config as c

from fdm.config import base


def hardware_read(thread):
    hal.addf('hpg.capture-position', '%s' % thread) # 'servo-thread')
    hal.addf('bb_gpio.read', 'base-thread') # 'servo-thread')


def hardware_write(thread):
    hal.addf('hpg.update', '%s' % thread) # 'servo-thread')
    hal.addf('bb_gpio.write', 'base-thread') # 'servo-thread')
    hal.addf('pepper.update', 'base-thread') # 'base-thread')

def init_hardware(thread):
    watchList = []
    # launch the setup script for bebopr hardware
    # hal.loadusr('/home/machinekit/mk-ve-configs/setup.bebopr_pp.sh', wait=True)

    # load low-level drivers
    rt.loadrt('hal_bb_gpio', output_pins='807,924,926', input_pins='808,809,810,814,817,818')
    prubin = '%s/%s' % (c.Config().EMC2_RTLIB_DIR, c.find('PRUCONF', 'PRUBIN'))
    rt.loadrt(c.find('PRUCONF', 'DRIVER'),
              pru=0, num_stepgens=5, num_pwmgens=3,
              prucode=prubin, halname='hpg')
    rt.loadrt('pepper', count=1)
    # Python user-mode HAL module to read ADC value and generate a thermostat output for PWM
    defaultThermistor = 'epcos_B57560G1104'
    hal.loadusr('hal_temp_bbb',
                name='temp',
                interval=0.05,
                filter_size=1,
                cape_board='BeBoPr',
                channels='04:%s,05:%s'
                % (c.find('HBP', 'THERMISTOR', defaultThermistor),
                   c.find('EXTRUDER_1', 'THERMISTOR', defaultThermistor)),
                wait_name='temp')
    watchList.append(['temp', 0.1])

    base.usrcomp_status('temp', 'temp-hw', thread='%s' % thread) # 'servo-thread')
    base.usrcomp_watchdog(watchList, 'estop-reset', thread='%s' % thread,
                          errorSignal='watchdog-error')


def setup_hardware(thread):
    # PWM pins
    hal.Pin('hpg.pwmgen.00.pwm_period').set(10000000)  # 100Hz
    hal.Pin('hpg.pwmgen.00.out.00.pin').set(813)
    hal.Pin('hpg.pwmgen.00.out.01.pin').set(819)
    hal.Pin('hpg.pwmgen.00.out.02.pin').set(914)
    # J2 E0 Heater PRU1.out1
    hal.Pin('hpg.pwmgen.00.out.00.enable').set(True)
    hal.Pin('hpg.pwmgen.00.out.00.value').link('e0-temp-pwm')
    # J3 FAN
    hal.Pin('hpg.pwmgen.00.out.01.enable').link('f0-pwm-enable')
    hal.Pin('hpg.pwmgen.00.out.01.value').link('f0-pwm')
    hal.Signal('f0-pwm-enable').set(True)
#    hal.Pin('hpg.pwmgen.00.out.01.enable').link('exp0-pwm-enable')
#    hal.Pin('hpg.pwmgen.00.out.01.value').link('exp0-pwm')
#    hal.Signal('exp0-pwm-enable').set(True)
    # J4 HB
    hal.Pin('hpg.pwmgen.00.out.02.enable').set(True)
    hal.Pin('hpg.pwmgen.00.out.02.value').link('hbp-temp-pwm')
    
    # GPIO
    hal.Pin('bb_gpio.p8.in-09').link('limit-0-home')   # Xmax
    hal.Pin('bb_gpio.p8.in-08').link('limit-0-min')    # Xmin
    hal.Pin('bb_gpio.p8.in-14').link('limit-1-home')   # Ymax
    hal.Pin('bb_gpio.p8.in-10').link('limit-1-min')    # Ymin
    hal.Pin('bb_gpio.p8.in-18').link('limit-2-home')   # Zmax
    hal.Pin('bb_gpio.p8.in-17').link('limit-2-min')    # Zmin

    # Adjust as needed for your switch polarity
    hal.Pin('bb_gpio.p8.in-09.invert').set(False) #Xmax = column C
    hal.Pin('bb_gpio.p8.in-08.invert').set(False) #Xmin
    hal.Pin('bb_gpio.p8.in-14.invert').set(False) #Ymax = column A
    hal.Pin('bb_gpio.p8.in-10.invert').set(False) #Ymin
    hal.Pin('bb_gpio.p8.in-18.invert').set(False) #Zmax = column B
    hal.Pin('bb_gpio.p8.in-17.invert').set(False) #Zmin

    # ADC
    hal.Pin('temp.ch-05.value').link('hbp-temp-meas')
    hal.Pin('temp.ch-04.value').link('e0-temp-meas')

    # Stepper
    hal.Pin('hpg.stepgen.00.steppin').set(812)
    hal.Pin('hpg.stepgen.00.dirpin').set(811)
    hal.Pin('hpg.stepgen.01.steppin').set(816)
    hal.Pin('hpg.stepgen.01.dirpin').set(815)
    hal.Pin('hpg.stepgen.02.steppin').set(915)
    hal.Pin('hpg.stepgen.02.dirpin').set(923)
    hal.Pin('hpg.stepgen.03.steppin').set(922)
    hal.Pin('hpg.stepgen.03.dirpin').set(921)
    hal.Pin('hpg.stepgen.04.steppin').set(918)
    hal.Pin('hpg.stepgen.04.dirpin').set(917)

    # ##################################################
    # Standard I/O - EStop, Enables, Limit Switches, Etc
    # ##################################################
    # create a signal for the estop loopback
    hal.newsig('estop-loop', hal.HAL_BIT, init=False)
    #hal.Pin('iocontrol.0.user-enable-out').link('estop-user')
    hal.Pin('iocontrol.0.user-enable-out').link('estop-loop')
    hal.Pin('iocontrol.0.emc-enable-in').link('estop-loop')
    #
    # Machine power (BeBoPr I/O-Enable)
    #
    # Link pepper component as last item in io_enable chain
    #
    # the chain is as follows:
    # sig emcmot-0-enable
    # pin    pepper.io-ena.in
    # hw        thru the pepper board
    # pin          pepper.io-ena.out
    # sig             io-enable
    # pin                 bb_gpio.p8.out-07 (enable the io)
    hal.Pin('pepper.io-ena.in').link('estop-loop')
    #hal.Pin('pepper.io-ena.in').link('estop-user')
    #hal.Pin('pepper.io-ena.in').link('emcmot-0-enable')
    hal.newsig('io-enable', hal.HAL_BIT, init=False)
    hal.Pin('pepper.io-ena.out').link('io-enable')
    hal.Pin('bb_gpio.p8.out-07').link('io-enable')
    hal.Pin('bb_gpio.p8.out-07.invert').set(True)
    # feed stepper enables to pepper component
    for n in range(0,3):
        hal.Signal('emcmot-%s-enable' % n).link('pepper.stepper-ena.%s.in' % n)
    # feed resulting enable outputs to bebopr
    hal.newsig('ena1', hal.HAL_BIT, init=False)
    hal.Pin('pepper.enable-sck.out').link('ena1')
    hal.Pin('bb_gpio.p9.out-26').link('ena1')
    hal.Pin('bb_gpio.p9.out-26.invert').set(True)
    hal.newsig('ena2', hal.HAL_BIT, init=False)
    hal.Pin('pepper.spindle-mosi.out').link('ena2')
    hal.Pin('bb_gpio.p9.out-24').link('ena2')
    hal.Pin('bb_gpio.p9.out-24.invert').set(True)
    #
    #  Set PEPPER configuration parameters
    #
    hal.Pin('pepper.no-store').set(c.find('PEPPER', 'VOLATILE'))
    hal.Pin('pepper.cycle-time').set(c.find('EMCMOT', 'BASE_PERIOD'))
    for n in range(0,3):
        hal.Pin('pepper.axis.%s.micro-step' % n).set(c.find('AXIS_%s' % n, 'MICRO_STEP'))
        hal.Pin('pepper.axis.%s.idle-current' % n).set(c.find('AXIS_%s' % n, 'IDLE_CURRENT'))
        hal.Pin('pepper.axis.%s.active-current' % n).set(c.find('AXIS_%s' % n, 'ACTIVE_CURRENT'))
        hal.Pin('pepper.axis.%s.idle-decay' % n).set(c.find('AXIS_%s' % n, 'IDLE_DECAY'))
        hal.Pin('pepper.axis.%s.active-decay' % n).set(c.find('AXIS_%s' % n, 'ACTIVE_DECAY'))
    # for extruder
    extruder_n=0
    pepper_axis=4
    hal.Pin('pepper.axis.%s.micro-step' % pepper_axis).set(c.find('EXTRUDER_%s' % extruder_n, 'MICRO_STEP'))
    hal.Pin('pepper.axis.%s.idle-current' % pepper_axis).set(c.find('EXTRUDER_%s' % extruder_n, 'IDLE_CURRENT'))
    hal.Pin('pepper.axis.%s.active-current' % pepper_axis).set(c.find('EXTRUDER_%s' % extruder_n, 'ACTIVE_CURRENT'))
    hal.Pin('pepper.axis.%s.idle-decay' % pepper_axis).set(c.find('EXTRUDER_%s' % extruder_n, 'IDLE_DECAY'))
    hal.Pin('pepper.axis.%s.active-decay' % pepper_axis).set(c.find('EXTRUDER_%s' % extruder_n, 'ACTIVE_DECAY'))


def setup_exp(name):
    hal.newsig('%s-pwm' % name, hal.HAL_FLOAT, init=0.0)
    hal.newsig('%s-pwm-enable' % name, hal.HAL_BIT, init=False)
