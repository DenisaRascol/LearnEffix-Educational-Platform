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

    materiale = clasa.materiale.exclude(titlu__startswith="[Sursă Test]").order_by('-data_incarcarii')
    
    teste = clasa.teste.all().order_by('-creat_la')
    studenti = clasa.studenti.all() if hasattr(clasa, 'studenti') else []

    return render(request, 'HTML/detalii_clasa.html', {
        'clasa': clasa,
        'materiale': materiale,
        'teste': teste,
        'studenti': studenti,
        'user': user
    })


def adauga_nota_manual(request, clasa_id):
    user_id = request.session.get('user_id')
    if not user_id or request.method != "POST":
        return redirect('login')
        
    clasa = get_object_or_404(Clasa, id=clasa_id, profesor__id=user_id)
    student_id = request.POST.get('student_id')
    valoare_nota = request.POST.get('valoare')
    tip_nota = request.POST.get('tip')
    
    student = get_object_or_404(Utilizator, id=student_id, rol='elev')
    
    from .models import Nota
    Nota.objects.create(
        student=student,
        clasa=clasa,
        valoare=int(valoare_nota),
        tip=tip_nota
    )
    
    messages.success(request, f"Nota {valoare_nota} a fost adăugată cu succes pentru {student.nume}!")
    return redirect('catalog_clasa', clasa_id=clasa.id)

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
    client = Groq(api_key="GROQ_API_KEY_HERE")

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

        print(f"--- Începe generarea testului pentru: {titlu} ---")
      
        material = Material.objects.create(
            titlu=f"[Sursă Test] {titlu}", 
            fisier_pdf=fisier, 
            autor=user,
            clasa=clasa  
        )

        try:
            with open(material.fisier_pdf.path, 'rb') as pdf_file:
                cititor = PyPDF2.PdfReader(pdf_file)
                text_complet = ""
                for i in range(min(3, len(cititor.pages))):
                    text_complet += cititor.pages[i].extract_text() or ""
                
                if not text_complet.strip():
                    material.delete() 
                    return render(request, 'HTML/incarcare_material.html', {
                        'eroare': 'PDF-ul pare gol sau necitibil.',
                        'clasa': clasa
                    })

                noul_test = Test.objects.create(
                    titlu=titlu, 
                    material_sursa=material, 
                    autor=user,
                    clasa=clasa 
                )
                
                lista_intrebari = genereaza_intrebari_ai(text_complet)
                
                if not lista_intrebari:
                    noul_test.delete()
                    material.delete()
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

        except Exception as e:
            print(f"Eroare critică la procesare: {e}")
            return render(request, 'HTML/incarcare_material.html', {
                'eroare': f'Eroare tehnică: {str(e)}',
                'clasa': clasa
            })

        return redirect('detalii_clasa', clasa_id=clasa.id)

    return render(request, 'HTML/incarcare_material.html', {'clasa': clasa})


def doar_incarcare_material(request, clasa_id):
    
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

        Material.objects.create(
            titlu=titlu, 
            fisier_pdf=fisier, 
            autor=user,
            clasa=clasa  
        )
        messages.success(request, f"Materialul '{titlu}' a fost încărcat cu succes!")
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
from django.db.models import Avg

def sterge_test(request, test_id):
    test = get_object_or_404(Test, pk=test_id)
    clasa = test.clasa

    studenti_clasa = clasa.studenti.all() 
    
    test.delete()
    
    for student in studenti_clasa:
        note_ramase = Nota.objects.filter(student=student, clasa=clasa)
        
        if note_ramase.exists():
            media_noua = note_ramase.aggregate(Avg('valoare'))['valoare__avg']
            student.media = round(media_noua, 2)
        else:
            student.media = 0.0 
        
        student.save() 
        
    messages.success(request, "Testul a fost șters cu succes!")
    return redirect('detalii_clasa', clasa_id=clasa.id)


def sterge_material(request, material_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    material = get_object_or_404(Material, id=material_id)
    clasa_id = material.clasa.id 

    if material.clasa.profesor.id != user_id:
        messages.error(request, "Nu ai permisiunea să ștergi materiale din această clasă!")
        return redirect('detalii_clasa', clasa_id=clasa_id)
    
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

    materiale = clasa.materiale.exclude(titlu__startswith="[Sursă Test]").order_by('-data_incarcarii')
    
    teste = clasa.teste.all() 
    
    return render(request, 'HTML/detalii_clasa_elev.html', {
        'clasa': clasa,
        'materiale': materiale,
        'teste': teste
    })
    

def sustine_test(request, test_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
        
    test = get_object_or_404(Test, id=test_id)
    student = get_object_or_404(Utilizator, id=user_id)
    
    if RezultatTest.objects.filter(student=student, test=test).exists():
        messages.warning(request, "Nu poți reface acest test. Permisiunea este de o singură încercare!")
        return redirect('detalii_clasa_elev', clasa_id=test.clasa.id)
        
    return render(request, 'HTML/sustine_test.html', {'test': test})


def calculeaza_rezultat(request, test_id):
    if request.method == "POST":
        test = get_object_or_404(Test, id=test_id)
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('login')
            
        student = get_object_or_404(Utilizator, id=user_id)
        
        if RezultatTest.objects.filter(student=student, test=test).exists():
            messages.error(request, "Ai susținut deja acest test! Nota ta a fost deja înregistrată.")
            return redirect('detalii_clasa_elev', clasa_id=test.clasa.id)
        
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
        
        nota_catalog = round(nota_finala)
        if nota_catalog < 1: 
            nota_catalog = 1  
            
        from .models import Nota
        Nota.objects.create(
            student=student,
            clasa=test.clasa,
            valoare=nota_catalog,
            tip='TEST'
        )

        context = {
            'test': test,
            'nota': nota_finala,
            'raspunsuri_corecte': raspunsuri_corecte,
            'total_intrebari': total_intrebari,
            'istoric_raspunsuri': istoric_raspunsuri
        }
        return render(request, 'HTML/rezultat_test.html', context)
        
    return redirect('dashboard_elev')


from django.db.models import Avg
from .models import Nota

def catalog_clasa(request, clasa_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
        
    user = get_object_or_404(Utilizator, id=user_id)
    clasa = get_object_or_404(Clasa, id=clasa_id, profesor=user)
    studenti = clasa.studenti.all()

    from django.db.models import Avg
    from .models import Nota

    for student in studenti:
        student.note_clasa = Nota.objects.filter(student=student, clasa=clasa).order_by('-id')
        media_calc = Nota.objects.filter(student=student, clasa=clasa).aggregate(Avg('valoare'))['valoare__avg']
        student.media = round(media_calc, 2) if media_calc else "-"

    return render(request, 'HTML/catalog_clasa.html', {
        'clasa': clasa,
        'studenti': studenti,
        'user': user
    })

def editeaza_nota(request, clasa_id):
    user_id = request.session.get('user_id')
    if not user_id or request.method != "POST":
        return redirect('login')
        
    clasa = get_object_or_404(Clasa, id=clasa_id, profesor__id=user_id)
    nota_id = request.POST.get('nota_id')
    noua_valoare = request.POST.get('noua_valoare')
    
    from .models import Nota
    nota = get_object_or_404(Nota, id=nota_id, clasa=clasa)
    
    valoare_veche = nota.valoare
    nota.valoare = int(noua_valoare)
    nota.save()
    
    messages.success(request, f"Nota studentului {nota.student.nume} a fost modificată cu succes din {valoare_veche} în {noua_valoare}!")
    return redirect('catalog_clasa', clasa_id=clasa.id)

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Avg
from .models import Nota, Clasa

def sterge_nota(request, clasa_id):
    if request.method == "POST":
        nota_id = request.POST.get("nota_id")
        nota = get_object_or_404(Nota, id=nota_id)
        student = nota.student
        clasa = nota.clasa
        
        nota.delete()
        
        note_ramase = Nota.objects.filter(student=student, clasa=clasa)
        if note_ramase.exists():
            media_noua = note_ramase.aggregate(Avg('valoare'))['valoare__avg']
            student.media = round(media_noua, 2)
        else:
            student.media = 0.0
            
        student.save()
        messages.success(request, "Nota a fost ștearsă cu succes, iar media a fost recalculată!")
        
    return redirect('catalog_clasa', clasa_id=clasa_id)

def catalog_student(request):
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
    
    clase_inrolate = student.clase_inrolate.all()
    
    situatii_materii = []
    
    for clasa in clase_inrolate:
        note_materie = Nota.objects.filter(student=student, clasa=clasa).order_by('-id')
        
        media_calc = note_materie.aggregate(Avg('valoare'))['valoare__avg']
        media_finala = round(media_calc, 2) if media_calc else "-"
        
        for n in note_materie:
            if n.tip == 'TEST':
                n.tip_evaluare = 'Test Online'
            else:
                n.tip_evaluare = 'Nota acordată manual'
        
        situatii_materii.append({
            'clasa': clasa,
            'media': media_finala,
            'note': note_materie
        })
        
    return render(request, 'HTML/catalog_student.html', {
        'situatii_materii': situatii_materii
    })

def sterge_clasa(request, clasa_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
        
    clasa = get_object_or_404(Clasa, id=clasa_id, profesor__id=user_id)
    
    if request.method == "POST":
        nume_clasa = clasa.nume_materie
        clasa.delete()
        messages.success(request, f"Clasa '{nume_clasa}' a fost ștearsă cu succes!")
        
    return redirect('dashboard_profesor')