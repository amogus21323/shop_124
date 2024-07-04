import logging

from django.contrib.auth import get_user_model, authenticate, login
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views import View
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.response import Response
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from account.send_email import send_confirmation_email, send_confirmation_password
from shop_ada.tasks import send_confirmation_email_task, send_confirmation_password_task
from account.serializers import (
    RegistrationSerializer,
    ActivationSerializer,
    ConfirmPasswordSerializer,
    ResetPasswordSerializer,
    RegistrationPhoneSerializer,
)

User = get_user_model()
logger = logging.getLogger("account")


class RegistrationView(APIView):
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if user:
            try:
                # send_confirmation_email(email=user.email, code=user.activation_code)
                send_confirmation_email_task.delay(
                    email=user.email, code=user.activation_code
                )
                logger.info(
                    f"User {user.email} был зарегистрирован и сообщение было отправлено на почту"
                )
            except:
                logger.error(f"Ошибка при отправке активационного кода на почту")
                return Response(
                    {
                        "message": "Зарегистрировался но на почту код не отправился",
                        "data": serializer.data,
                    },
                    status=201,
                )
        return Response(serializer.data, status=201)


class ActivationView(GenericAPIView):
    serializer_class = ActivationSerializer

    def get(self, request):
        code = request.GET.get("u")
        user = get_object_or_404(User, activation_code=code)
        user.is_active = True
        user.activation_code = ""
        user.save()
        return Response("Успешно активирован", status=200)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("Успешно активирован", status=200)


class LoginView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            logger.info(f'User {request.data.get("email")} успешно вошел на сайт')
        else:
            logger.warning(f"Ошибка при входе на сайт")
        return response


class RegistrationTemplateView(APIView):
    template_name = "account/registration.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if user:
                try:
                    # send_confirmation_email(user.email, user.activation_code)
                    send_confirmation_email_task.delay(user.email, user.activation_code)
                    return redirect("activation")
                except:
                    return Response(
                        {"message": "Зарегистрировался но на почту код не отправился"},
                        status=201,
                    )
        else:
            return render(request, self.template_name, {"errors": serializer.errors})


def activation_view(request):
    return render(request, "account/activation.html")


class LoginTemplateView(View):
    template_name = "account/login.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get("email")
        password = request.POST.get("password")
        if not email or not password:
            return render(
                request,
                self.template_name,
                {"error": "Email and password are required"},
            )
        user = authenticate(request, email=email, password=password)
        if user:
            login(request, user)
            token_view = TokenObtainPairView.as_view()
            token_response = token_view(request)
            if token_response.status_code == status.HTTP_200_OK:
                return HttpResponseRedirect(
                    reverse("dashboard") + f'?token={token_response.data["access"]}'
                )
        else:
            return render(request, self.template_name, {"error": "Invalid data"})
        return render(request, self.template_name)


class DashboardView(View):
    template_name = "account/dashboard.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        action = request.POST.get("action", None)

        if action == "login":
            return redirect("login")
        elif action == "register":
            return redirect("registration")
        else:
            return render(request, self.template_name, {"error": "Invalid action"})


class ResetPasswordView(APIView):
    def get(self, request):
        return Response({"message": "Please provide an email to reset the password"})

    def post(self, request):
        serializer = ConfirmPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            try:
                user = User.objects.get(email=email)
                user.create_activation_code()
                user.save()
                # send_confirmation_password(user.email, user.activation_code)
                send_confirmation_password_task.delay(user.email, user.activation_code)
                return Response({"activation_code": user.activation_code}, status=200)
            except:
                return Response(
                    {"message": "User with this email does not exist"}, status=404
                )
        return Response(serializer.errors, status=400)


class ResetPasswordConfirm(APIView):
    def post(self, request):
        code = request.GET.get("u")
        user = get_object_or_404(User, activation_code=code)
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data["new_password"]
        user.set_password(new_password)
        user.activation_code = ""
        user.save()
        return Response("Your password has been successfully updated", status=200)


class RegistrationPhoneView(APIView):
    def post(self, request):
        data = request.data
        serializer = RegistrationPhoneSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response("Успешно зарегистрирован", status=201)
