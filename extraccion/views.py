import os
import uuid
import shutil
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from extraccion.forms import Frame1Form, Frame2Form, Frame3Form
from extraccion import services as sc


def _session_dir(request):
    """Devuelve (y crea si no existe) el directorio temporal de la sesión."""
    if not request.session.session_key:
        request.session.create()
    dir_id = request.session.get('dir_id')
    if not dir_id:
        dir_id = str(uuid.uuid4())
        request.session['dir_id'] = dir_id
    path = os.path.join(settings.BASE_DIR, 'temporal_file_storage', dir_id)
    os.makedirs(path, exist_ok=True)
    return path


_ARCHIVOS_MAP = {
    'voz_indubitada':      'voz_indubitada.wav',
    'textgrid_indubitada': 'voz_indubitada.TextGrid',
    'voz_dubitada':        'voz_dubitada.wav',
    'textgrid_dubitada':   'voz_dubitada.TextGrid',
}


def _archivos_completos(session_dir):
    if not session_dir:
        return False
    return all(os.path.exists(os.path.join(session_dir, n)) for n in _ARCHIVOS_MAP.values())


def frame1(request):
    session_dir = _session_dir(request) if request.session.get('dir_id') else None
    ya_cargados = _archivos_completos(session_dir)

    if request.method == 'POST':
        form = Frame1Form(request.POST, request.FILES, archivos_existentes=ya_cargados)
        if form.is_valid():
            session_dir = _session_dir(request)
            nombres_guardados = request.session.get('archivos_nombres', {})
            for campo, nombre in _ARCHIVOS_MAP.items():
                if campo in request.FILES:
                    archivo = request.FILES[campo]
                    with open(os.path.join(session_dir, nombre), 'wb') as f:
                        for chunk in archivo.chunks():
                            f.write(chunk)
                    nombres_guardados[campo] = archivo.name
            request.session['archivos_nombres'] = nombres_guardados
            return redirect('frame2')
    else:
        form = Frame1Form(archivos_existentes=ya_cargados)

    nombres = request.session.get('archivos_nombres', {})
    return render(request, 'frame1.html', {'form': form, 'paso': 1, 'ya_cargados': ya_cargados, 'nombres': nombres})


def frame2(request):
    if not request.session.get('dir_id'):
        return redirect('frame1')

    if request.method == 'POST':
        form = Frame2Form(request.POST)
        if form.is_valid():
            request.session['genero'] = form.cleaned_data['genero']
            request.session['fonemas'] = form.cleaned_data['fonema']
            return redirect('frame3')
    else:
        initial = {}
        if request.session.get('genero'):
            initial['genero'] = request.session['genero']
        if request.session.get('fonemas'):
            initial['fonema'] = request.session['fonemas']
        form = Frame2Form(initial=initial)

    return render(request, 'frame2.html', {'form': form, 'paso': 2})


def frame3(request):
    if not request.session.get('dir_id') or not request.session.get('fonemas'):
        return redirect('frame1')

    fonemas = request.session['fonemas']
    tiene_vocales = any(f in fonemas for f in ['a', 'e', 'i', 'o', 'u'])
    tiene_s = 's' in fonemas

    if request.method == 'POST':
        form = Frame3Form(request.POST, tiene_vocales=tiene_vocales, tiene_s=tiene_s)
        if form.is_valid():
            request.session['frame3_params'] = {
                'parametros': form.cleaned_data.get('parametros', []),
                'medida':     form.cleaned_data.get('medida', ''),
                'espectro':   form.cleaned_data.get('espectro', []),
                'intensidad': form.cleaned_data.get('intensidad', []),
            }

            session_dir = _session_dir(request)
            genero = request.session['genero']
            espectro = form.cleaned_data.get('espectro', [])

            # Formantes seleccionados: F0 es el pitch; F1-F4 son formantes
            parametros = form.cleaned_data.get('parametros', [])
            incluir_pitch = '0' in parametros
            formant_mode = [int(p) for p in parametros if p != '0']

            sc.process_sample_separado(
                session_dir,
                vocales=fonemas,
                genero=genero,
                pitch_mode=form.cleaned_data.get('medida', 'mean'),
                formant_mode=formant_mode,
                incluir_pitch=incluir_pitch,
                intensity_modes=form.cleaned_data.get('intensidad', []),
                center_b='center' in espectro,
                sd_b='sd' in espectro,
                sk_b='sk' in espectro,
                kur_b='kur' in espectro,
                alt_b='alt' in espectro,
                gen_vocal=tiene_vocales,
                gen_s=tiene_s,
            )

            zip_base = os.path.join(settings.BASE_DIR, 'temporal_file_storage', request.session['dir_id'] + '_result')
            shutil.make_archive(zip_base, 'zip', session_dir)

            with open(zip_base + '.zip', 'rb') as f:
                data = f.read()

            os.remove(zip_base + '.zip')
            shutil.rmtree(session_dir, ignore_errors=True)
            for key in ['dir_id', 'fonemas', 'genero', 'frame3_params']:
                request.session.pop(key, None)

            response = HttpResponse(data, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="extraccion.zip"'
            return response
    else:
        initial = request.session.get('frame3_params', {})
        form = Frame3Form(tiene_vocales=tiene_vocales, tiene_s=tiene_s, initial=initial)

    return render(request, 'frame3.html', {
        'form': form,
        'paso': 3,
        'tiene_vocales': tiene_vocales,
        'tiene_s': tiene_s,
    })


def inicio(request):
    return render(request, 'inicio.html')


def acerca(request):
    return render(request, 'acerca.html')


def participantes(request):
    return render(request, 'participantes.html')


def publicaciones(request):
    return render(request, 'publicaciones.html')
