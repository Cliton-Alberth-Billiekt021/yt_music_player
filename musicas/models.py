from django.db import models

class Musica(models.Model):
    titulo = models.CharField(max_length=200)
    artista = models.CharField(max_length=200, default="Desconhecido")
    arquivo_audio = models.FileField(upload_to='musicas/')
    capa = models.ImageField(upload_to='capas/', blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.artista}"