from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Kebun, Tanaman, Rak, DataSensor, APIKey
from .forms import UserRegisterForm
import paho.mqtt.publish as publish # Pastikan sudah: pip install paho-mqtt
from PIL import Image
import os
from django.conf import settings
import random
from django.core.mail import send_mail
from django.contrib.auth.models import User
from google import genai
from google.genai import types


# --- AUTHENTICATION ---
def register_view(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False # Inactive until OTP is verified
            user.save()
            
            # Generate OTP
            otp = f"{random.randint(100000, 999999)}"
            request.session['otp_code'] = otp
            request.session['otp_user_id'] = user.id
            request.session['otp_purpose'] = 'register'
            
            # Send OTP email
            try:
                send_mail(
                    'Kode OTP Registrasi - Smart Hidroponik',
                    f'Halo {user.username},\n\nKode OTP registrasi Anda adalah: {otp}\n\nMasukkan kode ini di halaman verifikasi untuk mengaktifkan akun Anda.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send email: {e}")
                
            return redirect('verify_otp')
    else:
        form = UserRegisterForm()
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                # If they registered but haven't verified OTP yet, send a new one
                otp = f"{random.randint(100000, 999999)}"
                request.session['otp_code'] = otp
                request.session['otp_user_id'] = user.id
                request.session['otp_purpose'] = 'register'
                try:
                    send_mail(
                        'Kode OTP Registrasi - Smart Hidroponik',
                        f'Halo {user.username},\n\nKode OTP registrasi Anda adalah: {otp}\n\nMasukkan kode ini di halaman verifikasi untuk mengaktifkan akun Anda.',
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"Failed to send email: {e}")
                messages.warning(request, "Akun Anda belum aktif. Kami telah mengirimkan kode OTP baru ke email Anda.")
                return redirect('verify_otp')
                
            login(request, user)
            return redirect('daftar_kebun')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def password_reset_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            otp = f"{random.randint(100000, 999999)}"
            request.session['otp_code'] = otp
            request.session['otp_user_id'] = user.id
            request.session['otp_purpose'] = 'reset_password'
            
            try:
                send_mail(
                    'Kode OTP Reset Password - Smart Hidroponik',
                    f'Halo {user.username},\n\nKode OTP untuk mereset password Anda adalah: {otp}\n\nMasukkan kode ini di halaman verifikasi untuk melanjutkan reset password.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send email: {e}")
        except User.DoesNotExist:
            # Silently redirect for security to prevent email enumeration
            pass
        messages.success(request, "Jika email terdaftar di sistem kami, kode OTP telah dikirimkan.")
        return redirect('verify_otp')
        
    return render(request, 'auth/password_reset_form.html')

def verify_otp(request):
    purpose = request.session.get('otp_purpose')
    if not purpose:
        return redirect('login')
        
    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        session_otp = request.session.get('otp_code')
        user_id = request.session.get('otp_user_id')
        
        if entered_otp == session_otp and user_id:
            user = get_object_or_404(User, id=user_id)
            if purpose == 'register':
                user.is_active = True
                user.save()
                login(request, user)
                
                # Clear session OTP
                del request.session['otp_code']
                del request.session['otp_user_id']
                del request.session['otp_purpose']
                
                messages.success(request, "Registrasi berhasil! Akun Anda telah aktif.")
                return redirect('daftar_kebun')
            elif purpose == 'reset_password':
                # Mark that OTP is verified so password reset confirm page is accessible
                request.session['otp_verified'] = True
                return redirect('password_reset_confirm_otp')
        else:
            messages.error(request, "Kode OTP salah atau telah kadaluarsa.")
            
    return render(request, 'auth/verify_otp.html', {'purpose': purpose})

def password_reset_confirm_otp(request):
    user_id = request.session.get('otp_user_id')
    purpose = request.session.get('otp_purpose')
    otp_verified = request.session.get('otp_verified')
    
    if not user_id or purpose != 'reset_password' or not otp_verified:
        messages.error(request, "Akses tidak sah.")
        return redirect('login')
        
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password == confirm_password:
            user.set_password(password)
            user.save()
            
            # Clear all authentication session variables
            del request.session['otp_code']
            del request.session['otp_user_id']
            del request.session['otp_purpose']
            del request.session['otp_verified']
            
            messages.success(request, "Password Anda berhasil diperbarui.")
            return redirect('password_reset_complete')
        else:
            messages.error(request, "Password baru dan konfirmasi password tidak cocok.")
            
    return render(request, 'auth/password_reset_confirm_otp.html')

# --- HELPER FUNCTIONS ---
def process_and_convert_image(image_field, folder_name='uploads'):
    """Convert image to WebP format, crop ke square 1:1, dan resize ke 300x300px"""
    if not image_field:
        return None
    
    try:
        img = Image.open(image_field)
        
        # Tentukan folder penyimpanan
        webp_path = os.path.join(settings.MEDIA_ROOT, folder_name)
        os.makedirs(webp_path, exist_ok=True)
        
        # Buat nama file unik dengan ekstensi .webp
        filename = f"{image_field.name.split('.')[0]}.webp"
        filepath = os.path.join(webp_path, filename)
        
        img.save(filepath, 'WEBP', quality=settings.PILLOW_COMPRESS_QUALITY)
        
        return f"{folder_name}/{filename}"
    except Exception as e:
        print(f"Image processing error: {e}")
        return None

# --- CORE LOGIC ---

def daftar_kebun(request):
    if not request.user.is_authenticated:
        return render(request, 'landing.html')
        
    kebuns = Kebun.objects.filter(user=request.user)
    if request.method == "POST":
        nama = request.POST.get('nama_kebun')
        Kebun.objects.create(user=request.user, nama=nama)
        return redirect('daftar_kebun')
    return render(request, 'kebun_list.html', {'kebuns': kebuns})

@login_required
def daftar_tanaman(request, kebun_id):
    kebun = get_object_or_404(Kebun, id=kebun_id, user=request.user)
    tanamans = Tanaman.objects.filter(kebun=kebun)
    
    if request.method == "POST":
        nama = request.POST.get('nama_tanaman')
        foto = request.FILES.get('foto')
        
        foto_path = None
        if foto:
            foto_path = process_and_convert_image(foto, folder_name='tanaman_photos')
        
        Tanaman.objects.create(
            kebun=kebun,
            nama=nama,
            foto=foto_path if foto_path else 'tanaman_photos/default_tanaman.svg'
        )
        messages.success(request, "Tanaman berhasil ditambahkan!")
        return redirect('daftar_tanaman', kebun_id=kebun.id)
        
    return render(request, 'tanaman_list.html', {
        'kebun': kebun,
        'tanamans': tanamans,
    })

@login_required
def daftar_rak(request, tanaman_id):
    # Pastikan kebun milik user yang login
    tanaman = get_object_or_404(Tanaman, id=tanaman_id, kebun__user=request.user)
    raks = Rak.objects.filter(tanaman=tanaman)
    
    if request.method == "POST":
        nama = request.POST.get('nama_rak')
        wa = request.POST.get('nomor_wa')
        key = request.POST.get('api_key')
        foto = request.FILES.get('foto')
        min_ph = request.POST.get('min_ph', '5.5')
        max_ph = request.POST.get('max_ph', '6.5')
        
        # Validasi API Key
        try:
            api_key_obj = APIKey.objects.get(api_key=key, status='active')
        except APIKey.DoesNotExist:
            messages.error(request, f"API Key '{key}' tidak ditemukan atau tidak aktif. Pastikan API Key sudah terdaftar di admin.")
            return redirect('daftar_rak', tanaman_id=tanaman.id)
        
        # Process gambar jika ada
        foto_path = None
        if foto:
            foto_path = process_and_convert_image(foto, folder_name='rak_photos')
        
        Rak.objects.create(
            tanaman=tanaman, 
            nama_rak=nama, 
            nomor_wa=wa, 
            api_key=api_key_obj,
            foto=foto_path if foto_path else 'rak_photos/default_rak.svg',
            min_ph=float(min_ph),
            max_ph=float(max_ph)
        )
        messages.success(request, "Rak berhasil ditambahkan!")
        return redirect('daftar_rak', tanaman_id=tanaman.id)
    
    return render(request, 'rak_list.html', {
        'tanaman': tanaman,
        'kebun': tanaman.kebun,
        'raks': raks,
    })

@login_required
def edit_rak(request, rak_id):
    rak = get_object_or_404(Rak, id=rak_id, tanaman__kebun__user=request.user)
    
    if request.method == "POST":
        nama = request.POST.get('nama_rak')
        wa = request.POST.get('nomor_wa')
        key = request.POST.get('api_key')
        min_ph = request.POST.get('min_ph', '5.5')
        max_ph = request.POST.get('max_ph', '6.5')
        foto = request.FILES.get('foto')
        
        # Validasi API Key
        try:
            api_key_obj = APIKey.objects.get(api_key=key, status='active')
            rak.api_key = api_key_obj
        except APIKey.DoesNotExist:
            messages.error(request, f"API Key '{key}' tidak ditemukan atau tidak aktif.")
            return redirect('daftar_rak', tanaman_id=rak.tanaman.id)
            
        rak.nama_rak = nama
        rak.nomor_wa = wa
        rak.min_ph = float(min_ph)
        rak.max_ph = float(max_ph)
        
        if foto:
            foto_path = process_and_convert_image(foto, folder_name='rak_photos')
            if foto_path:
                rak.foto = foto_path
                
        rak.save()
        messages.success(request, f"Rak '{rak.nama_rak}' berhasil diperbarui!")
        
    return redirect('daftar_rak', tanaman_id=rak.tanaman.id)


@login_required
def monitoring_rak(request, rak_id):
    # Mengambil detail Rak dan data sensornya
    rak = get_object_or_404(Rak, id=rak_id, tanaman__kebun__user=request.user)
    data_logs = DataSensor.objects.filter(rak=rak).order_by('-timestamp')[:20]
    
    return render(request, 'monitoring.html', {
        'rak': rak, 
        'data_logs': data_logs
    })

@login_required
def update_interval(request, rak_id):
    rak = get_object_or_404(Rak, id=rak_id, tanaman__kebun__user=request.user)
    
    if request.method == "POST":
        menit = request.POST.get('menit')
        rak.deepsleep_menit = menit
        rak.save()
        
        # Kirim konfigurasi ke MQTT (Mode Publisher) dengan topic baru
        # Retain=True agar saat ESP32 bangun dari tidur, ia langsung menerima pesan ini
        topic = f"hydroponik/tanamanku/deepsleep/{rak.api_key.api_key}"
        try:
            publish.single(
                topic, 
                payload=str(menit), 
                hostname="broker.emqx.io", 
                retain=True,
                qos=1
            )
        except Exception as e:
            print(f"MQTT Publish Error: {e}")
            
    return redirect('monitoring_rak', rak_id=rak.id)

@login_required
def update_deepsleep_ajax(request, rak_id):
    """AJAX endpoint untuk update deepsleep interval"""
    rak = get_object_or_404(Rak, id=rak_id, tanaman__kebun__user=request.user)
    
    if request.method == "POST":
        menit = request.POST.get('menit')
        
        # Only publish to MQTT if value changed
        if str(rak.deepsleep_menit) != str(menit):
            rak.deepsleep_menit = int(menit)
            rak.save()
            
            # Kirim ke MQTT dengan topic baru
            topic = f"hydroponik/tanamanku/deepsleep/{rak.api_key.api_key}"
            try:
                publish.single(
                    topic, 
                    payload=str(menit), 
                    hostname="broker.emqx.io", 
                    retain=True,
                    qos=1
                )
                return JsonResponse({
                    'status': 'success',
                    'message': f'Deep Sleep updated to {menit} minutes',
                    'value': menit
                })
            except Exception as e:
                print(f"MQTT Publish Error: {e}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Failed to publish to MQTT: {str(e)}'
                }, status=500)
        else:
            return JsonResponse({
                'status': 'success',
                'message': 'No changes made',
                'value': menit
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def hapus_item(request, tipe, item_id):
    if tipe == 'kebun':
        Kebun.objects.filter(id=item_id, user=request.user).delete()
        return redirect('daftar_kebun')
    elif tipe == 'tanaman':
        tanaman = get_object_or_404(Tanaman, id=item_id, kebun__user=request.user)
        kebun_id = tanaman.kebun.id
        tanaman.delete()
        return redirect('daftar_tanaman', kebun_id=kebun_id)
    elif tipe == 'rak':
        rak = get_object_or_404(Rak, id=item_id, tanaman__kebun__user=request.user)
        tanaman_id = rak.tanaman.id
        rak.delete()
        return redirect('daftar_rak', tanaman_id=tanaman_id)
    return redirect('daftar_kebun')

@login_required
def hydro_ai_chat(request):
    if request.method == "POST":
        message = request.POST.get('message', '')
        
        # Get GEMINI_API_KEY from settings
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        
        # Check if configured and valid
        if api_key and api_key != 'ISI_API_KEY_GEMINI_DI_SINI':
            try:
                # Retrieve user's racks and latest sensor logs to create a RAG context
                raks = Rak.objects.filter(tanaman__kebun__user=request.user)
                rack_context_lines = []
                for r in raks:
                    latest_data = r.data_sensor.first()
                    if latest_data:
                        rack_context_lines.append(
                            f"- Rak: {r.nama_rak} | pH: {latest_data.ph:.1f} | TDS: {latest_data.tds:.0f} PPM | "
                            f"Suhu: {latest_data.suhu:.1f} C (Diupdate: {latest_data.timestamp.strftime('%d %b %Y, %H:%M')})"
                        )
                    else:
                        rack_context_lines.append(f"- Rak: {r.nama_rak} | (Belum ada data sensor masuk)")
                
                rack_context = "\n".join(rack_context_lines) if rack_context_lines else "Pengguna belum menambahkan rak apapun."
                
                # Initialize modern GenAI client
                client = genai.Client(api_key=api_key)
                
                system_prompt = (
                    "Anda adalah Hydro AI, asisten virtual pintar ahli berkebun hidroponik. "
                    "Tugas Anda adalah membantu pengguna dengan menjawab pertanyaan seputar tanaman, "
                    "nutrisi (TDS/PPM), pH air, suhu air nutrisi, penanganan hama, jenis media tanam, "
                    "dan seluruh topik pertanian/berkebun lainnya. "
                    "Jawablah dengan sopan, ramah, solutif, dan berwawasan ilmiah namun praktis dalam Bahasa Indonesia. "
                    "Jika ditanya di luar topik pertanian/hidroponik/tanaman, arahkan pengguna kembali dengan sopan ke topik hidroponik/pertanian.\n\n"
                    "Berikut adalah data sensor real-time dari rak hidroponik pengguna saat ini:\n"
                    f"{rack_context}\n\n"
                    "Gunakan data sensor ini untuk menjawab jika pengguna menanyakan status rak atau kondisi tanamannya. "
                    "Ketentuan ideal parameter hidroponik:\n"
                    "- pH Ideal: 5.5 - 6.5\n"
                    "- TDS Ideal: 800 - 1200 PPM (untuk selada/sayuran daun)\n"
                    "- Suhu Ideal: 20 C - 25 C (suhu air nutrisi)\n"
                    "Jika parameter di atas atau di bawah batas ideal, berikan saran pemulihan yang tepat."
                )
                
                response_obj = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=message,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    ),
                )
                response = response_obj.text
                return JsonResponse({'response': response})
            except Exception as e:
                print(f"Gemini API Error: {e}")
                # Fallback to static rules below
        
        # Fallback static rules if API key is not configured or fails
        message_lower = message.lower()
        response = "Halo! Saya Hydro AI, asisten hidroponik Anda. Ada yang bisa saya bantu?"
        
        if 'ph' in message_lower:
            response = "Nilai pH air ideal untuk hidroponik adalah 5.5 - 6.5. Jika pH terlalu tinggi, tanaman sulit menyerap nutrisi (larutan menjadi alkali), Anda bisa memberi larutan pH Down. Jika terlalu rendah, gunakan pH Up."
        elif 'tds' in message_lower or 'ppm' in message_lower or 'nutrisi' in message_lower:
            response = "Kadar nutrisi (TDS/PPM) bergantung pada usia dan jenis tanaman. Sayuran daun seperti selada memerlukan sekitar 800 - 1200 PPM. Sayuran buah seperti tomat memerlukan 1400 - 2000 PPM. Mulailah dengan PPM rendah untuk bibit muda."
        elif 'suhu' in message_lower or 'panas' in message_lower or 'dingin' in message_lower:
            response = "Suhu air nutrisi yang ideal adalah 20 C hingga 25 C. Suhu di atas 28 C dapat menghambat penyerapan oksigen akar, menyebabkan akar membusuk dan layu. Gunakan pelindung wadah agar tidak terpapar matahari langsung."
        elif 'kuning' in message_lower or 'layu' in message_lower or 'daun' in message_lower:
            response = "Daun menguning biasanya merupakan gejala kekurangan unsur hara (seperti Nitrogen atau Zat Besi) or disebabkan pH air yang tidak stabil. Cek dan stabilkan pH di kisaran 6.0, serta pastikan kepekatan PPM nutrisi Anda sudah sesuai."
        elif 'alat' in message_lower or 'kit' in message_lower or 'beli' in message_lower:
            response = "Anda bisa membeli Smart Hydro Detector Kit kami melalui menu 'Beli Alat Kit' di bagian atas halaman. Terdapat paket Lite dan Pro yang siap pasang!"
        else:
            response = "Saya saat ini berjalan dalam mode offline karena Gemini API belum dikonfigurasi. Anda dapat menanyakan tentang pH, TDS/PPM, Suhu Air, daun kuning/layu, atau cara membeli alat kit."
            
        return JsonResponse({'response': response})

    return render(request, 'hydro_ai.html')

@login_required
def beli_kit(request):
    return render(request, 'beli_kit.html')
