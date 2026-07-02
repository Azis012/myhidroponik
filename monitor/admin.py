from django.contrib import admin
from .models import APIKey, Kebun, Tanaman, Rak, DataSensor

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('api_key', 'nama_alat', 'get_connected_user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('api_key', 'nama_alat')

    def get_connected_user(self, obj):
        raks = obj.rak_set.all()
        users = set()
        for r in raks:
            if r.tanaman and r.tanaman.kebun and r.tanaman.kebun.user:
                users.add(r.tanaman.kebun.user.username)
        return ", ".join(users) if users else "-"
    get_connected_user.short_description = "Terhubung ke User"

@admin.register(Kebun)
class KebunAdmin(admin.ModelAdmin):
    list_display = ('nama', 'user', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('nama', 'user__username')

@admin.register(Tanaman)
class TanamanAdmin(admin.ModelAdmin):
    list_display = ('nama', 'kebun', 'created_at')
    list_filter = ('kebun', 'created_at')
    search_fields = ('nama', 'kebun__nama')

@admin.register(Rak)
class RakAdmin(admin.ModelAdmin):
    list_display = ('nama_rak', 'tanaman', 'api_key', 'min_ph', 'max_ph', 'deepsleep_menit', 'nomor_wa', 'created_at')
    list_filter = ('tanaman__kebun', 'tanaman', 'deepsleep_menit', 'created_at')
    search_fields = ('nama_rak', 'api_key__api_key', 'nomor_wa')
    readonly_fields = ('created_at', 'last_notification_sent')
    fieldsets = (
        ('Info Rak', {
            'fields': ('tanaman', 'nama_rak', 'api_key', 'nomor_wa', 'foto')
        }),
        ('Konfigurasi EWS & Daya', {
            'fields': ('deepsleep_menit', 'min_ph', 'max_ph', 'last_notification_sent')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(DataSensor)
class DataSensorAdmin(admin.ModelAdmin):
    list_display = ('rak', 'get_user', 'ph', 'tds', 'suhu', 'timestamp')
    list_filter = ('rak__tanaman__kebun__user', 'rak', 'timestamp')
    search_fields = ('rak__nama_rak', 'rak__tanaman__kebun__user__username')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)

    def get_user(self, obj):
        if obj.rak and obj.rak.tanaman and obj.rak.tanaman.kebun and obj.rak.tanaman.kebun.user:
            return obj.rak.tanaman.kebun.user.username
        return "-"
    get_user.short_description = "User Pemilik"
