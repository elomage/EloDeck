#!/usr/bin/python3

# EloDeck: MIDI pad controller - launcher.
# Configure the hardware and commands in config.yaml
#
# Author: Leo Selavo

import sys
import os
import time
import yaml
import subprocess
from threading import Timer

import re
import pyudev

# MIDI controller device path
midi_device_path = None

# Configuration file keys
k_actions = "actions"
k_pots = "pots"
k_buttons = "buttons"
k_sliders = "sliders"
k_up = "up"


# Response to errors (configuretion etc)
def problem(msg):
    print( "ERROR: {}".format(msg))
    sys.exit(1)


# Write bytes to MIDI device
def midi_write(data):
    global midi_device_path
    if midi_device_path is None:
        return
    with open(midi_device_path, "wb") as dev:
        try:
            print("Writing to {}: {}".format(midi_device_path, data))
            dev.write(data)
        except Exception as e:
            print("Unexpected write error: {}".format(sys.exc_info()[0]))

# Send a command to MIDI
def midi_send(cmd, note, velo):
    data = bytes([cmd, note, velo])
    midi_write(data)


# Assign actions from the configuration
stat_up, stat_dn, stat_rot = [0,0,0]

def assign_actions(config):
    global stat_up, stat_dn, stat_rot
    global xtmini_pots, xtmini_keys
    xtmini_pots = {}
    xtmini_keys = {}
    dev = config["midi"]
    stat_up  = dev["status_up"]
    stat_dn  = dev["status_dn"]
    stat_rot = dev["status_rot"]
    key_modes = dev["modes"]
    
    if k_actions in config:
        for k,v in config[k_actions].items():
            if len(k)<2:
                problem("Configuration error: key {} too short".format(k))
            if len(k)==2:   # The only or the first row:col controller
                k += "11"
            if len(k)==3:   # Defaults to the first row
                k = k[:2] + "1" + k[2]
            mm = k[0]
            cc = k[1]
            row = int(k[2], 16)-1
            col = int(k[3], 16)-1
            if row<0 or col<0:
                problem("Configuration: row or col must start from 1 for key {}".format(k))
            # Convert ID to number
            modes = [mm]
            if mm=="X":   # Any mode
                modes = key_modes
            elif not mm in key_modes:
                problem("Incorrect mode for control key {}".format(k))

            for md in modes:
                try:
                    if cc=="B":   # Button
                        idx = dev[md][k_buttons][row][col]
                        xtmini_keys[idx] = v
                    elif cc=="P": # Rotary / Pot
                        idx = dev[md][k_pots][row][col]
                        xtmini_pots[idx] = v
                    elif cc=="S": # Slider
                        idx = dev[md][k_sliders][row][col]
                        xtmini_pots[idx] = v
                except IndexError:
                    problem("Configuration error: check row or col for key {}".format(k))
                

# Read the defice config
def load_config(config_file_name) :
    with open( config_file_name ) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    assign_actions(config)
    return config


# Change volume. Limit the update rate.
timer_delay = 0.2
volume_mute = False
last_volume_set=999
last_volume_requested=0
volume_timer_running = False


def set_volume_mute_toggle():
    global volume_mute
    volume_mute = not volume_mute
    if volume_mute:
        subprocess.call(["amixer", "-D", "pulse", "sset", "Master", "mute"])
    else:
        subprocess.call(["amixer", "-D", "pulse", "sset", "Master", "unmute"])

def set_volume_now(volume):
    if (volume > 100) or (volume < 0): return
    subprocess.call(["amixer", "-D", "pulse", "sset", "Master", str(volume)+"%"])


def volume_timer_fired():
    global volume_timer_running, last_volume_set, last_volume_requested
    if last_volume_requested != last_volume_set :
        last_volume_set = last_volume_requested
        set_volume_now(last_volume_requested)
    volume_timer_running = False


def set_volume(volume):
    global volume_timer_running, last_volume_set, last_volume_requested
    last_volume_requested = int(volume)
    if not volume_timer_running:
        volume_timer_running = True
        set_volume_now(last_volume_requested)
        t = Timer(timer_delay, volume_timer_fired)
        t.start()


# Rate-limited rotary/pot value set

# For rotary/pot commands
# configuration must specify values: min, max, step=1, placeholder={} 
# and the command with the placeholder that will be replaced with the current value.
# Parameter rate=0.2 defines time in seconds how often can we call this

rotval_timer_delay=0.2
flag_rotval_timer_running={}
last_rotval_set=99999
last_rotval_requested=-1


def set_rotval_now(val, act):
    if (val > 100) or (val < 0): return
    cmd = act["cmd"]
    placeholder = str(act.get("placeholder", "{}"))
    vmin = int(act.get("min", 0))
    vmax = int(act.get("max", 100))
    step = int(act.get("step", 1))
    print_txt = act.get("print", None)

    val = int( vmin + (vmax-vmin) * val / 100 )
    val = int( val - val % step ) 
    cmd = cmd.replace(placeholder, str(val))

    if print_txt != None:
        print_txt = print_txt.replace(placeholder, str(val))
        print(print_txt)

    cmd = cmd.split(" ")
    p = subprocess.Popen(cmd)
    

def rotval_timer_fired(key, act):
    global flag_rotval_timer_running, last_rotval_set, last_rotval_requested
    if last_rotval_set != last_rotval_requested:
        last_rotval_set = last_rotval_requested
        set_rotval_now(last_rotval_requested, act)
    flag_rotval_timer_running[key] = False
        

# Set rotval value, use rate limiting to one call/0.2s or less
def set_rotval(key, val, act):
    global flag_rotval_timer_running, last_rotval_set, last_rotval_requested
    last_rotval_requested = int(val)
    if not flag_rotval_timer_running.get(key, False):
        flag_rotval_timer_running[key] = True
        last_rotval_set = last_rotval_requested
        set_rotval_now(last_rotval_requested, act)
        delay = act.get("rate", rotval_timer_delay)
        t = Timer(delay, rotval_timer_fired, [key, act])
        t.start()


# Respond to a button event
def button_action(cmd):
    if type(cmd) == dict:
        act = cmd
        cmd = act.get("cmd", None)
        print_txt = act.get("print", None)
        if print_txt != None:
            print(print_txt)

        midicmd = act.get("midi", None)
        if midicmd != None:
            if type(midicmd)==str:
                midicmd = bytearray.fromhex(midicmd)
            if type(midicmd)==list:
                midicmd = bytearray(midicmd)
            midi_write(midicmd)

        if cmd is None:
            return

    cmd = cmd.strip()
    if cmd=="Exit":
        print("Stop")
        sys.exit(0)
    cmd = cmd.split(" ")
    p = subprocess.Popen(cmd)

        
def button_down(k):
    cmd = xtmini_keys.get(k,None)
    if cmd is None:
        print("Unassigned button: {}".format(k))
        return
    button_action(cmd)

def button_up(k):
    cmd = xtmini_keys.get(k,None)
    if cmd is None or type(cmd)!=dict or not k_up in cmd:
        return
    button_action(cmd[k_up])

def rotary(k, val):
#     print("Rot {}, value {}".format(k, val))
    act = xtmini_pots.get(k, None)
    if act is None : return
    if act=="Volume":
        set_volume( val*100/127 )
    else:
        set_rotval(k, val*100/127, act )


# Parse the MIDI data stream
def parse_midi(x):
    l = len(x)
    if l<3 : return
    stat = x[0]
    if stat<128: return
    if stat==stat_dn: 
        button_down(x[1])
    if stat==stat_up: 
        button_up(x[1])
    elif stat==stat_rot:
        rotary(x[1], x[2])


# ID 1397:00b3 BEHRINGER International GmbH USB2.0 HUB
def is_my_midi_device(device):
    # dev_path0 = device.get('DEVPATH')
    return device.get('ID_VENDOR_ID') == '00b3' and device.get('ID_MODEL_ID') == '1397'


def is_midi_device(dev_path):
    if dev_path is None: 
        return False
    if re.match(u"^/dev/midi[0-9]+$", dev_path):
        return True
    if re.match(u"^/dev/midi$", dev_path):
        return True
    return False


# Return path to a MIDI device when found.
def wait_for_midi():
    context = pyudev.Context()

    #  Check for existing midi devices
    for device in context.list_devices():
        dev_path = device.device_node
        if is_midi_device(dev_path) :
            print('Found {}'.format(dev_path))
            return dev_path

    # Monitor for new midi devices as added
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='sound')
    for action, device in monitor:
        if action != "add": 
            continue
        dev_path = device.device_node
        if is_midi_device(dev_path) :
            print('Just added: {}'.format(dev_path))
            return dev_path


def midi_listen(dev_path):
    global midi_device_path

    while True:
        if dev_path!=None and os.path.exists(dev_path):
            midi_device_path = dev_path   # Save for writing to the same controller

            with open(dev_path, "rb") as f:
                while True:
                    try:
                        x = f.read(3)
                    except OSError as e:
                        if e.errno == 19:  # Lost the device. Unplugged?
                            print("MIDI device lost.")
                            break
                        else:
                            raise e
                            break
                    except KeyboardInterrupt:
                        print('Interrupted')
                        sys.exit(1)
                    except: #handle other exceptions such as attribute errors
                        print("Unexpected read error:", sys.exc_info()[0])
                        break
                    else:
                        parse_midi(x)
        else:
            print("Looking for a new MIDI device...")
            dev_path = wait_for_midi()


#==========================================
#  Main entry point from CLI
#  TODO: parameter - midi device type, if more than one connected
#==========================================
def main():
    argc = len(sys.argv)
    if argc < 2:
        print("Expected arguments: path to config file and possibly path to MIDI device.")
        print("Example:  prog ./config.yaml /dev/midi4")
        return
    
    config_path = sys.argv[1]
    dev_path = None
    if argc > 2: dev_path = sys.argv[2]
    print( "Configuration: {}".format(config_path) )
    if dev_path != None:
        print( "Device: {}".format(dev_path))

    # Load config
    config = load_config(config_path)    
    
    # Start the loop
    midi_listen(dev_path)

#==========================================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted at main()')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
