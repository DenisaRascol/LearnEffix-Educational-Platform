from django.shortcuts import render, redirect
from .models import Utilizator

def loading_view(request):
    return render(request, 'HTML/loading.html')

def login_view(request):
    if request.method == "POST":
        email_introdus = request.POST.get('email')
        parola_introdusa = request.POST.get('parola')
        rol_selectat = request.POST.get('rol')

        try:
            user = Utilizator.objects.get(email=email_introdus, parola=parola_introdusa)
            
            if user.rol == rol_selectat:
                if user.rol == 'profesor':
                    return redirect('dashboard_profesor')
                else:
                    return redirect('dashboard')
            else:
                return render(request, 'HTML/login.html', {
                    'eroare': f'Acest cont este înregistrat ca {user.rol}, nu ca {rol_selectat}!'
                })

        except Utilizator.DoesNotExist:
            return render(request, 'HTML/login.html', {
                'eroare': 'Email sau parolă incorectă!'
            })

    return render(request, 'HTML/login.html')

def register_view(request):
    if request.method == "POST":
        nume = request.POST.get('nume')
        email = request.POST.get('email')
        parola = request.POST.get('password')
        confirm_parola = request.POST.get('confirm_password')
        rol = request.POST.get('role')

        if parola != confirm_parola:
            return render(request, 'HTML/register.html', {'eroare': 'Parolele nu coincid!'})

        if Utilizator.objects.filter(email=email).exists():
            return render(request, 'HTML/register.html', {'eroare': 'Acest email este deja utilizat!'})

        nou_utilizator = Utilizator(
            nume=nume,
            email=email,
            parola=parola, 
        )
        nou_utilizator.save()

        return redirect('login')

    return render(request, 'HTML/register.html')

def home_view(request):
    return render(request, 'HTML/home.html')

def dashboard_view(request):
    return render(request, 'HTML/dashboard.html')

def dashboard_profesor_view(request):
    return render(request, 'HTML/dashboard_profesor.html')  