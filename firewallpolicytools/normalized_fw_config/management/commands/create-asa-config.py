#!/usr/local/bin/python
"""
Author: Fahad Yousuf <fahadysf@gmail.com>
This will create a Cisco ASA configuration from the normalized configuration of a device.
"""

import ipaddress
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
import json

from normalized_fw_config.models import *

def remove_fields_key(jsonobj):
    for i,obj in enumerate(jsonobj):
        jsonobj[i] = jsonobj[i]['fields']
    return jsonobj

def serializepolicyaddrset(id):
    try:
        pas = PolicyAddrSet.objects.get(pk=id)
        pasjson =  json.loads(serializers.serialize('json', [pas]))[0]['fields']
        pasjson['addresses'] = remove_fields_key(json.loads(
                serializers.serialize('json', AddressObject.objects.filter(pk__in=pasjson['addresses']))
            )
        )
        pasjson['addressgroups'] = remove_fields_key(json.loads(
                serializers.serialize('json', AddressGroup.objects.filter(pk__in=pasjson['addressgroups']))
            )
        )
        for agso in pasjson['addressgroups']:
            agso['members'] = remove_fields_key(json.loads(
                    serializers.serialize('json', AddressObject.objects.filter(pk__in=agso['members']))
                )
            )
        return pasjson
    except:
        print('PolicyAddressSet ID: %d' % id)
        raise

def serializepolicyserviceset(id):
    try:
        pss = PolicyServiceSet.objects.get(pk=id)
        pssjson =  json.loads(serializers.serialize('json', [pss]))[0]['fields']
        pssjson['services'] = remove_fields_key(json.loads(
                serializers.serialize('json', ServiceObject.objects.filter(pk__in=pssjson['services']))
            )
        )
        pssjson['compoundservices'] = remove_fields_key(json.loads(
                serializers.serialize('json', CompoundServiceObject.objects.filter(pk__in=pssjson['compoundservices']))
            )
        )
        for cso in pssjson['compoundservices']:
            cso['members'] = remove_fields_key(json.loads(
                    serializers.serialize('json', ServiceObject.objects.filter(pk__in=cso['members']))
                )
            )
        pssjson['servicegroups'] = remove_fields_key(json.loads(
                serializers.serialize('json', ServiceGroup.objects.filter(pk__in=pssjson['servicegroups']))
            )
        )
        return pssjson
    except:
        raise


def serializepolicy(jsonpolicy):
    try:
        if len(jsonpolicy)!=1:
            print("Unparsable policy: \n%s" % str(jsonpolicy))

        # Remove the 'fields' subkey
        jsonpolicy[0] = jsonpolicy[0]['fields']
        # Serialize the destinatoin in place
        jsonpolicy[0]['destination'] = serializepolicyaddrset(jsonpolicy[0]['destination'])
        # Serialize the source in place
        jsonpolicy[0]['source'] = serializepolicyaddrset(jsonpolicy[0]['source'])
        # Serialize the services list
        jsonpolicy[0]['services'] = serializepolicyserviceset(jsonpolicy[0]['services'])
        return jsonpolicy[0]
    except:
        print("Exception while handling policy: ")
        print(json.dumps(jsonpolicy, indent=2, sort_keys=True))
        raise

class Command(BaseCommand):
    help = 'Process Fortigate configuration and populate Normalized Model Objects'
    def add_arguments(self, parser):
        parser.add_argument('--hostname', action='store',
                            metavar='device-hostname',
                            help='Hostname for device to convert config from',
                            required=True)

        parser.add_argument('--vsys', metavar='y|n',
                            help='vsys/vdom/context',
                            required=False,
                            default='n'
                            )

    def handle(self, *args, **options):
        hn = options['hostname']
        try:
            if 'vsys' in options:
                srcdevobj = Device.objects.filter(hostname=hn, vsys=options['vsys'])
            else:
                srcdevobj = Device.objects.filter(hostname=hn)
        except:
            raise
        print(("!Policies for source device: %s" % srcdevobj))
        input_policies = Policy.objects.filter(device=srcdevobj)

        #Print out the policies
        jsonpollist = []
        for inputpol in input_policies:
            jsonpolicy = json.loads(serializers.serialize('json', [inputpol]))
            jsonpollist.append(serializepolicy(jsonpolicy))
            #if len(jsonpollist) > 20:
            #    break

        jsonout = open("full-json-output.json", 'w')
        jsonout.write(json.dumps(jsonpollist, indent=2, sort_keys=True))
        jsonout.close()

        # define the Cisco ASA routing table here
        ROUTES=[
               ("0.0.0.0", "0.0.0.0", "10.20.8.3", "Outside"),
               ("10.20.45.0", "255.255.255.0", "10.20.11.4", "FWOut-GenBand3850-1300"),
               ("10.20.46.0", "255.255.255.240", "10.20.11.4", "FWOut-GenBand3850-1300"),
               ("10.21.0.0", "255.255.240.0", "10.20.10.1", "FabricasGW-1201"),
               ("10.21.16.0", "255.255.240.0", "10.20.10.9", "FabricasGW-1202"),
               ("10.21.32.0", "255.255.224.0", "10.20.10.201", "FabricasGW-1294"),
               ("10.21.128.0", "255.255.224.0", "10.20.10.201", "FabricasGW-1294"),
               ("10.21.160.0", "255.255.240.0", "10.20.10.201", "FabricasGW-1294"),
               ("10.21.176.0", "255.255.240.0", "10.20.10.209", "FabricasGW-1295"),
               ("10.22.192.0", "255.255.240.0", "10.20.10.131", "LBasGW-1901"),
               ("10.22.208.0", "255.255.240.0", "10.20.10.139", "LBasGW-1902"),
        ]

        for i,dest in enumerate(ROUTES):
            ROUTES[i] = (ipaddress.IPv4Network(ROUTES[i][0]+'/'+ROUTES[i][1]), ROUTES[i][2], ROUTES[i][3])

        #print(ROUTES)

        MONITOR_NETS = [ "10.21.32.0/19", "10.21.128.0/19", "10.21.160.0/20" ]
        for i,net in enumerate(MONITOR_NETS):
            MONITOR_NETS[i] = ipaddress.IPv4Network(MONITOR_NETS[i])

        #print(MONITOR_NETS)

        addrobjs = dict()
        addrobjgroups = dict()
        serviceobjgroups = dict()
        in_to_out_policies = dict()
        out_to_in_policies = dict()

        INSIDE_ACL_NAME = 'FabricasGW-1294_in'
        OUTSIDE_ACL_NAME = 'outside_in'

        for pol in jsonpollist:
            #print('!parsing policyid %s' % pol['policyid'])
            policysrcnets = list()
            #We first determine whether policy is valid for us or not
            combined_pol_source_addrs = pol['source']['addresses']
            for addr in pol['source']['addressgroups']:
                for member in addr['members']:
                    combined_pol_source_addrs.append(member)
            #print('!policy source addresses')
            #print('!'+(', '.join([i['name'] for i in combined_pol_source_addrs])))
            combined_pol_destination_addrs = pol['destination']['addresses']
            for addr in pol['destination']['addressgroups']:
                for member in addr['members']:
                    combined_pol_destination_addrs.append(member)
            #print('!policy destination addresses')
            #print('!'+(', '.join([i['name'] for i in combined_pol_destination_addrs])))

            requires_in2out_policy = False
            requires_out2in_policy = False
            inside_srcs = set()
            outside_dsts = set()
            outside_srcs = set()
            inside_dsts = set()

            # Check for inside sources
            for srcaddr in combined_pol_source_addrs:
                try:
                    if srcaddr['type'] == 'net4':
                        netstr = srcaddr['start_ip'] + '_' + str(srcaddr['prefixlen'])
                        net = ipaddress.IPv4Network(netstr.replace('_', '/'))
                        for monnet in MONITOR_NETS:
                            if ipaddress.IPv4Network.overlaps(monnet, net) and (net.prefixlen >= monnet.prefixlen):
                                inside_srcs.add(netstr)
                    elif srcaddr['type'] == 'range4':
                        netstr = srcaddr['start_ip'] + '-' + srcaddr['end_ip']
                        rangenets = [ipaddr for ipaddr in ipaddress.summarize_address_range(
                            ipaddress.IPv4Address(srcaddr['start_ip']),
                            ipaddress.IPv4Address(srcaddr['end_ip']))
                                     ]
                        # If atleast 1 rangenet overlaps with monnets
                        singlematch = False
                        for rnet in rangenets:
                            if not singlematch:
                                for monnet in MONITOR_NETS:
                                    if (ipaddress.IPv4Network.overlaps(rnet, monnet) and (rnet.prefixlen >= monnet.prefixlen)):
                                        singlematch = True
                        if singlematch == True:
                            inside_srcs.add(netstr)
                    else:
                        netstr = srcaddr['start_ip']
                        for monnet in MONITOR_NETS:
                            if ipaddress.IPv4Network.overlaps(ipaddress.IPv4Network(netstr + '/32'), monnet):
                                inside_srcs.add(netstr)
                except:
                    print("!Error on srcaddr %s" % str(srcaddr))
                    raise
            # Check for outside destinations
            for dstaddr in combined_pol_destination_addrs:
                try:
                    if dstaddr['type'] == 'net4':
                        netstr = dstaddr['start_ip'] + '_' + str(dstaddr['prefixlen'])
                        net = ipaddress.IPv4Network(netstr.replace('_', '/'))
                        for monnet in MONITOR_NETS:
                            if ipaddress.IPv4Network.overlaps(monnet, net) and (net.prefixlen >= monnet.prefixlen):
                                pass
                            else:
                                outside_dsts.add(netstr)
                    elif dstaddr['type'] == 'range4':
                        netstr = dstaddr['start_ip'] + '-' + dstaddr['end_ip']
                        rangenets = [ipaddr for ipaddr in ipaddress.summarize_address_range(
                            ipaddress.IPv4Address(dstaddr['start_ip']),
                            ipaddress.IPv4Address(dstaddr['end_ip']))
                                     ]
                        # If NO rangenet overlaps with monnets
                        overlapcount = 0
                        for rnet in rangenets:
                            for monnet in MONITOR_NETS:
                                if (ipaddress.IPv4Network.overlaps(rnet, monnet) and (rnet.prefixlen >= monnet.prefixlen)):
                                    overlapcount += 1
                        if overlapcount == 0:
                            outside_dsts.add(netstr)
                    else:
                        netstr = dstaddr['start_ip']
                        overlapcount = 0
                        for monnet in MONITOR_NETS:
                            if ipaddress.IPv4Network.overlaps(ipaddress.IPv4Network(netstr + '/32'), monnet):
                                overlapcount += 1
                            if overlapcount == 0:
                                outside_dsts.add(netstr)
                except:
                    print("!Error on dstaddr %s" % str(dstaddr))
                    raise
            # Check for outside sources
            for srcaddr in combined_pol_source_addrs:
                try:
                    if srcaddr['type'] == 'net4':
                        netstr = srcaddr['start_ip'] + '_' + str(srcaddr['prefixlen'])
                        net = ipaddress.IPv4Network(netstr.replace('_', '/'))
                        for monnet in MONITOR_NETS:
                            if ipaddress.IPv4Network.overlaps(monnet, net) and (net.prefixlen >= monnet.prefixlen):
                                pass
                            else:
                                outside_srcs.add(netstr)
                    elif srcaddr['type'] == 'range4':
                        netstr = srcaddr['start_ip'] + '-' + srcaddr['end_ip']
                        rangenets = [ipaddr for ipaddr in ipaddress.summarize_address_range(
                            ipaddress.IPv4Address(srcaddr['start_ip']),
                            ipaddress.IPv4Address(srcaddr['end_ip']))
                                     ]
                        # If not a single rangenet overlap with monnets
                        overlapcount = 0
                        for rnet in rangenets:
                            for monnet in MONITOR_NETS:
                                if (ipaddress.IPv4Network.overlaps(rnet, monnet) and (rnet.prefixlen >= monnet.prefixlen)):
                                    overlapcount += 1
                        if overlapcount == 0:
                            outside_srcs.add(netstr)
                    else:
                        netstr = srcaddr['start_ip']
                        overlapcount = 0
                        for monnet in MONITOR_NETS:
                            if ipaddress.IPv4Network.overlaps(ipaddress.IPv4Network(netstr + '/32'), monnet):
                                overlapcount += 1
                            if overlapcount == 0:
                                outside_srcs.add(netstr)
                except:
                    print("!Error on srcaddr %s" % str(srcaddr))
                    raise
            # Check for inside destinations
            for dstaddr in combined_pol_destination_addrs:
                try:
                    if dstaddr['type'] == 'net4':
                        netstr = dstaddr['start_ip'] + '_' + str(dstaddr['prefixlen'])
                        net = ipaddress.IPv4Network(netstr.replace('_', '/'))
                        for monnet in MONITOR_NETS:
                            if ipaddress.IPv4Network.overlaps(monnet, net) and (net.prefixlen >= monnet.prefixlen):
                                inside_dsts.add(netstr)
                    elif dstaddr['type'] == 'range4':
                        netstr = dstaddr['start_ip'] + '-' + dstaddr['end_ip']
                        rangenets = [ipaddr for ipaddr in ipaddress.summarize_address_range(
                            ipaddress.IPv4Address(dstaddr['start_ip']),
                            ipaddress.IPv4Address(dstaddr['end_ip']))
                                     ]
                        # If atleast 1 rangenet overlaps with monnets
                        singlematch = False
                        for rnet in rangenets:
                            if not singlematch:
                                for monnet in MONITOR_NETS:
                                    if (ipaddress.IPv4Network.overlaps(rnet, monnet) and (rnet.prefixlen >= monnet.prefixlen)):
                                        singlematch = True
                        if singlematch == True:
                            inside_dsts.add(netstr)
                    else:
                        netstr = dstaddr['start_ip']
                        for monnet in MONITOR_NETS:
                            if ipaddress.IPv4Network.overlaps(ipaddress.IPv4Network(netstr + '/32'), monnet):
                                inside_dsts.add(netstr)
                except:
                    print("!Error on dstaddr %s" % str(dstaddr))
                    raise
            if len(inside_srcs) and len(outside_dsts):
                requires_in2out_policy = True
                #print("!Inside sources: %s" % (', '.join([i for i in inside_srcs])))
                #print("!Outside destinations: %s" % (', '.join([i for i in outside_dsts])))

            if len(outside_srcs) and len(inside_dsts):
                requires_out2in_policy = True
                #print("!Outside sources: %s" % (', '.join([i for i in outside_srcs])))
                #print("!Inside destinations: %s" % (', '.join([i for i in inside_dsts])))

            if requires_in2out_policy:

                #Create the source objects
                srcaddrobjgrpstr = 'pol-' + str(pol['policyid']) + '-in2out-srcs'
                addrobjgroups[srcaddrobjgrpstr] = "object-group network %s\n" % (srcaddrobjgrpstr)
                for inside_src in inside_srcs:
                    for srcaddr in combined_pol_source_addrs:
                        netstr = inside_src
                        if srcaddr['type'] == 'net4' and (netstr.replace('_', '/') == srcaddr['name']):
                            net = ipaddress.IPv4Network(netstr.replace('_', '/'))
                            if inside_src not in addrobjs:
                                addrobjs[inside_src] = "object network %s\n subnet %s %s\nexit" % (netstr,
                                                                                                    str(
                                                                                                        net.network_address),
                                                                                                    str(net.netmask))
                            addrobjgroups[srcaddrobjgrpstr] += " network-object object %s\n" % netstr
                        elif srcaddr['type'] == 'range4' and netstr == srcaddr['start_ip'] + '-' + srcaddr['end_ip']:
                            if inside_src not in addrobjs:
                                addrobjs[netstr] = "object network %s\n range %s %s\nexit" % (netstr,
                                                                                              srcaddr['start_ip'],
                                                                                              srcaddr['end_ip'])
                            addrobjgroups[srcaddrobjgrpstr] += " network-object object %s\n" % netstr
                        elif netstr == srcaddr['start_ip']:
                            addrobjgroups[srcaddrobjgrpstr] += " network-object host %s\n" % netstr
                addrobjgroups[srcaddrobjgrpstr] += "exit"

                # Create the destination objects
                dstaddrobjgrpstr = 'pol-' + str(pol['policyid']) + '-in2out-dsts'
                addrobjgroups[dstaddrobjgrpstr] = "object-group network %s\n" % (dstaddrobjgrpstr)
                for outside_dst in outside_dsts:
                    for dstaddr in combined_pol_destination_addrs:
                        netstr = outside_dst
                        if dstaddr['type'] == 'net4' and (netstr.replace('_','/') == dstaddr['name']):
                            net = ipaddress.IPv4Network(netstr.replace('_', '/'))
                            if outside_dst not in addrobjs:
                                addrobjs[outside_dst] = "object network %s\n subnet %s %s\nexit" % (netstr,
                                                                                               str(net.network_address),
                                                                                               str(net.netmask))
                            addrobjgroups[dstaddrobjgrpstr] += " network-object object %s\n" % netstr
                        elif dstaddr['type'] == 'range4' and netstr == dstaddr['start_ip']+'-'+dstaddr['end_ip']:
                            if outside_dst not in addrobjs:
                                addrobjs[netstr] = "object network %s\n range %s %s\nexit" % (netstr,
                                                                                              dstaddr['start_ip'],
                                                                                              dstaddr['end_ip'])
                            addrobjgroups[dstaddrobjgrpstr] += " network-object object %s\n" % netstr
                        elif netstr == dstaddr['start_ip']:
                            addrobjgroups[dstaddrobjgrpstr] += " network-object host %s\n" % netstr
                addrobjgroups[dstaddrobjgrpstr] += "exit"

                # Create the Service Objects Group for the Policy
                serviceobjgrpstr = 'pol-' + str(pol['policyid']) + '-services'
                if serviceobjgrpstr not in serviceobjgroups:
                    serviceobjgroups[serviceobjgrpstr] = "object-group service %s\n" % serviceobjgrpstr
                    for key in pol['services']:
                        if key == 'compoundservices':
                            for svc in pol['services'][key]:
                                for i in svc['members']:
                                    if i['protocol'] == 6:
                                        protostr = 'tcp'
                                    elif i['protocol'] == 17:
                                        protostr = 'udp'
                                    if i['end_port'] is None:
                                        serviceobjgroups[
                                            serviceobjgrpstr] += ' service-object %s destination eq %s\n' % (
                                        protostr, str(
                                            i['start_port']))
                                    else:
                                        serviceobjgroups[
                                            serviceobjgrpstr] += ' service-object %s destination range %s %s\n' % (
                                            protostr, str(i['start_port']), str(i['end_port']))

                        if key == 'servicegroups':
                            for svcgrp in pol['services'][key]:
                                for key in svcgrp['members']:
                                    if key == 'compoundservices':
                                        for svc in pol['services'][key]:
                                            for i in svc['members']:
                                                if i['protocol'] == 6:
                                                    protostr = 'tcp'
                                                elif i['protocol'] == 17:
                                                    protostr = 'udp'
                                                if i['end_port'] is None:
                                                    serviceobjgroups[
                                                        serviceobjgrpstr] += ' service-object %s destination eq %s\n' % (
                                                        protostr, str(
                                                            i['start_port']))
                                                else:
                                                    serviceobjgroups[
                                                        serviceobjgrpstr] += ' service-object %s destination range %s %s\n' % (
                                                        protostr, str(i['start_port']), str(i['end_port']))
                    serviceobjgroups[serviceobjgrpstr] += 'exit'

                # Build the policy
                in_to_out_policies[pol['policyid']] = "access-list %s line 1 extended permit object-group %s object-group %s  object-group %s log" % (
                    INSIDE_ACL_NAME, serviceobjgrpstr, srcaddrobjgrpstr, dstaddrobjgrpstr)
            if requires_out2in_policy:

                #Create the source objects
                srcaddrobjgrpstr = 'pol-' + str(pol['policyid']) + '-out2in-srcs'
                addrobjgroups[srcaddrobjgrpstr] = "object-group network %s\n" % (srcaddrobjgrpstr)
                for outside_src in outside_srcs:
                    for srcaddr in combined_pol_source_addrs:
                        netstr = outside_src
                        if srcaddr['type'] == 'net4' and (netstr.replace('_', '/') == srcaddr['name']):
                            net = ipaddress.IPv4Network(netstr.replace('_', '/'))
                            if outside_src not in addrobjs:
                                addrobjs[outside_src] = "object network %s\n subnet %s %s\nexit" % (netstr,
                                                                                                    str(
                                                                                                        net.network_address),
                                                                                                    str(net.netmask))
                            addrobjgroups[srcaddrobjgrpstr] += " network-object object %s\n" % netstr
                        elif srcaddr['type'] == 'range4' and netstr == srcaddr['start_ip'] + '-' + srcaddr['end_ip']:
                            if outside_src not in addrobjs:
                                addrobjs[netstr] = "object network %s\n range %s %s\nexit" % (netstr,
                                                                                              srcaddr['start_ip'],
                                                                                              srcaddr['end_ip'])
                            addrobjgroups[srcaddrobjgrpstr] += " network-object object %s\n" % netstr
                        elif netstr == srcaddr['start_ip']:
                            addrobjgroups[srcaddrobjgrpstr] += " network-object host %s\n" % netstr
                addrobjgroups[srcaddrobjgrpstr] += "exit"

                # Create the destination objects
                dstaddrobjgrpstr = 'pol-' + str(pol['policyid']) + '-out2in-dsts'
                addrobjgroups[dstaddrobjgrpstr] = "object-group network %s\n" % (dstaddrobjgrpstr)
                for inside_dst in inside_dsts:
                    for dstaddr in combined_pol_destination_addrs:
                        netstr = inside_dst
                        if dstaddr['type'] == 'net4' and (netstr.replace('_','/') == dstaddr['name']):
                            net = ipaddress.IPv4Network(netstr.replace('_', '/'))
                            if inside_dst not in addrobjs:
                                addrobjs[inside_dst] = "object network %s\n subnet %s %s\nexit" % (netstr,
                                                                                               str(net.network_address),
                                                                                               str(net.netmask))
                            addrobjgroups[dstaddrobjgrpstr] += " network-object object %s\n" % netstr
                        elif dstaddr['type'] == 'range4' and netstr == dstaddr['start_ip']+'-'+dstaddr['end_ip']:
                            if inside_dst not in addrobjs:
                                addrobjs[netstr] = "object network %s\n range %s %s\nexit" % (netstr,
                                                                                              dstaddr['start_ip'],
                                                                                              dstaddr['end_ip'])
                            addrobjgroups[dstaddrobjgrpstr] += " network-object object %s\n" % netstr
                        elif netstr == dstaddr['start_ip']:
                            addrobjgroups[dstaddrobjgrpstr] += " network-object host %s\n" % netstr
                addrobjgroups[dstaddrobjgrpstr] += "exit"

                # Create the Service Objects Group for the Policy
                serviceobjgrpstr = 'pol-' + str(pol['policyid']) + '-services'
                if serviceobjgrpstr not in serviceobjgroups:
                    serviceobjgroups[serviceobjgrpstr] = "object-group service %s\n" % serviceobjgrpstr
                    for key in pol['services']:
                        if key == 'compoundservices':
                            for svc in pol['services'][key]:
                                for i in svc['members']:
                                    if i['protocol'] == 6:
                                        protostr = 'tcp'
                                    elif i['protocol'] == 17:
                                        protostr = 'udp'
                                    if i['end_port'] is None:
                                        serviceobjgroups[
                                            serviceobjgrpstr] += ' service-object %s destination eq %s\n' % (
                                        protostr, str(
                                            i['start_port']))
                                    else:
                                        serviceobjgroups[
                                            serviceobjgrpstr] += ' service-object %s destination range %s %s\n' % (
                                            protostr, str(i['start_port']), str(i['end_port']))

                        if key == 'servicegroups':
                            for svcgrp in pol['services'][key]:
                                print(json.dumps(svcgrp))
                    serviceobjgroups[serviceobjgrpstr] += 'exit'

                # Build the policy
                out_to_in_policies[pol['policyid']] = "access-list %s line 1 extended permit object-group %s object-group %s object-group %s log" % (
                    OUTSIDE_ACL_NAME, serviceobjgrpstr, srcaddrobjgrpstr, dstaddrobjgrpstr)

        for a in addrobjs:
            #print("!Address Object %s" % a)
            print(addrobjs[a])
        for ag in addrobjgroups:
            #print("!Address Object Group %s" % ag)
            print(addrobjgroups[ag])
        for svcg in serviceobjgroups:
            #print("!Service Object Group %s" % svcg)
            print(serviceobjgroups[svcg])
        for policy in in_to_out_policies:
            #print("!Policy ID %s" % policy)
            print(in_to_out_policies[policy])
        for policy in out_to_in_policies:
            #print("!Policy ID %s" % policy)
            print(out_to_in_policies[policy])
