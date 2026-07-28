from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

User = get_user_model()


class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
        )

    def test_user_creation(self):
        self.assertEqual(self.user.email, "test@example.com")
        self.assertTrue(self.user.check_password("testpass123"))

    def test_user_str_returns_email(self):
        self.assertEqual(str(self.user), "test@example.com")

    def test_user_email_unique(self):
        with self.assertRaises(Exception):
            User.objects.create_user(
                email="test@example.com",
                username="another",
                password="pass123",
            )

    def test_user_default_is_not_staff(self):
        self.assertFalse(self.user.is_staff)

    def test_user_default_is_active(self):
        self.assertTrue(self.user.is_active)


class RegisterViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("register")

    def test_register_success(self):
        data = {
            "email": "new@example.com",
            "username": "newuser",
            "password": "securepass123",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "new@example.com")
        self.assertNotIn("password", response.data)

    def test_register_missing_fields(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email="dup@example.com",
            username="user1",
            password="pass123",
        )
        data = {
            "email": "dup@example.com",
            "username": "user2",
            "password": "pass123",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password(self):
        data = {
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "123",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("profile")
        self.user = User.objects.create_user(
            email="profile@example.com",
            username="profileuser",
            password="pass123",
        )

    def test_profile_get_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "profile@example.com")

    def test_profile_patch_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url, {"first_name": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated")

    def test_profile_patch_unauthenticated(self):
        response = self.client.patch(
            self.url, {"first_name": "Hacker"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
