from django.contrib import admin

# Register your models here.
from normalized_fw_config.models import RawConfigFile, \
    ConfigVersion, \
    AddressObject, \
    AddressGroup, \
    ServiceObject, \
    ServiceGroup, \
    Policy, \
    ZoneObject, \
    Device, \
    Interface

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
    fields = ('name',  )
    search_fields = ['name']
    list_display = fields

@admin.register(ServiceGroup)
class ServiceGrouptAdmin(admin.ModelAdmin):
    fields = ('name', 'device', 'members')
    search_fields = ['name']
    list_display = ('name', 'device', 'get_members' )

    def get_members(self, obj):
        return ", ".join([mem.name for mem in obj.members.all()])

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    pass

@admin.register(ZoneObject)
class ZoneObjectAdmin(admin.ModelAdmin):
    pass

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    fields = ('hostname', 'vsys', 'devtype')
    list_display = fields
    pass

@admin.register(Interface)
class InterfaceAdmin(admin.ModelAdmin):
    pass
