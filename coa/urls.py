from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

def home(request):
    if request.user.is_authenticated:
        return redirect('/coa/')
    return redirect('/login/')

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='/login/',
    ), name='logout'),
    path('coa/', include('coa.urls')),
]