from django import forms
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError


def validate_textgrid(value):
    if not value.name.lower().endswith('.textgrid'):
        raise ValidationError('El archivo debe tener extensión .TextGrid')


# ── FRAME 1: Subida de archivos ──────────────────────────────────
class Frame1Form(forms.Form):
    voz_indubitada = forms.FileField(
        label="Voz indubitada (.wav)",
        validators=[FileExtensionValidator(allowed_extensions=['wav'])]
    )
    textgrid_indubitada = forms.FileField(
        label="TextGrid indubitada (.TextGrid)",
        validators=[validate_textgrid]
    )
    voz_dubitada = forms.FileField(
        label="Voz dubitada (.wav)",
        validators=[FileExtensionValidator(allowed_extensions=['wav'])]
    )
    textgrid_dubitada = forms.FileField(
        label="TextGrid dubitada (.TextGrid)",
        validators=[validate_textgrid]
    )

    def __init__(self, *args, archivos_existentes=False, **kwargs):
        super().__init__(*args, **kwargs)
        if archivos_existentes:
            for field in self.fields.values():
                field.required = False


# ── FRAME 2: Género y fonemas ────────────────────────────────────
class Frame2Form(forms.Form):
    GENERO = (
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('X', 'Sin especificar'),
    )
    genero = forms.ChoiceField(label="Género *", choices=GENERO)

    FONEMA = (
        ('a', 'a'),
        ('e', 'e'),
        ('i', 'i'),
        ('o', 'o'),
        ('u', 'u'),
        ('s', 's  (espectro)'),
    )
    fonema = forms.MultipleChoiceField(
        label="Fonema *",
        choices=FONEMA,
        widget=forms.CheckboxSelectMultiple,
    )


# ── FRAME 3: Parámetros acústicos (dinámico) ─────────────────────
class Frame3Form(forms.Form):
    def __init__(self, *args, tiene_vocales=True, tiene_s=True, **kwargs):
        super().__init__(*args, **kwargs)

        if tiene_vocales:
            PARAMS = ((0, 'F0'), (1, 'F1'), (2, 'F2'), (3, 'F3'), (4, 'F4'))
            self.fields['parametros'] = forms.MultipleChoiceField(
                label="Parámetros vocálicos",
                choices=PARAMS,
                widget=forms.CheckboxSelectMultiple,
                required=True,
                error_messages={'required': 'Selecciona al menos un parámetro vocálico (F0–F4).'},
            )
            MEDIDA = (
                ('mean',    'Promedio'),
                ('median',  'Punto medio'),
                ('maximum', 'Máximo'),
                ('minimun', 'Mínimo'),
            )
            self.fields['medida'] = forms.ChoiceField(
                label="Métrica de extracción",
                choices=MEDIDA,
                widget=forms.RadioSelect(),
            )

        if tiene_s:
            ESPECTRO = (
                ('center', 'Centro de gravedad'),
                ('sd',     'Desviación estándar'),
                ('sk',     'Asimetría'),
                ('kur',    'Curtosis'),
                ('alt',    'Altura de la fricción'),
            )
            self.fields['espectro'] = forms.MultipleChoiceField(
                label="Parámetros del fonema /s/",
                choices=ESPECTRO,
                widget=forms.CheckboxSelectMultiple(),
                required=False,
            )
            INTENSIDAD = (
                ('mean',    'Promedio'),
                ('maximum', 'Máximo'),
                ('minimum', 'Mínimo'),
            )
            self.fields['intensidad'] = forms.MultipleChoiceField(
                label="Intensidad",
                choices=INTENSIDAD,
                widget=forms.CheckboxSelectMultiple(),
            )

