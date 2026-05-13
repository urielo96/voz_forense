from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from .forms import FormDeArchivos
from django.shortcuts import get_object_or_404
from django.conf import settings
import os
from extraccion import services as sc
import shutil

# Create your views here.
def hello(request,variable):
    print(variable)
    return HttpResponse("<h1> Hola, estudiantx %s </h1>" % variable)

def get_name(request):
    # Si el método es POST (enviamos un formulario) entonces ejecuta lo siguiente
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = FormDeArchivos(request.POST,request.FILES)
        # Hasta ahora no hace validaciones sobre el formulario
        if form.is_valid():

            # Crear el directorio temporal si no existe
            temporal_dir = os.path.join(settings.BASE_DIR, 'temporal_file_storage')
            os.makedirs(temporal_dir, exist_ok=True)

            # Aquí lo gestiona FILES - guardar archivos directamente
            voz_indubitada = request.FILES["voz_indubitada"]
            path_voz_indubitada = os.path.join(temporal_dir, 'voz_indubitada.wav')
            with open(path_voz_indubitada, 'wb') as f:
                for chunk in voz_indubitada.chunks():
                    f.write(chunk)
            
            textgrid_indubitado = request.FILES["textgrid_indubitada"]
            path_textgrid_indubitado = os.path.join(temporal_dir, 'voz_indubitada.TextGrid')
            with open(path_textgrid_indubitado, 'wb') as f:
                for chunk in textgrid_indubitado.chunks():
                    f.write(chunk)

            voz_dubitada = request.FILES["voz_dubitada"]
            path_voz_dubitada = os.path.join(temporal_dir, 'voz_dubitada.wav')
            with open(path_voz_dubitada, 'wb') as f:
                for chunk in voz_dubitada.chunks():
                    f.write(chunk)

            textgrid_dubitado = request.FILES["textgrid_dubitada"]
            path_textgrid_dubitado = os.path.join(temporal_dir, 'voz_dubitada.TextGrid')
            with open(path_textgrid_dubitado, 'wb') as f:
                for chunk in textgrid_dubitado.chunks():
                    f.write(chunk)

            # Obtener los demás datos del formulario
            genero_i = form.cleaned_data.get('genero')
            fonema = form.cleaned_data.get('fonema')
            parametros = form.cleaned_data.get('parametros')
            medida = form.cleaned_data.get('medida')
            intensidad = form.cleaned_data.get('intensidad')
            espectro = form.cleaned_data.get('espectro')
            # Esta preguntando si esta en lo que marco el usuario entonces que sea True, sino False
            center = 'center' in espectro
            sd = 'sd' in espectro
            sk = 'sk' in espectro
            kur = 'kur' in espectro

            # Hace las extracciones sobre los archivos guardados
            # Estamos Haciendo la llamada a la función que hace las extracciones, le pasamos el directorio temporal y los parámetros que el usuario seleccionó en el formulario
            sc.process_sample_separado(temporal_dir, vocales=fonema, genero=genero_i, pitch_mode=medida, intensity_mode=intensidad, center_b=center, sd_b=sd, sk_b=sk, kur_b=kur)

            # Hacer un comprimido para la descarga del CSV 
            zip_path = os.path.join(settings.BASE_DIR, 'extraccion')
            shutil.make_archive(zip_path, 'zip', temporal_dir)

            filename = 'extraccion.zip'
            file_path = os.path.join(settings.BASE_DIR, filename)

            with open(file_path, 'rb') as f:
                data = f.read()

            response = HttpResponse(data, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            sc.reset_archivos(temporal_dir)

            return response

    # Esto sucede si la petición HTTP es GET; muestra solamente el formulario (sin rellenar).
    else:
        form = FormDeArchivos()

    return render(request, "name.html", {"form": form})