#!/usr/bin/python

import sys
import os
import subprocess
import time
from machinekit import launcher
from subprocess import call

configurationlist = {
    'cramps_lineardelta' : ['BeagleBone Black (PRU) with CRAMPS cape and lineardelta kinematics', 'rostock', 'cramps2_cape'],
    'bebopr_pp_lineardelta' : ['BeagleBone Black (PRU) with BeBoPr++ cape and Pepper board and lineardelta kinematics', 'bebopr_pp_pepper_lineardelta', 'bebopr_pp'],
    'add other configurations' : ['Add other configurations here', 'name of the config', 'name of the hardware.bbio file']
}


def check_input():
    if len(sys.argv) == 2:
        # get the hardware type from the command line
        configuration = str(sys.argv[1])
        #return configuration
    else:
        print("usage: %s <configuration>" % sys.argv[0])
        exit(1)
    if not configuration in configurationlist:
	print("USAGE: %s <configuration>" % sys.argv[0])
	print("Argument \"%s\" is not in configuration list") % configuration
	print("")
	print "{:<15} {:<20}".format('Argument','Description')
	print("----------------------------------------------")
	for argument, description in configurationlist.iteritems():
		print "{:<15} {:<20}".format(argument, description[0])
	exit(1)
    return configuration

def check_mklaucher():
    try:
        subprocess.check_output(['pgrep', 'mklauncher'])
        return True
    except subprocess.CalledProcessError:
        return False

os.chdir(os.path.dirname(os.path.realpath(__file__)))

try:
    configuration = check_input();
    # there's a valid configuration in the list, otherwise we wouldn't
    # be here. So return the 3rd array member which depicts the hardware
    configuration_array = configurationlist.get(configuration)
    
    launcher.check_installation()
    launcher.cleanup_session()
    launcher.register_exit_handler()  # needs to executed after HAL files
    # bebopr capes are not universal overlay
    bbio_file = configuration_array[2]
    if not (bbio_file=='bebopr_pp'):
        launcher.load_bbio_file('%s.bbio' % bbio_file)
    else:
        call(['bash', 'setup.bebopr_pp.sh'])
    nc_path = os.path.expanduser('~/nc_files')
    if not os.path.exists(nc_path):
        os.mkdir(nc_path)

    if not check_mklaucher():  # start mklauncher if not running to make things easier
        launcher.start_process('mklauncher .')

    config_file = configuration_array[1]
    launcher.start_process("configserver -n %s ~/Machineface" % config_file)
    launcher.start_process('machinekit %s.ini' % config_file)
    while True:
        launcher.check_processes()
        time.sleep(1)
except subprocess.CalledProcessError:
    launcher.end_session()
    sys.exit(1)

sys.exit(0)
