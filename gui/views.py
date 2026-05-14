from django.shortcuts import render, redirect

def get_menu(request):
    return render(request, 'gui/menu.html')

def get_extraccion(request):
    return redirect('extraccion:get_name', pk=1)