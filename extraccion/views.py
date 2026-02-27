from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from .form import FormDeArchivos
from django.shortcuts import get_object_or_404
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import python_code.extraccion_parametros as ep
import shutil

# Create your views here.
def inicial(request):
    return render(request, 'extraccion_principal.html')

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

            # Aquí lo gestiona FILES
            voz_indubitada = request.FILES["voz_indubitada"]
            path_voz_indubitada = default_storage.save('temporal_file_storage/voz_indubitada.wav', ContentFile(voz_indubitada.read()))
            
            textgrid_indubitado = request.FILES["textgrid_indubitada"]
            path_textgrid_indubitado = default_storage.save('temporal_file_storage/voz_indubitada.TextGrid', ContentFile(textgrid_indubitado.read()))

            voz_dubitada = request.FILES["voz_dubitada"]
            path_voz_dubitada = default_storage.save('temporal_file_storage/voz_dubitada.wav', ContentFile(voz_dubitada.read()))

            textgrid_dubitado = request.FILES["textgrid_dubitada"]
            path_textgrid_dubitado = default_storage.save('temporal_file_storage/voz_dubitada.TextGrid', ContentFile(textgrid_dubitado.read()))

            # Aquí lo gestiona POST o cleanded data
            genero_i = form.cleaned_data.get('genero')
            fonema = form.cleaned_data.get('fonema')
            parametros = form.cleaned_data.get('parametros')
            medida = request.POST.get('medida')
            intensidad = request.POST.get('intensidad')
            espectro = form.cleaned_data.get('espectro')

            center = 'center' in espectro
            sd = 'sd' in espectro
            sk = 'sk' in espectro
            kur = 'kur' in espectro

            # Hace las extracciones sobre los archivos guardados
            ep.process_sample_separado(os.path.join(os.getcwd(), 'temporal_file_storage'),vocales=fonema, genero = genero_i, pitch_mode= medida, intensity_mode = intensidad, center_b= center, sd_b= sd, sk_b= sk, kur_b= kur)

            # Hacer un comprimido para la descarga del CSV 
            shutil.make_archive("extraccion",'zip',os.path.join(os.getcwd(), 'temporal_file_storage'))

            filename = 'extraccion.zip'
            file_path = os.path.join(os.getcwd(), filename)

            with open(file_path, 'rb') as f:
                data = f.read()

            response = HttpResponse(data, content_type='zip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            ep.reset_archivos(os.path.join(os.getcwd(), 'temporal_file_storage'))

            return response

    # Esto sucede si la petición HTTP es GET; muestra solamente el formulario (sin rellenar).
    else:
        form = FormDeArchivos()

    return render(request, "name.html", {"form": form})