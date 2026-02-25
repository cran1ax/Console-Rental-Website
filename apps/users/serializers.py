from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers

from .models import User, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "id_proof_type",
            "id_proof_number",
            "stripe_customer_id",
        ]
        read_only_fields = ["stripe_customer_id"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone_number",
            "address",
            "avatar",
            "is_verified",
            "date_joined",
            "profile",
        ]
        read_only_fields = ["id", "email", "is_verified", "date_joined"]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "phone_number", "address", "avatar"]


class CustomRegisterSerializer(RegisterSerializer):
    username = None
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=17, required=False, allow_blank=True)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data.update(
            {
                "full_name": self.validated_data.get("full_name", ""),
                "phone_number": self.validated_data.get("phone_number", ""),
            }
        )
        return data

    def save(self, request):
        user = super().save(request)
        user.full_name = self.cleaned_data.get("full_name", "")
        user.phone_number = self.cleaned_data.get("phone_number", "")
        user.save(update_fields=["full_name", "phone_number"])
        return user
