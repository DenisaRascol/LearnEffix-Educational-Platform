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