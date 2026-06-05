from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views

def home(request):
    return redirect('/coa/')

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('coa/', include('coa.urls')),
    path('<int:coa_id>/download-word/', views.download_coa_word, name='download_coa_word'),
]
