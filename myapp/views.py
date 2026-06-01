from django.db.models import Count 
from django.conf import settings
from django.contrib.auth.hashers import make_password
import json
import PyPDF2
from django.shortcuts import render, redirect, get_object_or_404
from .models import Material, Utilizator, Test, Intrebare, Clasa, RezultatTest
from groq import Groq  
from django.http import HttpResponse
from django.template.loader import get_template
from django.contrib import messages
import os

def loading_view(request):
    return render(request, 'HTML/loading.html')

from django.contrib.auth.hashers import check_password

def login_view(request):
    if request.method == "POST":
        email_introdus = request.POST.get('email')
        parola_introdusa = request.POST.get('parola')
        rol_selectat = request.POST.get('rol')

        try:
            user = Utilizator.objects.get(email=email_introdus)
            
            if check_password(parola_introdusa, user.parola):
                if user.rol == rol_selectat:
                    request.session.flush() 
                    
                    request.session['user_id'] = user.id
                    request.session['nume_utilizator'] = user.nume
                    
                    if user.rol == 'profesor':
                        return redirect('dashboard_profesor')
                    else:
                        return redirect('dashboard_elev')
                else:
                    return render(request, 'HTML/login.html', {
                        'eroare': f'Acest cont este înregistrat ca {user.rol}, nu ca {rol_selectat}!'
                    })
            else:
                return render(request, 'HTML/login.html', {
                    'eroare': 'Email sau parolă incorectă!'
                })

        except Utilizator.DoesNotExist:
            return render(request, 'HTML/login.html', {
                'eroare': 'Email sau parolă incorectă!'
            })

    return render(request, 'HTML/login.html')

def logout_view(request):
    request.session.flush() 
    return redirect('login')

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

        parola_criptata = make_password(parola)

        nou_utilizator = Utilizator(
            nume=nume,
            email=email,
            parola=parola_criptata, 
            rol=rol               
        )
        nou_utilizator.save()

        return redirect('login')

    return render(request, 'HTML/register.html')

def home_view(request):
    return render(request, 'HTML/home.html')

def dashboard_profesor_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
        
    user = Utilizator.objects.get(id=user_id)

    clase = Clasa.objects.filter(profesor=user).annotate(
        nr_studenti=Count('studenti')
    ).order_by('-id')

    return render(request, 'HTML/dashboard_profesor.html', {
        'clase': clase,
        'user': user
    })

def detalii_clasa(request, clasa_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    user = get_object_or_404(Utilizator, id=user_id)

    clasa = get_object_or_404(Clasa, id=clasa_id, profesor=user)

    materiale = clasa.materiale.all().order_by('-data_incarcarii')
    teste = clasa.teste.all().order_by('-creat_la')
    
    studenti = clasa.studenti.all() if hasattr(clasa, 'studenti') else []

    return render(request, 'HTML/detalii_clasa.html', {
        'clasa': clasa,
        'materiale': materiale,
        'teste': teste,
        'studenti': studenti,
        'user': user
    })

def creeaza_clasa(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
        
    try:
        user = Utilizator.objects.get(id=user_id)
        
        if user.rol != 'profesor':
            messages.error(request, "Doar profesorii pot crea clase!")
            return redirect('dashboard_elev')
            
    except Utilizator.DoesNotExist:
        request.session.flush()
        return redirect('login')

    if request.method == "POST":
        nume_materie = request.POST.get('nume_materie')
        specializare = request.POST.get('specializare')
        an_studiu = request.POST.get('an')

        if nume_materie and specializare and an_studiu:
            Clasa.objects.create(
                nume_materie=nume_materie,
                specializare=specializare,
                an_studiu=an_studiu,
                profesor=user  
            )
            messages.success(request, f"Clasa {nume_materie} a fost creată!")
            return redirect('dashboard_profesor')

    return render(request, 'HTML/creeaza_clasa.html')

def genereaza_intrebari_ai(text_extras):
    client = Groq(api_key="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")

    text_scurt = text_extras[:1500] 

    prompt = (
        f"Generează 10 întrebări grilă din următorul text: {text_scurt}. "
        "Răspunde EXCLUSIV cu un cod JSON valid, fără alt text înainte sau după. "
        "Formatul trebuie să fie o listă de obiecte de tipul: "
        "[{\"text\": \"întrebare\", \"A\": \"varianta\", \"B\": \"varianta\", \"C\": \"varianta\", \"D\": \"varianta\", \"corect\": \"A\"}]"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )

        continut = response.choices[0].message.content.strip()

        import re
        match = re.search(r'\[.*\]', continut, re.DOTALL)
        if match:
            json_string = match.group(0)
            return json.loads(json_string)
        else:
            continut = continut.replace('```json', '').replace('```', '').strip()
            return json.loads(continut)

    except Exception as e:
        print(f"Eroare Groq/Parsing: {e}")
        return []

def incarcare_material(request, clasa_id):
    user_id = request.session.get('user_id')
    if not user_id: 
        return redirect('login')
    
    try:
        user = Utilizator.objects.get(id=user_id)
    except Utilizator.DoesNotExist:
        return redirect('login')

    clasa = get_object_or_404(Clasa, id=clasa_id, profesor=user)

    if request.method == "POST":
        titlu = request.POST.get('titlu')
        fisier = request.FILES.get('fisier_pdf') 

        if not titlu or not fisier:
            return render(request, 'HTML/incarcare_material.html', {
                'eroare': 'Te rog completează titlul și alege un fișier!',
                'clasa': clasa
            })

        print(f"--- Începe procesarea pentru: {titlu} (Clasa: {clasa.nume_materie}) ---")
        
        material = Material.objects.create(
            titlu=titlu, 
            fisier_pdf=fisier, 
            autor=user,
            clasa=clasa  
        )
        print("Material salvat în baza de date.")

        try:
            with open(material.fisier_pdf.path, 'rb') as pdf_file:
                cititor = PyPDF2.PdfReader(pdf_file)
                text_complet = ""
                for i in range(min(3, len(cititor.pages))):
                    text_complet += cititor.pages[i].extract_text() or ""
                
                if not text_complet.strip():
                    print("Eroare: Nu s-a putut extrage text din PDF.")
                    return render(request, 'HTML/incarcare_material.html', {
                        'eroare': 'PDF-ul pare gol sau necitibil.',
                        'clasa': clasa
                    })

                print(f"Text extras cu succes ({len(text_complet)} caractere).")

                noul_test = Test.objects.create(
                    titlu=f"Test: {material.titlu}", 
                    material_sursa=material, 
                    autor=user,
                    clasa=clasa 
                )
                
                print("Se procesează textul prin AI...")
                lista_intrebari = genereaza_intrebari_ai(text_complet)
                
                if not lista_intrebari:
                    print("Eroare: nu s-a returnat nicio întrebare.")
                    return render(request, 'HTML/incarcare_material.html', {
                        'eroare': 'Nu s-au putut genera întrebări. Verifică serviciul AI!',
                        'clasa': clasa
                    })

                for item in lista_intrebari:
                    Intrebare.objects.create(
                        test=noul_test,
                        text_intrebare=item.get('text', 'Întrebare lipsă'),
                        varianta_a=item.get('A', '-'),
                        varianta_b=item.get('B', '-'),
                        varianta_c=item.get('C', '-'),
                        varianta_d=item.get('D', '-'),
                        raspuns_corect=item.get('corect', 'A')
                    )
                print(f"Succes! S-au salvat {len(lista_intrebari)} întrebări.")

        except Exception as e:
            print(f"Eroare critică la procesare: {e}")
            return render(request, 'HTML/incarcare_material.html', {
                'eroare': f'Eroare tehnică: {str(e)}',
                'clasa': clasa
            })

        return redirect('detalii_clasa', clasa_id=clasa.id)

    return render(request, 'HTML/incarcare_material.html', {'clasa': clasa})

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

import datetime

def export_pdf(request, test_id):
    test = Test.objects.get(pk=test_id)
    intrebari = Intrebare.objects.filter(test=test)
    varianta = request.GET.get('varianta', 'elev')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Test_{test.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    latime, inaltime = A4
    y = inaltime - 50 

    path_font = os.path.join(settings.BASE_DIR, 'LearnEffix', 'fonts', 'DejaVuSans.ttf')
    pdfmetrics.registerFont(TTFont('DejaVu', path_font))

    p.setFont("DejaVu", 10)
    p.drawString(50, y, "Nume și prenume: ________________________________")
    p.drawString(400, y, "Clasa: ________")
    y -= 20
    p.drawString(50, y, f"Data: {datetime.date.today().strftime('%d.%m.%Y')}")
    p.drawString(400, y, "Punctaj: ________")
    y -= 15
    p.line(50, y, latime-50, y)
    y -= 35

    p.setFont("DejaVu", 16)
    titlu_curat = test.titlu.replace("Test: ", "")
    p.drawCentredString(latime/2, y, f"TEST: {titlu_curat.upper()}")
    y -= 40

    p.setFont("DejaVu", 11)
    for index, i in enumerate(intrebari, 1):
        if y < 150:
            p.showPage()
            y = inaltime - 50
        
        p.setFont("DejaVu", 11)
        p.drawString(50, y, f"{index}. {i.text_intrebare}")
        y -= 20
        
        p.setFont("DejaVu", 10)
        p.drawString(70, y, f"a) {i.varianta_a}")
        y -= 15
        p.drawString(70, y, f"b) {i.varianta_b}")
        y -= 15
        p.drawString(70, y, f"c) {i.varianta_c}")
        y -= 15
        p.drawString(70, y, f"d) {i.varianta_d}")
        y -= 25

        if varianta == 'profesor':
            p.drawString(70, y, f"Răspuns corect: {i.raspuns_corect}")
            y -= 25
        y -= 10

    p.showPage()
    p.save()
    return response

def detalii_test(request, test_id):
    test = Test.objects.get(id=test_id)
    intrebari = test.intrebari.all()
    
    mod_vizualizare = request.GET.get('mod', 'elev') 

    context = {
        'test': test,
        'intrebari': intrebari,
        'varianta': mod_vizualizare,
    }
    return render(request, 'HTML/detalii_test.html', context)

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

def sterge_test(request, test_id):
    test = get_object_or_404(Test, pk=test_id)
    clasa_id = test.clasa.id
    test.delete()
    messages.success(request, "Testul a fost șters cu succes!")
    return redirect('detalii_clasa', clasa_id=clasa_id)

def sterge_material(request, material_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    material = get_object_or_404(Material, id=material_id, autor_id=user_id)
    clasa_id = material.clasa.id 
    
    if request.method == "POST":
        material.delete()
        messages.success(request, "Materialul a fost șters!")
        return redirect('detalii_clasa', clasa_id=clasa_id)

    return redirect('detalii_clasa', clasa_id=clasa_id)


def editare_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    intrebari = test.intrebari.all()

    if request.method == "POST":
        for intrebare in intrebari:
            prefix = f"intrebare_{intrebare.id}_"
            
            intrebare.text_intrebare = request.POST.get(f"{prefix}text")
            intrebare.varianta_a = request.POST.get(f"{prefix}a")
            intrebare.varianta_b = request.POST.get(f"{prefix}b")
            intrebare.varianta_c = request.POST.get(f"{prefix}c")
            intrebare.varianta_d = request.POST.get(f"{prefix}d")
            intrebare.raspuns_corect = request.POST.get(f"{prefix}corect")
            intrebare.save()
            
        messages.success(request, "Testul a fost actualizat cu succes!")
        return redirect('detalii_test', test_id=test.id)

    return render(request, 'HTML/editare_test.html', {'test': test, 'intrebari': intrebari})


def dashboard_elev(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
        
    try:
        student = Utilizator.objects.get(id=user_id)
        if student.rol != 'elev':
            return redirect('dashboard_profesor')
    except Utilizator.DoesNotExist:
        request.session.flush()
        return redirect('login')
    
    clase = student.clase_inrolate.all()
    rezultate = RezultatTest.objects.filter(student=student).order_by('-data_finalizarii')
    
    total_teste = rezultate.count()
    if total_teste > 0:
        media = sum(r.punctaj for r in rezultate) / total_teste
    else:
        media = 0

    return render(request, 'HTML/dashboard.html', {
        'clase': clase,
        'rezultate': rezultate,
        'total_teste': total_teste,
        'media_scor': round(media, 2)
    })


def inrolare_clasa(request):
    if request.method == "POST":
        cod = request.POST.get('cod_inrolare')
        user_id = request.session.get('user_id')
        
        try:
            clasa = Clasa.objects.get(cod_inrolare=cod)
            student = Utilizator.objects.get(id=user_id)
            
            if student in clasa.studenti.all():
                messages.warning(request, "Ești deja înrolat în această clasă!")
            else:
                clasa.studenti.add(student)
                messages.success(request, f"Te-ai înrolat cu succes la {clasa.nume_materie}!")
                
        except Clasa.DoesNotExist:
            messages.error(request, "Codul introdus este invalid. Verifică-l și încearcă din nou.")
            
    return redirect('dashboard')

def detalii_clasa_elev(request, clasa_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    clasa = get_object_or_404(Clasa, id=clasa_id)
    
    if not clasa.studenti.filter(id=user_id).exists():
        messages.error(request, "Nu ai acces la această clasă. Te rugăm să te înrolezi mai întâi.")
        return redirect('dashboard_elev')

    materiale = clasa.materiale.all() 
    teste = clasa.teste.all() 
    
    return render(request, 'HTML/detalii_clasa_elev.html', {
        'clasa': clasa,
        'materiale': materiale,
        'teste': teste
    })

def calculeaza_rezultat(request, test_id):
    if request.method == "POST":
        test = get_object_or_404(Test, id=test_id)
        user_id = request.session.get('user_id')
        student = get_object_or_404(Utilizator, id=user_id)
        
        intrebari = test.intrebari.all()
        raspunsuri_corecte = 0
        total_intrebari = intrebari.count()
        
        istoric_raspunsuri = []

        for intrebare in intrebari:
            raspuns_elev = request.POST.get(f'intrebare_{intrebare.id}')
            
            este_corect = (raspuns_elev == intrebare.raspuns_corect)
            if este_corect:
                raspunsuri_corecte += 1
                
            istoric_raspunsuri.append({
                'intrebare': intrebare,
                'raspuns_elev': raspuns_elev if raspuns_elev else "Niciun răspuns",
                'este_corect': este_corect,
                'text_raspuns_elev': getattr(intrebare, f'varianta_{raspuns_elev.lower()}') if raspuns_elev else "Nespecificat",
                'text_raspuns_corect': getattr(intrebare, f'varianta_{intrebare.raspuns_corect.lower()}')
            })

        nota = (raspunsuri_corecte / total_intrebari) * 10 if total_intrebari > 0 else 0
        nota_finala = round(nota, 2)
        
        RezultatTest.objects.create(
            student=student,
            test=test,
            punctaj=nota_finala
        )

        context = {
            'test': test,
            'nota': nota_finala,
            'raspunsuri_corecte': raspunsuri_corecte,
            'total_intrebari': total_intrebari,
            'istoric_raspunsuri': istoric_raspunsuri
        }
        return render(request, 'HTML/rezultat_test.html', context)
        
    return redirect('dashboard')
    
def sustine_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    return render(request, 'HTML/sustine_test.html', {'test': test})