from django.db import models
import uuid

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

class Clasa(models.Model):
    nume_materie = models.CharField(max_length=100) 
    specializare = models.CharField(max_length=100) 
    an_studiu = models.CharField(max_length=10, default="1")
    cod_inrolare = models.CharField(max_length=8, unique=True, blank=True)
    profesor = models.ForeignKey(
        Utilizator, 
        on_delete=models.CASCADE, 
        related_name='clasele_mele',
        limit_choices_to={'rol': 'profesor'}
    )
    studenti = models.ManyToManyField(
        Utilizator, 
        related_name='clase_inrolate', 
        blank=True
    )

    def save(self, *args, **kwargs):
        if not self.cod_inrolare:
            self.cod_inrolare = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nume_materie} - {self.specializare} (An {self.an_studiu})"

class Material(models.Model):
    titlu = models.CharField(max_length=200)
    fisier_pdf = models.FileField(upload_to='materiale_pdf/')
    data_incarcarii = models.DateTimeField(auto_now_add=True)
    autor = models.ForeignKey(
        Utilizator, 
        on_delete=models.CASCADE, 
        limit_choices_to={'rol': 'profesor'}
    )
    clasa = models.ForeignKey(Clasa, on_delete=models.CASCADE, related_name='materiale', null=True)

    def __str__(self):
        return self.titlu

class Test(models.Model):
    titlu = models.CharField(max_length=200)
    autor = models.ForeignKey(Utilizator, on_delete=models.CASCADE, null=True, blank=True)
    clasa = models.ForeignKey(Clasa, on_delete=models.CASCADE, related_name='teste', null=True)
    material_sursa = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    creat_la = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sursa = self.material_sursa.titlu if self.material_sursa else "Material șters"
        return f"Test: {self.titlu} (Sursa: {sursa})"

class Intrebare(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='intrebari')
    text_intrebare = models.TextField()
    varianta_a = models.CharField(max_length=200)
    varianta_b = models.CharField(max_length=200)
    varianta_c = models.CharField(max_length=200)
    varianta_d = models.CharField(max_length=200)
    raspuns_corect = models.CharField(max_length=1) 

    def __str__(self):

        return f"Întrebare pentru {self.test.titlu}: {self.text_intrebare[:20]}..."

class RezultatTest(models.Model):
    student = models.ForeignKey(Utilizator, on_delete=models.CASCADE, related_name='rezultate')
    test = models.ForeignKey('Test', on_delete=models.CASCADE)
    punctaj = models.FloatField()
    data_finalizarii = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.nume} - {self.test.titlu}: {self.punctaj}"

class Nota(models.Model):
    TIP_NOTE = [
        ('TEST', 'Test Online'),
        ('ACTIVITATE', 'Activitate la clasă'),
    ]
    
    student = models.ForeignKey(Utilizator, on_delete=models.CASCADE, limit_choices_to={'rol': 'elev'})
    clasa = models.ForeignKey(Clasa, on_delete=models.CASCADE)
    test = models.ForeignKey('Test', on_delete=models.CASCADE, null=True, blank=True) 
    valoare = models.IntegerField() 
    tip = models.CharField(max_length=20, choices=TIP_NOTE, default='TEST')
    data_acordarii = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.nume} - {self.clasa.nume_materie}: {self.valoare}"