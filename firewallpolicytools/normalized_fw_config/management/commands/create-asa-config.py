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
        print(("Policies for source device: %s" % srcdevobj))
        input_policies = Policy.objects.filter(device=srcdevobj)

        #Print out the policies
        jsonpollist = []
        for inputpol in input_policies:
            jsonpolicy = json.loads(serializers.serialize('json', [inputpol]))
            jsonpollist.append(serializepolicy(jsonpolicy))
            if len(jsonpollist) > 0:
                break

        print(json.dumps(jsonpollist, indent=2, sort_keys=True))

        # define the Cisco ASA routing table here
