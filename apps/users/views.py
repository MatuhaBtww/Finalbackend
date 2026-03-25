from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.models import AccessRight, Role, User
from apps.users.permissions import IsAdminOrSelf, IsAuthenticatedReadOnlyOrAdmin, get_role_name
from apps.users.serializers import (
    AccessRightSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    RoleSerializer,
    UserSerializer,
)


class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrAdmin]


class AccessRightViewSet(ModelViewSet):
    queryset = AccessRight.objects.select_related("role").all()
    serializer_class = AccessRightSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrAdmin]


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = User.objects.select_related("role").all().order_by("full_name", "username")
        role_name = self.request.query_params.get("role")
        role_id = self.request.query_params.get("role_id")
        if role_name:
            queryset = queryset.filter(role__role_name__iexact=role_name)
        if role_id:
            queryset = queryset.filter(role_id=role_id)
        if get_role_name(self.request.user) != "admin":
            queryset = queryset.filter(pk=self.request.user.pk)
        return queryset

    def get_permissions(self):
        if self.action in {"list", "create", "destroy"}:
            return [IsAuthenticatedReadOnlyOrAdmin()]
        return [IsAuthenticated(), IsAdminOrSelf()]


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        client_role = Role.objects.filter(role_name__iexact="client").first()
        serializer.save(role=client_role)


class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return Response({"detail": "Logout on JWT is handled client-side by deleting the access token."})


class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
