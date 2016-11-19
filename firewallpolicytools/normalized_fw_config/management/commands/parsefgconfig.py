#!/usr/local/bin/python
"""
Author: Fahad Yousuf <fahadysf@gmail.com>
This module takes a FortiGate configuration file as input, and parses it to populate the normalized_fw_config models.
"""

import argparse
import re
import pprint
import os
import datetime
import ipaddress
import ntpath
import json

from django.core.management.base import BaseCommand, CommandError
from normalized_fw_config.models import AddressObject, \
    Device, \
    Policy, \
    CompoundServiceObject, \
    RawConfigFile, \
    ConfigVersion, \
    AddressGroup, \
    ServiceObject, \
    ServiceGroup

pp = pprint.PrettyPrinter(indent=2)

def pprintobj(objname, obj):
    print('%s: ' % objname)
    pp.pprint(obj)

def populate_addressobjs(dev, addressobjdict, options):
    for objname in addressobjdict.keys():
        """
        Create the Address Objects
        """
        addressobj, created = AddressObject.objects.get_or_create(name=objname, device=dev)
        obj = addressobjdict[objname]
        addressobj.name = objname
        addressobj.device = dev
        # Check type and create correct AddressObject
        if 'type' in obj:
            if obj['type'] == 'fqdn':
                addressobj.type = 'fqdn'
                addressobj.fqdn = obj['fqdn']
            if obj['type'] == 'iprange':
                addressobj.type = 'range4'
                addressobj.start_ip = obj['start-ip']
                addressobj.end_ip = obj['end-ip']
        elif 'subnet' in obj:
            addressobj.start_ip, netmask = obj['subnet'].split(' ')
            prefixlen = ipaddress.IPv4Network('0.0.0.0/%s' % netmask).prefixlen
            if prefixlen == 32:
                addressobj.type = 'ip4'
            else:
                addressobj.type = 'net4'
                addressobj.prefixlen = prefixlen
        if 'description' in obj:
            addressobj.description = obj['description']
        # Handle the special case "all" object
        if objname == 'all':
            addressobj.type = 'net4'
            addressobj.start_ip = '0.0.0.0'
            addressobj.prefixlen = 0
            if options['d'] == 'n':
                addressobj.save()
            else:
                print("Object not saved")
                addressobj.delete()
        elif addressobj.start_ip or addressobj.fqdn:
            if options['d'] == 'n':
                addressobj.save()
            else:
                print("Object not saved")
                addressobj.delete()

def populate_addrgrpobjects(dev, addrgrpdict, options):
    for objname in addrgrpdict.keys():
        """
        Create the Address Group Objects
        """
        addrgrpobject, created = AddressGroup.objects.get_or_create(name=objname, device=dev)
        obj = addrgrpdict[objname]
        addrgrpobject.name = objname
        addrgrpobject.device = dev
        members = obj['member'].split(" ")
        for m in members:
            m = m.strip('"')
            try:
                addrobj = AddressObject.objects.get(name=m, device=dev)
                addrgrpobject.members.add(addrobj)
            except:
                raise
        if options['d'] == 'n':
            addrgrpobject.save()
        else:
            print("Object not saved")
            addrgrpobject.delete()

def populate_serviceobjects(dev, serviceobjdict, options):
    for objname in serviceobjdict.keys():
        """
        Create the Service Objects
        """
        # By default FortiGate Service Objects are UDP+TCP+SCTP with multiple port-ranges per protocol included
        # We can check if the service is having multiple ranges with different protocols and create a Compound Service
        # Group

        obj = serviceobjdict[objname]
        objkeys = list(obj.keys())

        try:
            #Make compund service object if there are multiple portranges in the service
            compserv, created = CompoundServiceObject.objects.get_or_create(name=objname, device=dev)
            if 'comment' in obj.keys():
                compserv.description = obj['comment']
            for k in objkeys:
                # Handle TCP and UDP Services
                if k == 'tcp-portrange' or k == 'udp-portrange':
                    #Format of objects created for compound service groups is
                    # proto-dstportlow<-dstporthigh-src-portlow-srcporthigh>
                    ranges = (obj[k].split(' '))
                    for range in ranges:
                        portrangename = k[0:3] + '-'
                        srcrange = None
                        dstrange = None
                        dstlow = None
                        dsthigh = None
                        srclow = None
                        srchigh = None
                        if ':' in range:
                            dstrange, srcrange = range.split(':')
                            if dstrange != None:
                                if '-' in dstrange:
                                    dstlow,dsthigh = dstrange.split('-')
                                    dstlow = int(dstlow)
                                    dsthigh = int(dsthigh)
                                else:
                                    dstlow = int(dstrange)
                            if srcrange != None:
                                if '-' in srcrange:
                                    srclow,srchigh = srcrange.split('-')
                                    srclow = int(srclow)
                                    srchigh = int(srchigh)
                                else:
                                    srclow = int(srcrange)
                        elif '-' in range:
                            dstlow, dsthigh = range.split('-')
                            dstlow = int(dstlow)
                            dsthigh = int(dsthigh)
                        else:
                            dstlow = int(range)
                        portrangename += str(dstlow)
                        if dsthigh:
                            portrangename +='-'+str(dsthigh)
                        if srclow:
                            portrangename += ':' + str(srclow)
                        if srchigh:
                            portrangename += '-' + str(srchigh)
                        serviceobj, created = ServiceObject.objects.get_or_create(name=portrangename, device=dev)
                        serviceobj.device = dev
                        serviceobj.name = portrangename
                        if k[0:3] == 'tcp':
                            serviceobj.protocol = 6
                        elif k[0:3] == 'udp':
                            serviceobj.protocol = 17
                        serviceobj.start_port = dstlow
                        serviceobj.end_port = dsthigh
                        serviceobj.src_start_port = srclow
                        serviceobj.src_start_port = srchigh
                        compserv.members.add(serviceobj)
                        if options['d'] == 'n':
                            serviceobj.save()
                        else:
                            print("Object not saved")
                            serviceobj.delete()
                elif k == 'protocol' and obj[k] == 'ICMP':
                    if 'unset' in obj.keys() and obj['unset'] == "icmptype":
                        serviceobj, created = ServiceObject.objects.get_or_create(name="icmp", device=dev)
                        serviceobj.start_port = 0
                        serviceobj.end_port = 255
                        serviceobj.save()
                        compserv.members.add(serviceobj)
                    elif 'icmptype' in obj.keys():
                        serviceobj, created = ServiceObject.objects.get_or_create(name="icmp-"+obj['icmptype'], device=dev)
                        serviceobj.start_port = obj['icmptype']
                        serviceobj.save()
                        compserv.members.add(serviceobj)
                elif k == 'protocol' and obj[k] == 'IP':
                    if 'protocol-number' in obj.keys():
                        serviceobj, created = ServiceObject.objects.get_or_create(name="ip-proto-"+obj['protocol-number'], device=dev)
                        serviceobj.protocol = int(obj['protocol-number'])
                        serviceobj.save()
                        compserv.members.add(serviceobj)
            if options['d'] == 'n':
                compserv.save()
            else:
                print("Object not saved")
                compserv.delete()
        except:
            print("%s: " % objname)
            print(str(obj))
            raise

def populate_servicegroupobjects(dev, servicegroupdict, options):
    for objname in servicegroupdict.keys():
        """
        Create the Address Group Objects
        """
        servicegroupobject, created = ServiceGroup.objects.get_or_create(name=objname, device=dev)
        obj = servicegroupdict[objname]
        servicegroupobject.name = objname
        servicegroupobject.device = dev
        servicegroupobject.compoundservice = False
        members = obj['member'].split(" ")
        for m in members:
            m = m.strip('"')
            try:
                servicegroup = CompoundServiceObject.objects.get(name=m, device=dev)
                servicegroupobject.members.add(servicegroup)
            except:
                raise
        if options['d'] == 'n':
            servicegroupobject.save()
        else:
            print("Object not saved")
            servicegroupobject.delete()

class Command(BaseCommand):
    help = 'Process Fortigate configuration and populate Normalized Model Objects'
    def add_arguments(self, parser):
        parser.add_argument('-f', action='store',
                            metavar='<configuration-file>',
                            help='path to configuration file',
                            required=True)

        parser.add_argument('-d', metavar='y|n',
                            help='Dry Run (Don\'t alter database)',
                            required=False,
                            default='n'
                            )

    def handle(self, *args, **options):
        CONFIGFILE = options['f']
        print(("Parsing Configuration File: %s" % CONFIGFILE))
        try:
            fullconfigstr = open(CONFIGFILE, 'r').read()
            configtime = os.path.getmtime(CONFIGFILE)
        except:
            print(("Error reading config file: %s" % CONFIGFILE))

        fullconfiglines = fullconfigstr.splitlines()

        # Create the RawConfig Object
        rawconfig, rawconfigcreated = RawConfigFile.objects.get_or_create(name=ntpath.basename(CONFIGFILE),
                                                            import_date = datetime.datetime.fromtimestamp(configtime))


        #configversion, configversioncreated = ConfigVersion.objects.get_or_create(rawfile=rawconfig)
        rawconfig.configstr = fullconfigstr
        rawconfig.name = ntpath.basename(CONFIGFILE)
        rawconfig.import_date = datetime.datetime.fromtimestamp(configtime)

        # Get device and vdom information
        globalconfig = fullconfiglines[fullconfiglines.index('config system global') + 1:]
        globalconfig = globalconfig[:globalconfig.index('end')]

        for line in globalconfig:
            if line.strip() != 'next' and line.strip().startswith('set'):
                key, val = re.match(r'^set (\S*) (.+)$', line.strip()).groups()
                val = val.strip('"')
                if key == 'hostname':
                    hostname = val

        configdict = {}
        #Try to convert the config to a dict
        elementstack = []
        for line in fullconfiglines:
            currentdict = configdict
            for key in elementstack:
                currentdict = currentdict[key]
            arguments = line.split()
            if arguments != []:
                action = arguments.pop(0)
                #python3: action, *arguments = line.split()
                if action == 'config':
                    header = ' '.join(arguments)
                    if (header == 'vdom' and ('vdom' not in elementstack)) or (header != 'vdom'):
                        if header not in currentdict:
                            currentdict[header] = {}
                        elementstack.append(header)
                if action == 'edit':
                    section = ' '.join(arguments).strip('"')
                    if section not in currentdict:
                        currentdict[section] = {}
                    elementstack.append(section)
                if action == 'set':
                    name = arguments.pop(0)
                    value = ' '.join(arguments).strip('"')
                    currentdict[name] = value
                if action == 'end' or action == 'next':
                    elementstack.pop()


        # Create one Device Object and ConfigSet for each VDOM
        if 'vdom' in configdict:
            print("VDOMs Detected: %d %s" % (
                len(list(configdict['vdom'].keys())),
                str(list(configdict['vdom'].keys())))
                  )
            for vdom in configdict['vdom']:
                device, devicecreated = Device.objects.get_or_create(hostname=hostname, vsys=vdom)
                device.devtype = 'fgt52'
                device.hostname = hostname
                if options['d'] == 'n':
                    device.save()
                if 'firewall address' in configdict['vdom'][vdom]:
                    addressobjdict = configdict['vdom'][vdom]['firewall address']
                else:
                    addressobjdict = {}

                if 'firewall addrgrp' in configdict['vdom'][vdom]:
                    addrgrpdict = configdict['vdom'][vdom]['firewall addrgrp']
                else:
                    addrgrpdict = {}

                if 'firewall service custom' in configdict['vdom'][vdom]:
                    serviceobjdict = configdict['vdom'][vdom]['firewall service custom']
                else:
                    serviceobjdict = {}

                if 'firewall service group' in configdict['vdom'][vdom]:
                    servicegroupdict = configdict['vdom'][vdom]['firewall service group']
                else:
                    servicegroupdict = {}

                if 'firewall policy' in configdict['vdom'][vdom]:
                    policydict = configdict['vdom'][vdom]['firewall policy']
                else:
                    policydict = {}

                populate_addressobjs(device, addressobjdict, options)
                populate_addrgrpobjects(device, addrgrpdict, options)
                populate_serviceobjects(device, serviceobjdict, options)
                populate_servicegroupobjects(device, servicegroupdict, options)
                print("\nStatistics for VDOM: %s" % vdom)
                print("Total Address Objects: %d" % len(list(addressobjdict.keys())))
                print("Total Address Group Objects: %d" % len(list(addrgrpdict.keys())))
                print("Total Service Objects: %d" % len(list(serviceobjdict.keys())))
                print("Total Policies: %d" % len(list(policydict.keys())))
        else:
            device, devicecreated = Device.objects.get_or_create(hostname=hostname, vsys='default')
            device.devtype = 'fgt52'
            device.hostname = hostname
            if options['d'] == 'n':
                device.save()
            addressobjdict = configdict['firewall address']
            populate_addressobjs(device, addressobjdict, options)
            populate_addrgrpobjects(device, addrgrpdict, options)

        # Create the current configversion object

        if options['d'] == 'n':
            rawconfig.save()
