from django.contrib import admin

# Register your models here.
from normalized_fw_config.models import RawConfigFile, \
    ConfigVersion, \
    AddressObject, \
    AddressGroup, \
    ServiceObject, \
    CompoundServiceObject, \
    ServiceGroup, \
    Policy, \
    ZoneObject, \
    Device, \
    Interface, \
    PolicyAddrSet, \
    PolicyZoneSet, \
    PolicyServiceSet

@admin.register(RawConfigFile)
class RawConfigFileAdmin(admin.ModelAdmin):
    pass

@admin.register(ConfigVersion)
class ConfigVersionAdmin(admin.ModelAdmin):
    pass

@admin.register(AddressObject)
class AddressObjectAdmin(admin.ModelAdmin):
    fields = ('name', 'type', 'fqdn', 'start_ip', 'end_ip', 'prefixlen', 'device')
    search_fields = ['name']
    list_display = fields

@admin.register(AddressGroup)
class AddressGroupAdmin(admin.ModelAdmin):
    fields = ('name','device', 'members')
    search_fields = ['name']
    list_display = ('name', 'device', 'get_members' )

    def get_members(self, obj):
        return ", ".join([mem.name for mem in obj.members.all()])

@admin.register(ServiceObject)
class ServiceObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'device')
    search_fields = ['name']

@admin.register(CompoundServiceObject)
class CompoundServiceObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'device', 'get_members')
    search_fields = ['name']

    def get_members(self, obj):
        return ", ".join([mem.name for mem in obj.members.all()])

@admin.register(ServiceGroup)
class ServiceGrouptAdmin(admin.ModelAdmin):
    fields = ('name', 'device', 'members')
    search_fields = ['name']
    list_display = ('name', 'device', 'get_members' )

    def get_members(self, obj):
        return ", ".join([mem.name for mem in obj.members.all()])

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('id', 'sequence', 'source')

@admin.register(ZoneObject)
class ZoneObjectAdmin(admin.ModelAdmin):
    pass

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    fields = ('hostname', 'vsys', 'devtype')
    list_display = fields

@admin.register(Interface)
class InterfaceAdmin(admin.ModelAdmin):
    fields = ('name', 'device')
    list_display = fields

@admin.register(PolicyAddrSet)
class PolicyAddrSetAdmin(admin.ModelAdmin):
    fields = ('addresses', 'addressgroups')
    list_display = ('addrlist', 'addrgrouplist')

    def addrlist(self, obj):
        return ", ".join([z.name for z in obj.addresses.all()])

    def addrgrouplist(self, obj):
        return ", ".join([i.name for i in obj.addressgroups.all()])

@admin.register(PolicyServiceSet)
class PolicyServiceSetAdmin(admin.ModelAdmin):
    fields = ('services','servicegroups')
    list_display = ('compoundservicelist','servicelist', 'servicegrouplist')

    def compoundservicelist(self, obj):
        return ", ".join([z.name for z in obj.compoundservices.all()])

    def servicelist(self, obj):
        return ", ".join([z.name for z in obj.services.all()])

    def servicegrouplist(self, obj):
        return ", ".join([i.name for i in obj.servicegroups.all()])

@admin.register(PolicyZoneSet)
class PolicyZoneSetAdmin(admin.ModelAdmin):
    fields = ('zones', 'interfaces')
    list_display = ('zonelist', 'interfacelist')

    def zonelist(self, obj):
        return ", ".join([z.name for z in obj.zones.all()])

    def interfacelist(self, obj):
        return ", ".join([i.name for i in obj.interfaces.all()])