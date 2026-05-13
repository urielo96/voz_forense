# En este archivo definimos los formularios que vamos a usar en la aplicación. En este caso, tenemos un formulario para subir archivos y seleccionar opciones para la extracción de características de voz.

from django import forms
from django.core.validators import FileExtensionValidator



class FormDeArchivos(forms.Form):

    # Extracción general

    voz_indubitada = forms.FileField(label="Voz indubitada",validators=[FileExtensionValidator(allowed_extensions=["wav"])]) 
    textgrid_indubitada = forms.FileField(label="Textgrid indubitada",validators=[FileExtensionValidator(allowed_extensions=["textgrid"])])

    voz_dubitada = forms.FileField(label="Voz dubitada",validators=[FileExtensionValidator(allowed_extensions=["wav"])])
    textgrid_dubitada = forms.FileField(label="Textgrid dubitado",validators=[FileExtensionValidator(allowed_extensions=["textgrid"])])

    
    GENERO = (('M', 'M: Masculino'),('F', 'F: Femenino'),('X', 'X: Sin especificar'))
    genero = forms.ChoiceField(label="Género",choices=GENERO)

    # Extracción vocálica

    FONEMA = (('a', 'a'),('e', 'e'),('i', 'i'),('o', 'o'),('u', 'u'))
    fonema = forms.MultipleChoiceField(choices=FONEMA, widget=forms.CheckboxSelectMultiple)

    PARAMS = ((0, 'F0'),(1, 'F1'),(2, 'F2'),(3, 'F3'),(4, 'F4'))
    parametros = forms.MultipleChoiceField(choices=PARAMS, widget=forms.CheckboxSelectMultiple())

    MEDIDA = (('mean', 'Promedio'),('median', 'Punto medio'),('maximum', 'Máximo'),('minimun', 'Mínimo'))
    medida = forms.ChoiceField(choices=MEDIDA,widget=forms.RadioSelect())

    # Extracción sonido s

    INTENSIDAD = (('mean', 'Promedio'),('maximum', 'Máximo'))
    intensidad = forms.ChoiceField(choices=INTENSIDAD,widget=forms.RadioSelect())
    
    ESPECTRO = (('center', 'Centro de gravedad'),('sd', 'Desviación estándar'),('sk', 'Asimetría'),('kur','Curtosis'))
    espectro = forms.MultipleChoiceField(choices=ESPECTRO, widget=forms.CheckboxSelectMultiple())

