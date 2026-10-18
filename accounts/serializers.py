from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import exceptions, serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "phone_number", "role"]
        read_only_fields = ["id", "email", "username", "phone_number", "role"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "phone_number"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        normalized_email = value.lower().strip()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return normalized_email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        # Force default DRIVER role to prevent role escalation
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            phone_number=validated_data.get("phone_number", ""),
            role=User.Role.DRIVER,
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )
        if not user:
            # Fallback for backends checking username keyword
            user = authenticate(
                request=self.context.get("request"),
                username=email,
                password=password,
            )

        if not user:
            raise exceptions.AuthenticationFailed("Invalid email or password.")

        if not user.is_active:
            raise exceptions.AuthenticationFailed("User account is disabled.")

        attrs["user"] = user
        return attrs
