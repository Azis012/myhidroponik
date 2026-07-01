from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail

class AuthFlowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='TestPassword123!'
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login.html')
        self.assertContains(response, 'Lupa password?')

    def test_register_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/register.html')

    def test_register_otp_flow(self):
        # 1. Post registration data (email is required in our custom form)
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'NewPassword123!',
            'password2': 'NewPassword123!'
        })
        # Check redirect to verify_otp
        self.assertRedirects(response, reverse('verify_otp'))
        
        # 2. User should be created but inactive
        new_user = User.objects.get(username='newuser')
        self.assertFalse(new_user.is_active)
        
        # 3. Check OTP email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['newuser@example.com'])
        self.assertIn('Kode OTP Registrasi', email.subject)
        
        # 4. Submit correct OTP
        session = self.client.session
        otp_code = session.get('otp_code')
        self.assertIsNotNone(otp_code)
        
        response = self.client.post(reverse('verify_otp'), {
            'otp': otp_code
        })
        # Redirects to dashboard/daftar_kebun upon success
        self.assertRedirects(response, reverse('daftar_kebun'))
        
        # 5. User should now be active
        new_user.refresh_from_db()
        self.assertTrue(new_user.is_active)

    def test_password_reset_otp_flow(self):
        # 1. Request reset link
        response = self.client.post(reverse('password_reset'), {
            'email': 'testuser@example.com'
        })
        self.assertRedirects(response, reverse('verify_otp'))
        
        # 2. Check email sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['testuser@example.com'])
        self.assertIn('Kode OTP Reset Password', email.subject)
        
        # 3. Verify OTP
        session = self.client.session
        otp_code = session.get('otp_code')
        self.assertIsNotNone(otp_code)
        
        response = self.client.post(reverse('verify_otp'), {
            'otp': otp_code
        })
        self.assertRedirects(response, reverse('password_reset_confirm_otp'))
        
        # 4. Submit new password
        response = self.client.post(reverse('password_reset_confirm_otp'), {
            'password': 'NewResetPassword123!',
            'confirm_password': 'NewResetPassword123!'
        })
        self.assertRedirects(response, reverse('password_reset_complete'))
        
        # 5. Check login with new password works
        login_success = self.client.login(username='testuser', password='NewResetPassword123!')
        self.assertTrue(login_success)


from unittest.mock import patch
from monitor.models import Kebun, Tanaman, Rak, APIKey
from monitor.whatsapp_helper import send_wa_notification

class HydroponicEWSTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser2',
            email='testuser2@example.com',
            password='TestPassword123!'
        )
        self.kebun = Kebun.objects.create(user=self.user, nama="Kebun Uji")
        self.tanaman = Tanaman.objects.create(kebun=self.kebun, nama="Selada Hidro")
        self.api_key = APIKey.objects.create(api_key="API-TEST-999", nama_alat="Test Device")
        self.rak = Rak.objects.create(
            tanaman=self.tanaman,
            nama_rak="Rak A",
            api_key=self.api_key,
            nomor_wa="628123456789",
            min_ph=5.5,
            max_ph=6.5
        )

    def test_rak_creation_limits(self):
        self.assertEqual(self.rak.min_ph, 5.5)
        self.assertEqual(self.rak.max_ph, 6.5)
        self.assertIsNone(self.rak.last_notification_sent)

    @patch('requests.post')
    def test_send_wa_notification_normalization(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'status': True, 'message': 'sent'}
        
        # Test number normalization from '0812...' to '62812...'
        result = send_wa_notification("08123456789", "Test Alert")
        self.assertTrue(result)
        mock_post.assert_called_with(
            'http://127.0.0.1:3000/send',
            json={'number': '628123456789', 'message': 'Test Alert'},
            timeout=10
        )

