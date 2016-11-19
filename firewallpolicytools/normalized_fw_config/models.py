from django.db import models

# Create your models here.
class RawConfigFile(models.Model):
    configstr = models.TextField()
    name = models.CharField(max_length=300)
    import_date = models.DateTimeField('Import Timestamp', auto_now=True)

class Device(models.Model):
    DEVTYPE_CHOICES = (
        ('asa9', 'Cisco ASA 9.x'),
        ('fgt52', 'Fortigate 5.2+')
    )
    devtype = models.CharField(max_length=10, choices=DEVTYPE_CHOICES)
    hostname = models.CharField(max_length=128)
    vsys = models.CharField(max_length=64, null=True, default=None)

    def __str__(self):
        return self.hostname + " [" + self.vsys +"]"

class ConfigVersion(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    current_active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now=True)
    rawfile = models.ForeignKey(RawConfigFile, null=True, default=None)

class AddressObject(models.Model):
    TYPE_CHOICES = (
        ('range4', 'IPv4 Range Object'),
        ('range6', 'IPv6 Range Object'),
        ('net4', 'IPv4 Network Object'),
        ('net6', 'IPv6 Network Object'),
        ('ip4', 'IPv4 Single Address Object'),
        ('ip6', 'IPv6 Single Address Object'),
        ('fqdn', 'Fully Qualified Domain Name (FQDN) Object')
    )
    type = models.CharField(max_length=6, choices=TYPE_CHOICES)
    name = models.CharField(max_length=64)
    start_ip = models.GenericIPAddressField(null=True)
    end_ip = models.GenericIPAddressField(null=True)
    prefixlen = models.IntegerField(null=True, default=None)
    fqdn = models.CharField(max_length=256, null=True, default=None)
    description = models.CharField(max_length=512, null=True, default=None)
    configs = models.ManyToManyField(ConfigVersion)
    device = models.ForeignKey(Device)

    def __str__(self):
        return self.name

class ServiceObject(models.Model):
    PROTO_CHOICES = (
        (0, 'HOPOPT'),
        (1, 'ICMP'),
        (2, 'IGMP'),
        (3, 'GGP'),
        (4, 'IPv4'),
        (5, 'ST'),
        (6, 'TCP'),
        (7, 'CBT'),
        (8, 'EGP'),
        (9, 'IGP'),
        (10, 'BBN-RCC-MON'),
        (11, 'NVP-II'),
        (12, 'PUP'),
        (13, 'ARGUS'),
        (14, 'EMCON'),
        (15, 'XNET'),
        (16, 'CHAOS'),
        (17, 'UDP'),
        (18, 'MUX'),
        (19, 'DCN-MEAS'),
        (20, 'HMP'),
        (21, 'PRM'),
        (22, 'XNS-IDP'),
        (23, 'TRUNK-1'),
        (24, 'TRUNK-2'),
        (25, 'LEAF-1'),
        (26, 'LEAF-2'),
        (27, 'RDP'),
        (28, 'IRTP'),
        (29, 'ISO-TP4'),
        (30, 'NETBLT'),
        (31, 'MFE-NSP'),
        (32, 'MERIT-INP'),
        (33, 'DCCP'),
        (34, '3PC'),
        (35, 'IDPR'),
        (36, 'XTP'),
        (37, 'DDP'),
        (38, 'IDPR-CMTP'),
        (39, 'TP++'),
        (40, 'IL'),
        (41, 'IPv6'),
        (42, 'SDRP'),
        (43, 'IPv6-Route'),
        (44, 'IPv6-Frag'),
        (45, 'IDRP'),
        (46, 'RSVP'),
        (47, 'GRE'),
        (48, 'DSR'),
        (49, 'BNA'),
        (50, 'ESP'),
        (51, 'AH'),
        (52, 'I-NLSP'),
        (53, 'SWIPE'),
        (54, 'NARP'),
        (55, 'MOBILE'),
        (56, 'TLSP'),
        (57, 'SKIP'),
        (58, 'IPv6-ICMP'),
        (59, 'IPv6-NoNxt'),
        (60, 'IPv6-Opts'),
        (62, 'CFTP'),
        (64, 'SAT-EXPAK'),
        (65, 'KRYPTOLAN'),
        (66, 'RVD'),
        (67, 'IPPC'),
        (69, 'SAT-MON'),
        (70, 'VISA'),
        (71, 'IPCV'),
        (72, 'CPNX'),
        (73, 'CPHB'),
        (74, 'WSN'),
        (75, 'PVP'),
        (76, 'BR-SAT-MON'),
        (77, 'SUN-ND'),
        (78, 'WB-MON'),
        (79, 'WB-EXPAK'),
        (80, 'ISO-IP'),
        (81, 'VMTP'),
        (82, 'SECURE-VMTP'),
        (83, 'VINES'),
        (84, 'TTP'),
        (84, 'IPTM'),
        (85, 'NSFNET-IGP'),
        (86, 'DGP'),
        (87, 'TCF'),
        (88, 'EIGRP'),
        (89, 'OSPFIGP'),
        (90, 'Sprite-RPC'),
        (91, 'LARP'),
        (92, 'MTP'),
        (93, 'AX.25'),
        (94, 'IPIP'),
        (96, 'SCC-SP'),
        (97, 'ETHERIP'),
        (98, 'ENCAP'),
        (100, 'GMTP'),
        (101, 'IFMP'),
        (102, 'PNNI'),
        (103, 'PIM'),
        (104, 'ARIS'),
        (105, 'SCPS'),
        (106, 'QNX'),
        (107, 'A/N'),
        (108, 'IPComp'),
        (109, 'SNP'),
        (110, 'Compaq-Peer'),
        (111, 'IPX-in-IP'),
        (112, 'VRRP'),
        (113, 'PGM'),
        (115, 'L2TP'),
        (116, 'DDX'),
        (117, 'IATP'),
        (118, 'STP'),
        (119, 'SRP'),
        (120, 'UTI'),
        (121, 'SMP'),
        (122, 'SM',),
        (123, 'PTP'),
        (124, 'ISIS over IPv4'),
        (125, 'FIRE'),
        (126, 'CRTP'),
        (127, 'CRUDP'),
        (128, 'SSCOPMCE'),
        (129, 'IPLT'),
        (130, 'SPS'),
        (131, 'PIPE'),
        (132, 'SCTP'),
        (133, 'FC'),
        (134, 'RSVP-E2E-IGNORE'),
        (135, 'Mobility Header'),
        (136, 'UDPLite'),
        (137, 'MPLS-in-IP'),
        (138, 'manet'),
        (139, 'HIP'),
        (140, 'Shim6'),
        (141, 'WESP'),
        (142, 'ROHC'),
        (256, 'TCP+UDP'),
        (257, 'TCP+UDP+SCTP'), #  This is the default for FortiGate Devices
    )
    name = models.CharField(max_length=128)
    protocol = models.IntegerField(choices=PROTO_CHOICES, default=256),
    # This substitutes as ICMP type for ICMP protocol
    start_port = models.IntegerField(null=True,default=None)
    end_port = models.IntegerField(null=True, default=None)
    src_start_port = models.IntegerField(null=True, default=None)
    src_end_port = models.IntegerField(null=True, default=None)
    # Only valid for ICMP
    icmp_code = models.IntegerField(null=True, default=None)
    description = models.CharField(max_length=512, default='')
    configs = models.ManyToManyField(ConfigVersion)
    device = models.ForeignKey(Device)

    def __str__(self):
        return self.name

class CompoundServiceObject(models.Model):
    name = models.CharField(max_length=64)
    members = models.ManyToManyField(ServiceObject)
    configs = models.ManyToManyField(ConfigVersion)
    device = models.ForeignKey(Device)

    def __str__(self):
        return self.name

class AddressGroup(models.Model):
    name = models.CharField(max_length=64)
    members = models.ManyToManyField(AddressObject)
    configs = models.ManyToManyField(ConfigVersion)
    device = models.ForeignKey(Device)

    def __str__(self):
        return self.name

class ServiceGroup(models.Model):
    name = models.CharField(max_length=64)
    members = models.ManyToManyField(CompoundServiceObject)
    device = models.ForeignKey(Device)
    configs = models.ManyToManyField(ConfigVersion)

    def __str__(self):
        return self.name

class Interface(models.Model):
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=512, null=True, default=None)
    configs = models.ManyToManyField(ConfigVersion)
    device = models.ForeignKey(Device)

    def __str__(self):
        return self.name

class ZoneObject(models.Model):
    # An interface can be treated as a zone
    name = models.CharField(max_length=128)
    members = models.ManyToManyField(Interface)
    description = models.CharField(max_length=512, null=True, default=None)
    configs = models.ManyToManyField(ConfigVersion)
    device = models.ForeignKey(Device)

    def __str__(self):
        return self.name

class Policy(models.Model):
    ACTION_CHOICES = (
        ('permit', "Allow traffic to pass"),
        ('deny', "Deny traffic silently (Drop)"),
        ('reject', "Deny Traffic with and notify sender (TCP RST or ICMP Unreachable)")
    )
    name = models.CharField(max_length=128, null=True, default=None)
    policyid = models.IntegerField(default=0)
    sequence = models.IntegerField(default=0)
    source = models.ManyToManyField(AddressObject, related_name='src_object')
    destination = models.ManyToManyField(AddressObject, related_name='dst_object')
    srczone = models.ManyToManyField(ZoneObject, related_name='src_zone')
    dstzone = models.ManyToManyField(ZoneObject, related_name='dst_zone')
    services = models.ManyToManyField(ServiceObject)
    configs = models.ManyToManyField(ConfigVersion)
    device = models.ForeignKey(Device)
    action = models.CharField(max_length=6, choices=ACTION_CHOICES)

    def __str__(self):
        if self.name:
            return self.policyid + ': ' + self.name
        return self.policyid