from django.shortcuts import render, redirect,get_object_or_404
from .forms import CustomerForm
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from customer.models import Customer
import os
import pandas as pd
from customer.sendEmail import send_email
from Invoice.models import Invoice  


@login_required
def Customer_create_view(request):  
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)
        print(form)
        if form.is_valid():
            customer = form.save()
            destinatario = customer.email 
            asunto = '¡Bienvenido a Berserker!'
            contenido_texto = f'Hola {customer}, ¡gracias por registrarte!'
            
            contenido_html = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Bienvenido a Berserker</title>
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa;">
                <div style="width: 100%; background-color: #f8f9fa; padding: 40px 0;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden;">
                        
                        <!-- Header con logo -->
                        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 40px 20px; text-align: center;">
                            <div style="background-color: rgba(255,255,255,0.15); display: inline-block; padding: 15px 25px; border-radius: 8px; margin-bottom: 20px;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: 700; letter-spacing: 1px;">⚡ BERSERKER</h1>
                            </div>
                            <h2 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 300;">Libera tu potencial</h2>
                        </div>
                        
                        <!-- Contenido principal -->
                        <div style="padding: 40px 30px;">
                            <div style="text-align: center; margin-bottom: 30px;">
                                <!-- Icono de usuario -->
                                <div style="width: 80px; height: 80px; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center;">
                                    <span style="color: white; font-size: 36px;">👤</span>
                                </div>
                            </div>
                            
                            <h3 style="color: #2c3e50; font-size: 24px; text-align: center; margin-bottom: 20px; font-weight: 600;">¡Hola {customer.nombre if hasattr(customer, 'nombre') else customer}!</h3>
                            
                            <p style="color: #5a6c7d; font-size: 16px; line-height: 1.6; text-align: center; margin-bottom: 25px;">
                                ¡Bienvenido a <strong>Berserker</strong>! Has sido registrado exitosamente en nuestra plataforma. 
                                Si quieres disfrutar de nuestros servicios premium y desbloquear todo tu potencial, 
                                te invitamos a explorar todas las funcionalidades que tenemos preparadas para ti.
                            </p>
                            
                            <!-- Botón principal -->
                            <div style="text-align: center; margin: 35px 0;">
                                <a href="https://berserker.com" 
                                   style="display: inline-block; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
                                          color: #ffffff; text-decoration: none; padding: 15px 35px; 
                                          border-radius: 8px; font-weight: 600; font-size: 16px; 
                                          box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
                                          transition: transform 0.2s;">
                                    Comenzar ahora
                                </a>
                            </div>
                            
                            
                            <p style="color: #5a6c7d; font-size: 14px; text-align: center; margin: 30px 0 10px;">
                                Si tienes alguna pregunta, no dudes en 
                                <a href="mailto:soporte@berserker.com" style="color: #28a745; text-decoration: none;">contactarnos</a>. 
                                Siempre estamos felices de ayudar.
                            </p>
                        </div>
                        
                        <!-- Footer -->
                        <div style="background-color: #2c3e50; padding: 30px 20px; text-align: center;">
                            <p style="color: #ecf0f1; margin: 0 0 15px; font-size: 16px; font-weight: 500;">
                                ¡Saludos!<br>
                                <span style="color: #20c997;">El equipo de Berserker</span>
                            </p>
                            
                            <!-- Enlaces del footer -->
                            <div style="margin: 20px 0;">
                                <a href="https://berserker.com/privacidad" style="color: #95a5a6; text-decoration: none; margin: 0 15px; font-size: 12px;">Política de Privacidad</a>
                                <span style="color: #95a5a6;">•</span>
                                <a href="https://berserker.com/contacto" style="color: #95a5a6; text-decoration: none; margin: 0 15px; font-size: 12px;">Contáctanos</a>
                                <span style="color: #95a5a6;">•</span>
                                <a href="https://berserker.com/blog" style="color: #95a5a6; text-decoration: none; margin: 0 15px; font-size: 12px;">Blog</a>
                            </div>
                            
                            <!-- Redes sociales -->
                            <div style="margin: 20px 0;">
                                <a href="#" style="display: inline-block; margin: 0 10px; width: 36px; height: 36px; background-color: #3b5998; border-radius: 50%; text-align: center; line-height: 36px; color: white; text-decoration: none;">f</a>
                                <a href="#" style="display: inline-block; margin: 0 10px; width: 36px; height: 36px; background-color: #0077b5; border-radius: 50%; text-align: center; line-height: 36px; color: white; text-decoration: none;">in</a>
                                <a href="#" style="display: inline-block; margin: 0 10px; width: 36px; height: 36px; background-color: #1da1f2; border-radius: 50%; text-align: center; line-height: 36px; color: white; text-decoration: none;">@</a>
                            </div>
                            
                            <p style="color: #95a5a6; font-size: 12px; margin: 20px 0 0; line-height: 1.4;">
                                Copyright © 2025 Berserker. Todos los derechos reservados.<br>
                                Soledad,Atlantico, Colombia.<br>
                            </p>
                            
                            <!-- Logo pequeño del footer -->
                            <div style="margin-top: 20px;">
                                <span style="color: #20c997; font-size: 18px; font-weight: 700;">⚡ BERSERKER</span>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            try:
                send_email(destinatario, asunto, contenido_texto, contenido_html)
            except Exception as e: 
                print(f"error al enviar correo: {e}")
            return JsonResponse({'redirect': reverse('viewClient')})
        else:
            cedula_error = form.errors.get('cedula')
            if cedula_error:
                return JsonResponse({'error': cedula_error}, status=400)
    else:
        form = CustomerForm()
    return render(request, 'Customer/createCustomer.html', {'form': form})

@login_required
def view_Clients(request):
    clients = Customer.objects.all()
    context = {
        'clients': clients,
    }
    print(context)
    return render(request, 'Customer/viewClient.html', context)

@login_required
def download_pdf(request, client_id):
    client = get_object_or_404(Customer, id=client_id)
    print(client)
    pdf_path = client.pdf.path
    with open(pdf_path, 'rb') as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={os.path.basename(pdf_path)}'
        return response


@login_required
def update_Customer(request, client_id):
    client = get_object_or_404(Customer, id=client_id)
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            return JsonResponse({'redirect': reverse('viewClient')})
        else:
            cedula_error = form.errors.get('cedula')
            if cedula_error:
                return JsonResponse({'error': cedula_error}, status=400)
    else:
        form = CustomerForm(instance=client)
    return render(request, 'Customer/updateCustomer.html', {'form': form, 'client_id': client.id})


@login_required
def delete_Customer(request, client_id):
    client = get_object_or_404(Customer, id=client_id)

    
    
    if Invoice.objects.filter(customer=client).exists():
        return JsonResponse({
            'status': 'error',
            'message': 'Este cliente tiene movimientos y no se puede eliminar.'
        })

    client.delete()
    return JsonResponse({
        'status': 'success',
        'message': 'Cliente eliminado correctamente.'
    })



@login_required
def export_clients_to_excel(request):
    clients = Customer.objects.all()
    data = {
        'ID': [client.id for client in clients],
        'Cedula': [client.cedula for client in clients],
        'Nombre': [client.name for client in clients],
        'Apellido': [client.lastname for client in clients],
        'Telefono': [client.phone for client in clients],
        'Email': [client.email for client in clients],
        'Direccion': [client.address for client in clients],
        'Ciudad': [client.city for client in clients],
        'Barrio': [client.neighborhood for client in clients],
        'Ingresos': [client.income for client in clients],
        'Ocupacion': [client.source_of_income for client in clients],
        'Situacion laboral': [client.employment_situation for client in clients],
        'producto solicitado': [client.producto_solicitados for client in clients],
        'Fecha de registro': [client.record_date for client in clients],
    }
    
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Customers.xlsx'
    df.to_excel(response, index=False)
    
    return response

@login_required
def cargar_datos_excel(request):
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        cedulas_repetidas = []

        try:
            df = pd.read_excel(archivo, dtype={'Cedula': str})

            df = df.dropna(subset=['Cedula'])

            cedulas_existentes = set(Customer.objects.values_list('cedula', flat=True))

            customers_nuevos = []
            for _, row in df.iterrows():
                cedula = str(row.get('Cedula', '')).strip()
                if cedula in cedulas_existentes:
                    cedulas_repetidas.append(cedula)
                    continue

                try:
                    customers_nuevos.append(
                        Customer(
                            name=safe_strip(row.get('Nombre', '')),
                            lastname=safe_strip(row.get('Apellido', '')),
                            cedula=cedula,
                            phone=safe_strip(row.get('Telefono', '')),
                            neighborhood=safe_strip(row.get('Barrio', '')),
                            address=safe_strip(row.get('Direccion', '')),
                            email=safe_strip(row.get('Email', '')),
                            income=float(row.get('Ingreso mensual', 0) or 0),
                            source_of_income=safe_strip(row.get('Fuente de ingreso', '')),
                            employment_situation=safe_strip(row.get('Situacion laboral', '')),
                            producto_solicitados=safe_strip(row.get('Producto solicitado', ''))
                        )
                    )
                except Exception as e:
                    print(f"Error procesando fila {row.to_dict()}: {e}")
                    continue

            if customers_nuevos:
                Customer.objects.bulk_create(customers_nuevos)

            if cedulas_repetidas:
                mensaje = f"Los siguientes registros no fueron importados porque ya existen: {', '.join(cedulas_repetidas)}"
                return JsonResponse({'status': 'warning', 'message': mensaje, 'duplicados': cedulas_repetidas})
            else:
                return JsonResponse({'status': 'success', 'message': 'Datos cargados correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'No se recibió ningún archivo.'})

def safe_strip(value):
    return str(value).strip() if value is not None else ''

