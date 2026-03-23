from django.db import models

class Utilizator(models.Model):
    nume = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    parola = models.CharField(max_length=100)
    
    ROLURI = [
        ('elev', 'Elev'),
        ('profesor', 'Profesor'),
    ]
    rol = models.CharField(max_length=10, choices=ROLURI, default='elev')

    def __str__(self):
        return f"{self.nume} - {self.rol}"

class Material(models.Model):
    titlu = models.CharField(max_length=200)
    fisier_pdf = models.FileField(upload_to='materiale_pdf/')
    data_incarcarii = models.DateTimeField(auto_now_add=True)
    autor = models.ForeignKey(
        Utilizator, 
        on_delete=models.CASCADE, 
        limit_choices_to={'rol': 'profesor'}
    )
    def __str__(self):
        return self.titlu

class Test(models.Model):
    titlu = models.CharField(max_length=200)
    material_sursa = models.ForeignKey(Material, on_delete=models.CASCADE)
    creat_la = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Test: {self.titlu} (Sursa: {self.material_sursa.titlu})"
class Intrebare(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='intrebari')
    text_intrebare = models.TextField()
    varianta_a = models.CharField(max_length=200)
    varianta_b = models.CharField(max_length=200)
    varianta_c = models.CharField(max_length=200)
    varianta_d = models.CharField(max_length=200)
    raspuns_corect = models.CharField(max_length=1) # Vom stoca 'A', 'B', 'C' sau 'D'

    def __str__(self):
        return self.text_intrebare