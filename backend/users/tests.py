import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from django.urls import reverse
from model_bakery import baker

User = get_user_model()


class TestUserModel:
    def test_user_creation(self, user):
        assert user.email == "test@example.com"
        assert user.check_password is not None

    def test_user_str_returns_email(self, user):
        assert str(user) == "test@example.com"

    def test_user_email_unique(self, db):
        baker.make(User, email="dup@example.com")
        with pytest.raises(Exception):
            baker.make(User, email="dup@example.com")

    def test_user_default_is_not_staff(self, user):
        assert not user.is_staff

    def test_user_default_is_active(self, user):
        assert user.is_active


class TestRegisterView:
    URL = reverse("register")

    def test_register_success(self, db, api_client):
        data = {"email": "new@example.com", "username": "newuser", "password": "securepass123"}
        response = api_client.post(self.URL, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "new@example.com"
        assert "password" not in response.data

    def test_register_missing_fields(self, api_client):
        response = api_client.post(self.URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, user):
        data = {"email": user.email, "username": "user2", "password": "pass123"}
        response = api_client.post(self.URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, db, api_client):
        data = {"email": "weak@example.com", "username": "weakuser", "password": "123"}
        response = api_client.post(self.URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestProfileView:
    URL = reverse("profile")

    def test_profile_get_unauthenticated(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_profile_get_authenticated(self, authenticated_client):
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK

    def test_profile_patch_success(self, authenticated_client):
        response = authenticated_client.patch(self.URL, {"first_name": "Updated"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"

    def test_profile_patch_unauthenticated(self, api_client):
        response = api_client.patch(self.URL, {"first_name": "Hacker"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
