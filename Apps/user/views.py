from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from .form import CustomUserCreationForm, CustomAuthenticationForm
from django.db.models import Count
from item.models import Item
import json
from django.contrib import messages
from customer.models import Customer
from Invoice.models import Invoice, InvoiceItem
from django.db.models import Sum
from .form import UserUpdateForm, CustomPasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from datetime import datetime, timedelta

MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
DIAS_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def _fecha_larga_es(d):
    return f'{DIAS_ES[d.weekday()]} {d.day} de {MESES_ES[d.month - 1]}'
from django.db.models.functions import TruncMonth
from django.db.models import F, Sum, Count
from django.db.models.functions import TruncMonth
import calendar

# Login and register

def home(request):
    return render(request, 'home.html')

def signup(request):
    if request.method == 'GET':
        return render(request, 'signup.html', {"form": CustomUserCreationForm()})
    else:

        if User.objects.filter(username=request.POST["username"]).exists():
            return render(request, 'signup.html', {"form": CustomUserCreationForm, "error": "El nombre de usuario ya existe."})
        if request.POST["password1"] == request.POST["password2"]:
            try:
                user = User.objects.create_user(
                    username=request.POST["username"],
                    password=request.POST["password1"],
                    email=request.POST["email"],
                    first_name=request.POST["name"],
                    last_name=request.POST["lastname"]
                )
                user.save()
                login(request, user)
                return redirect('Dasboard')
            except IntegrityError:
                return render(request, 'signup.html', {"form": CustomUserCreationForm(), "error": "El nombre de usuario ya existe."})
        return render(request, 'signup.html', {"form": CustomUserCreationForm(), "error": "Las contraseñas no coinciden."})



@login_required
def Dashboard(request):
    customer_count = Customer.objects.count()
    items_count = Item.objects.filter(active=True).count()
    low_stock_qs = Item.objects.filter(active=True, Stock__lte=2).order_by('Stock', 'Name')
    low_stock_count = low_stock_qs.count()
    low_stock_items = list(low_stock_qs[:8])

    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))

    # Clientes nuevos por día
    new_clients_per_day = (
        Customer.objects
        .filter(record_date__isnull=False, record_date__gte=datetime.now().date() - timedelta(days=60))
        .values('record_date')
        .annotate(count=Count('id'))
        .order_by('record_date')
    )


    monthly_sales = (
        Invoice.objects
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('total'))
        .order_by('month')
    )
    labels = [f"{MESES_CORTOS[sale['month'].month - 1]} {sale['month'].year}" for sale in monthly_sales if sale['month']]
    totals = [float(sale['total'] or 0) for sale in monthly_sales if sale['month']]

    # Productos más vendidos
    best_selling_products = (
        InvoiceItem.objects
        .values('item__Name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:10]
    )

    # Totales por estado
    Total = Invoice.objects.filter(status='Pagada').aggregate(
        result=Sum(F('total') - F('delivery_amount'))
    )
    Total_Payment = float(Total.get('result') or 0)

    Total_credit = Invoice.objects.filter(status='Credito').aggregate(
        result=Sum(F('total') - F('delivery_amount'))
    )
    Total_Payment_credit = float(Total_credit.get('result') or 0)

    # Datos para gráficos
    dates_clients = [entry['record_date'].strftime('%d/%m') for entry in new_clients_per_day if entry['record_date']]
    counts_clients = [entry['count'] for entry in new_clients_per_day]


    months_sales = json.dumps(labels)
    totals_sales = json.dumps(totals)

    products_names = [entry['item__Name'] for entry in best_selling_products]
    products_sales = [entry['total_quantity'] for entry in best_selling_products]

    context = {
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_count,
        'today_label': _fecha_larga_es(datetime.now()),
        'num_Customers': customer_count,
        'num_items': items_count,
        'num_total': Total_Payment,
        'dates_clients': json.dumps(dates_clients),
        'counts_clients': json.dumps(counts_clients),
        'dates_sales': months_sales,  
        'totals_sales': totals_sales,
        'products_names': json.dumps(products_names),
        'products_sales': json.dumps(products_sales),
        'num_total_credit': Total_Payment_credit,
    }

    return render(request, 'tasks.html', context)

@login_required 
def signout(request): 
    logout(request)
    return redirect('home')


def signin(request):
    storage = messages.get_messages(request)
    storage.used = True

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('Dasboard')
            else:
                messages.error(request, "Incorrect username or password.")
        else:
            messages.error(request, "Incorrect username or password.")

    else:
        form = CustomAuthenticationForm()

    return render(request, 'signin.html', {'form': form})


# Profile 
@login_required
def profile_view(request):
    user = request.user
    return render(request, 'Profile.html', {'user': user})


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)

        # La contraseña es opcional: solo se valida si se llenó algún campo
        wants_password = any(request.POST.get(f) for f in ('old_password', 'new_password1', 'new_password2'))
        password_ok = password_form.is_valid() if wants_password else True

        if user_form.is_valid() and password_ok:
            user_form.save()
            if wants_password:
                password_form.save()
                update_session_auth_hash(request, password_form.user)
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('edit_profile')
        for form in ([user_form, password_form] if wants_password else [user_form]):
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
    else:
        user_form = UserUpdateForm(instance=request.user)
        password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'edit_profile.html', {
        'user_form': user_form,
        'password_form': password_form
    })


