import json
import PyPDF2
from django.shortcuts import render, redirect
from .models import Material, Utilizator, Test, Intrebare
from groq import Groq  

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
                request.session['user_id'] = user.id
                
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
    user_id = request.session.get('user_id')
    user = Utilizator.objects.get(id=user_id)
    
    teste = Test.objects.filter(material_sursa__autor=user).order_by('-creat_la')
    
    return render(request, 'HTML/dashboard_profesor.html', {
        'nr_materiale': Material.objects.filter(autor=user).count(),
        'nr_teste': teste.count(),
        'teste': teste 
    })

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

def incarcare_material(request):
    user_id = request.session.get('user_id')
    if not user_id: return redirect('login')
    
    try:
        user = Utilizator.objects.get(id=user_id)
    except Utilizator.DoesNotExist:
        return redirect('login')

    if request.method == "POST":
        titlu = request.POST.get('titlu')
        fisier = request.FILES.get('fisier_pdf') # Verifică să fie același 'name' ca în HTML

        if not titlu or not fisier:
            return render(request, 'HTML/incarcare_material.html', {'eroare': 'Te rog completează titlul și alege un fișier!'})

        print(f"--- Începe procesarea pentru: {titlu} ---")
        
        # 1. Salvează Materialul
        material = Material.objects.create(titlu=titlu, fisier_pdf=fisier, autor=user)
        print("Material salvat în baza de date.")

        try:
            # 2. Citește PDF-ul
            with open(material.fisier_pdf.path, 'rb') as pdf_file:
                cititor = PyPDF2.PdfReader(pdf_file)
                text_complet = ""
                # Citim primele 3 pagini
                for i in range(min(3, len(cititor.pages))):
                    text_complet += cititor.pages[i].extract_text() or ""
                
                if not text_complet.strip():
                    print("Eroare: Nu s-a putut extrage text din PDF.")
                    return render(request, 'HTML/incarcare_material.html', {'eroare': 'PDF-ul pare gol sau necitibil.'})

                print(f"Text extras cu succes ({len(text_complet)} caractere).")

                # 3. Generează testul
                noul_test = Test.objects.create(titlu=f"Test: {material.titlu}", material_sursa=material)
                
                print("Se apelează OpenAI...")
                lista_intrebari = genereaza_intrebari_ai(text_complet)
                
                if not lista_intrebari:
                    print("Eroare: OpenAI nu a returnat nicio întrebare.")
                    return render(request, 'HTML/incarcare_material.html', {'eroare': 'AI-ul nu a putut genera întrebări. Verifică cheia API!'})

                # 4. Salvează întrebările
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
            return render(request, 'HTML/incarcare_material.html', {'eroare': f'Eroare: {str(e)}'})

        return render(request, 'HTML/incarcare_material.html', {'mesaj': 'Succes! Testul AI a fost generat.'})

    return render(request, 'HTML/incarcare_material.html')

def detalii_test_view(request, test_id):
    test = Test.objects.get(id=test_id)
    intrebari = Intrebare.objects.filter(test=test)
    
    return render(request, 'HTML/detalii_test.html', {
        'test': test,
        'intrebari': intrebari
    })