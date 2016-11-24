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
                srcdevobj = Device.objects.filter(hostname=hn)
            else:
                srcdevobj = Device.objects.filter(hostname=hn, vsys=options['vsys'])
        except:
            raise
        print(("Policies for source device: %s" % srcdevobj))
        input_policies = Policy.objects.filter(device=srcdevobj)

        #Print out the policies
        for inputpol in input_policies:
            print(
                serializers.serialize('json', [inputpol],
                sort_keys=True,
                indent=2,
                )
            )