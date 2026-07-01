from django.db import models
from django.contrib.auth.models import User

class Kebun(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nama = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

class APIKey(models.Model):
    """Model untuk menyimpan API Key yang sudah ada di admin (untuk validasi saat konek alat)"""
    api_key = models.CharField(max_length=100, unique=True, primary_key=True)
    nama_alat = models.CharField(max_length=100, default="Unknown Device")
    status = models.CharField(max_length=20, choices=[
        ('active', 'Aktif'),
        ('inactive', 'Tidak Aktif'),
    ], default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.api_key} - {self.nama_alat}"

class Tanaman(models.Model):
    kebun = models.ForeignKey(Kebun, on_delete=models.CASCADE, related_name='tanamans')
    nama = models.CharField(max_length=100)
    foto = models.ImageField(upload_to='tanaman_photos/', null=True, blank=True, default='tanaman_photos/default_tanaman.svg')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama} - {self.kebun.nama}"

class Rak(models.Model):
    tanaman = models.ForeignKey(Tanaman, on_delete=models.CASCADE, related_name='raks', null=True, blank=True)
    nama_rak = models.CharField(max_length=100)
    # API Key harus ada di database admin terlebih dahulu
    api_key = models.ForeignKey(APIKey, on_delete=models.PROTECT)
    nomor_wa = models.CharField(max_length=20)
    # Foto Rak (opsional)
    foto = models.ImageField(upload_to='rak_photos/', null=True, blank=True, default='rak_photos/default_rak.svg')
    # Deep Sleep Interval (Default 30 menit)
    deepsleep_menit = models.IntegerField(default=30, choices=[
        (5, '5 Menit'),
        (10, '10 Menit'),
        (15, '15 Menit'),
        (30, '30 Menit'),
        (60, '1 Jam'),
    ])
    # Early Warning System (EWS) pH Limits
    min_ph = models.FloatField(default=5.5)
    max_ph = models.FloatField(default=6.5)
    # Cooldown timer to prevent spamming notifications
    last_notification_sent = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)


class DataSensor(models.Model):
    rak = models.ForeignKey(Rak, on_delete=models.CASCADE, related_name='data_sensor')
    timestamp = models.DateTimeField(auto_now_add=True)
    ph = models.FloatField()
    tds = models.FloatField()
    suhu = models.FloatField()

    class Meta:
        ordering = ['-timestamp']