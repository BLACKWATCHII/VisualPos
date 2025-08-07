from django.shortcuts import render


def ajustesInventario(request):
    if request.method == 'POST':
        pass
    return render(request, 'Inventory/AjusteInventario.html')
