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

    # Clientes nuevos
    new_clients_per_day = (
        Customer.objects
        .filter(record_date__isnull=False)
        .values('record_date')
        .annotate(count=Count('id'))
        .order_by('record_date')
    )

    # Ventas diarias
    sales_per_day = (
        Invoice.objects
        .filter(date__isnull=False)
        .values('date')
        .annotate(total_sales=Sum('total'))
        .order_by('date')
    )

    # Productos más vendidos
    best_selling_products = (
        InvoiceItem.objects
        .values('item__Name') 
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:10] 
    )

    Total= Invoice.objects.filter(status ='Pagada').aggregate(result =Sum('total'))
    Total_Payment = float(Total.get('result') or 0)

    Total_credit = Invoice.objects.filter(status ='credit').aggregate(result =Sum('total'))
    Total_Payment_credit = float(Total_credit.get('result') or 0)

    dates_clients = [entry['record_date'].strftime('%Y-%m-%d') for entry in new_clients_per_day if entry['record_date']]
    counts_clients = [entry['count'] for entry in new_clients_per_day]

    dates_sales = [entry['date'].strftime('%Y-%m-%d') for entry in sales_per_day if entry['date']]
    totals_sales = [float(entry['total_sales']) for entry in sales_per_day]

    products_names = [entry['item__Name'] for entry in best_selling_products]
    products_sales = [entry['total_quantity'] for entry in best_selling_products]

    context = {
        'num_Customers': customer_count,
        'num_items': items_count,
        'num_total': Total_Payment,
        'dates_clients': json.dumps(dates_clients),
        'counts_clients': json.dumps(counts_clients),
        'dates_sales': json.dumps(dates_sales),
        'totals_sales': json.dumps(totals_sales),
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

        if user_form.is_valid() and password_form.is_valid():
            user_form.save()
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, 'Usuario actualizado exitosamente')
            return redirect('edit_profile')
        else:
            if password_form.errors:
                for field, errors in password_form.errors.items():
                    for error in errors:
                        messages.error(request, 'Ultilize otra contraseña')
            if user_form.errors:
                for field, errors in user_form.errors.items():
                    for error in errors:
                        messages.error(request, 'Ultilize otro nombre de usuario')
    else:
        user_form = UserUpdateForm(instance=request.user)
        password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'edit_profile.html', {
        'user_form': user_form,
        'password_form': password_form
    })


