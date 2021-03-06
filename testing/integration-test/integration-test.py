#!/usr/bin/env python3

import os.path
import glob
import json
import os
import subprocess
import re
import sys
import time
sys.path.append('/usr/lib/waggle/nodecontroller/wagman')

import argparse

#from wagman_client import *

#Test serial connection with XU4 and with C1+
#use minicom


wagman_device='/dev/waggle_sysmon'

coresense_device='/dev/waggle_coresense'


alphasense_device='/dev/alphasense'


# cameras, see https://github.com/waggle-sensor/waggle_image/blob/master/device_rules/wwan_modems/75-wwan-net.rules
camera_pantech_device_prefix='/dev/vzwwan'
camera_other_device_prefix='/dev/attwwan'


summary = {}


def read_file( str ):
    print("read_file: "+str)
    if not os.path.isfile(str) :
        return ""
    with open(str,'r') as file_:
        return file_.read().strip()
    return ""
    



def wagman_connected():
    return os.path.exists(wagman_device)
    
    

def coresense_connected():
    return os.path.exists(coresense_device)


def list_pantech_modems():
    return glob.glob('/dev/%s[0-9]' % (camera_pantech_device_prefix))


def list_other_modems():
    return glob.glob('/dev/%s[0-9]' % (camera_other_device_prefix))


def read_sourced_env(script):
    command = ['bash', '-c', 'source %s && env' % (script)]
    environment={}
    proc = subprocess.Popen(command, stdout = subprocess.PIPE)

    for line in proc.stdout:
        (key, _, value) = line.decode().partition("=")
        environment[key] = value.rstrip()

    proc.communicate()
    
    return environment
    

def get_command_output(command):
    
    use_shell=True
    if str(type(command))=="<class 'list'>":
        print("execute:", " ".join(command))
        use_shell=False
    else:
        print("execute:", command)
    
    result = ''
        
    try:
        result = subprocess.check_output(command, shell=use_shell)
    except Exception as e:
        print("error:", str(e))
        return ''
    
    #print("result type:", type(result))
    if (str(type(result)) == "<class 'str'>"):
            return result.rstrip()
    
    return result.decode("utf-8").rstrip()
        
    
def get_mac_address():
    environment = read_sourced_env('/usr/lib/waggle/waggle_image/scripts/detect_mac_address.sh')
    return environment['MAC_ADDRESS'] if 'MAC_ADDRESS' in environment else "NA"
    
    
def get_odroid_model():
    environment = read_sourced_env('/usr/lib/waggle/waggle_image/scripts/detect_odroid_model.sh')
    return environment['ODROID_MODEL'] if 'ODROID_MODEL' in environment else "NA"


def parse_lsusb_line(line):
    matchObj = re.match( r'Bus (\d{3}) Device (\d{3}): ID (\S{4}):(\S{4}) (.*)$', line, re.M|re.I)
    if matchObj:
        #print "matchObj.group() : ", matchObj.group()
    
        result={}
        result['bus']           =matchObj.group(1).rstrip()
        result['device']        =matchObj.group(2).rstrip()
        result['idVendor']      =matchObj.group(3).rstrip()
        result['idProduct']     =matchObj.group(4).rstrip()
        result['vendor_name']   =matchObj.group(5).rstrip()
        return result
    
    return None
    

def get_sensorboard_mac_addresses():
    import serial
    mac_addresses={}

    start = int(time.time())
    with serial.Serial('/dev/waggle_coresense', 115200, timeout=60) as ser:
        while int(time.time()) < start + 30:
            try:
                line = ser.readline().decode('utf-8').rstrip()   # read a '\n' terminated line
            #print(line)
            except:
                continue
            (sensorboard, _, mac) = line.partition('-')
            #print(sensorboard, mac)
            mac_array = mac.split(':')
            #print(mac_array)
            if len(mac_array) == 6:
                if not sensorboard.lower() in mac_addresses:
                    mac_addresses[sensorboard.lower()]={}
                    mac_addresses[sensorboard.lower()]['mac']= mac.upper()
            if 'airsense' in mac_addresses and 'chemsense' in mac_addresses and 'lightsense' in mac_addresses:
                break


    return mac_addresses


###############################################################



if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output")

    args = parser.parse_args()
    
    

    ### MAC
    summary['MAC-address']=get_mac_address()


    ### Odroid model
    summary['odroid-model']=get_odroid_model()





    ### Extension node

    # TODO: recursive call (scp and ssh) (only one recursion!!!)



    ### Coresense
    summary['coresense']={}
    summary['coresense']['connected']=coresense_connected()
    print("coresense connected:", summary['coresense']['connected'])

    # TODO: Read sensor values ?

    if summary['coresense']['connected']:
        summary['coresense']['boards'] = get_sensorboard_mac_addresses()


    ### Cameras


    # issue: found no way to map lsusb and /dev/videoX devices

    summary['cameras']={}
    summary['cameras']['list'] = []




    # known cameras:
    # 05a3:9520 -- ELP-USB500W02M-{L21,L170} ; Sorry, there's no way to distiguish lenses.
    # 05a3:9830 -- ELP-USB8MP02G-L75   Sonix_Technology_Co.__Ltd._USB_2.0_Camera_SN0001


    for vendor_product in ['05a3:9830', '05a3:9520']:
    
        # example output os lsusb: "Bus 003 Device 006: ID 05a3:9520 ARC International"
        lsusb_result=''
    
        lsusb_result = get_command_output(["lsusb", "-d", vendor_product])
        print(lsusb_result)
    
        for line in lsusb_result.split("\n"):
            #print "line:", line
            camera_obj = parse_lsusb_line(line)
            #matchObj = re.match( r'Bus (\d{3}) Device (\d{3}): ID (\S{4}):(\S{4}) (.*)$', line, re.M|re.I)
            if camera_obj:
                #print "matchObj.group() : ", matchObj.group()
        
                bus_device = "%s:%s" % (camera_obj['bus'], camera_obj['device'])
        
                for line in get_command_output(["lsusb", "-s", bus_device , "-v" ]).split("\n"):
                    #print line
                    for key in ['wHeight','wWidth']:
                        matchObj = re.match( r'.*%s\( 0\)\s+(\d+)' % (key), line, re.M|re.I)
                        if matchObj:
                            #print "got:", key, matchObj.group(1).rstrip()
                            camera_obj[key] = matchObj.group(1).rstrip()
            
                # TODO: try v4l2 to extract resolution
                # v4l2-ctl --list-formats-ext -d /dev/video? works , BUT: I do not know which video device that would be!!!
        
                print(json.dumps(camera_obj, indent=4))
                summary['cameras']['list'].append(camera_obj)
        
                # TODO:  fswebcam -r 2592x1944 --jpeg 95 -D 0 best.jpg
                # apt-get install fswebcam
       



    #TODO fswebcam and confirm image

    # list devices
    #ls -1 /dev/ | grep "^video"
    video_devices = get_command_output('ls -1 /dev/ | grep "^video"').split('\n')

    summary['video_devices']={}
    summary['video_devices']['list'] = []

    for video_device in video_devices:
        
        video_device_number = None
        matchObj = re.match( r'video(\d+)', video_device, re.M|re.I)
        if matchObj:
            video_device_number = matchObj.group(1).rstrip()
            
        if not video_device_number:
            print('video_device_number not detected: %s ' % (video_device))
            continue
            
        print("--------------------------- %s", video_device)
        command  = 'udevadm info --query=all /dev/%s | grep "P: /devices/virtual" | wc -l' % (video_device)
        print(command)
        count_virtual = get_command_output(command)
        print("\"%s\"" % (count_virtual))
        if count_virtual == "1":
            # video device is virtual
            print("virtual device")
            continue
        print("NOT virtual device")
    
        video_device_obj={}
        video_device_obj['device']='/dev/%s' % (video_device)
    
        #TODO list all possible resolutions (rightv now this just extracts the highest resolution and ignores the Pixel Format)
        # alternative to extract resolution might be: ffmpeg -f v4l2 -list_formats all -i /dev/video0
        resolutions = get_command_output('v4l2-ctl --list-formats-ext -d /dev/%s | grep -o "Size: Discrete [0-9]*x[0-9]*" | grep -o "[0-9]*x[0-9]*"' % (video_device)).split('\n')
        print(resolutions)
        max_resolution_size = 0
        max_resolution_x = 0
        max_resolution_y = 0
        for resolution in resolutions:
            print("resolution:", resolution)
            (x, _, y) = resolution.partition('x')
            try:
                size = int(x)*int(y)
            except Exception:
                print("error: could not parse resolution", resolution)
                continue
            print(x,y, size)
            if size > max_resolution_size:
                max_resolution_size = size
                max_resolution_x = x
                max_resolution_y = y
        if max_resolution_x == 0:
            continue
        print(max_resolution_x, max_resolution_y , max_resolution_size)
        video_device_obj['max_resolution_x'] = max_resolution_x
        video_device_obj['max_resolution_y'] = max_resolution_y
        video_device_obj['max_resolution_size'] = max_resolution_size
        
        
        test_file = "/tmp/best.jpg"
        fswebcam_command = 'fswebcam -r %sx%s --jpeg 95 -D %s %s' % (max_resolution_x, max_resolution_y, video_device_number, test_file)
        if fswebcam_command:
            ignore_result = get_command_output(fswebcam_command)
        
            statinfo = os.stat(test_file)
            video_device_obj['test_file_size'] = "%d" % (statinfo.st_size)
        else:
            video_device_obj['test_file_size'] = 'NA'
            
        try:
            os.remove(test_file)
        except:
            pass
            
        summary['video_devices']['list'].append(video_device_obj)
    # get highest resolution
    # v4l2-ctl --list-formats-ext -d /dev/video0

    # v4l2-ctl --list-formats-ext -d /dev/video0 | grep -o "Size: Discrete [0-9]*x[0-9]*" | grep -o "[0-9]*x[0-9]*"


    ### microphone

    summary['microphone']={}
    summary['microphone']['list'] = []
    for vendor_product in ['0d8c:013c']:
    
        for mic_line in get_command_output(['lsusb', '-d', vendor_product]).split('\n'):
            if mic_line.rstrip() == "":
                continue

            mic_obj = parse_lsusb_line(mic_line)
            if not mic_obj:
                print("could not parse: ", mic_line)
                continue
            
            bus_device = "%s:%s" % (mic_obj['bus'], mic_obj['device'])

            for line in get_command_output(["lsusb", "-s", bus_device , "-v" ]).split("\n"):
        
                for key in ['idProduct', 'idVendor']:
                    matchObj = re.match( r'.*%s\s+\d+\s+(\d+)' % (key), line, re.M|re.I)
                    if matchObj:
                        mic_obj[key] = matchObj.group(1).rstrip()
        
    
            summary['microphone']['list'].append(mic_obj)
    ### modem

    summary['modems']={}
    summary['modems']['list'] = []

    # list_pantech_modems()
    #summary['modems']['list'].append(list_other_modems())
    #print("modems:" , summary['modems']['list'])

    #summary['modems']['IMEI']='NA'


    # 1199:68a3  Sierra Wireless, Inc. MC8700 Modem
    for vendor_product in ['1199:68a3']:
        for modem_line in get_command_output(['lsusb', '-d', vendor_product]).split('\n'):
            if modem_line.rstrip() == "":
                continue
            
            modem_obj = parse_lsusb_line(modem_line)
            if not modem_obj:
                print("could not parse: ", modem_line)
                continue
        
            bus_device = "%s:%s" % (modem_obj['bus'], modem_obj['device'])

            for line in get_command_output(["lsusb", "-s", bus_device , "-v" ]).split("\n"):
        
                for key in ['iSerial', 'idProduct', 'idVendor']:
                    matchObj = re.match( r'.*%s\s+\d+\s+(\d+)' % (key), line, re.M|re.I)
                    if matchObj:
                        if key == 'iSerial':
                            modem_obj['IMEI'] = matchObj.group(1).rstrip()
                        else:
                            modem_obj[key] = matchObj.group(1).rstrip()
        
    
            summary['modems']['list'].append(modem_obj)


    ### WagMan (should be last test)
    
    summary['wagman']={}
    summary['wagman']['id']=''
    summary['wagman']['connected']=wagman_connected()

    if summary['wagman']['connected']:
        from wagman_client import *
        # wagman ID
        try:
            summary['wagman']['id'] = wagman_client(['id'])[1].strip()
        except:
            pass
    
        print("wagman_id: \"%s\"" % (summary['wagman']['id']))


        # current usage
        try:
            summary['wagman']['current_usage'] = wagman_client(['cu'])[1].strip().split('\n')
        except:
            pass

        # thermistors
        try:
            summary['wagman']['thermistors'] = wagman_client(['th'])[1].strip().split('\n')
        except:
            pass

        # environment: temperature, humidity
        environment_array=''
        try:
            environment_array=wagman_client(['env'])[1].strip().split('\n')
        except:
            pass

        summary['wagman']['environment'] = {}
        for line in environment_array:
            (key, _, value) = line.partition('=')
            if value:
                summary['wagman']['environment'][key]=value
    
    
        # test wagman reset
        try:
            wagman_client(['reset'])[1]
        except:
            pass
    
        # wait some time until wagman is responsive
        time.sleep(20)

        # this is a fake call, workaround for a bug in wagman-server
        try:
            wagman_client(['uptime'])[1].strip().split('\n')
        except:
            pass
        
        #get uptime
        uptime = -1
        try:
            uptime = int(wagman_client(['uptime'])[1].strip())
        except:
            pass

        if uptime == 0:
            summary['wagman']['reset-test']='no_time_available'
        elif uptime > 0 and uptime < 30:
            summary['wagman']['reset-test']='success'
        else:
            summary['wagman']['reset-test']='error: uptime %d seconds'% (uptime)
   




    if summary["odroid-model"] == "C":
        summary["extension_nodes"] = []


    print(json.dumps(summary, indent=4))
 
    if args.output:
        target = open(args.output, 'w')
        target.write(json.dumps(summary, indent=4))
        target.close()
        print("File %s written." % (args.output))
        



