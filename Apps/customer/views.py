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
            asunto = '¡Bienvenido a Celupro Co! 🎉'
            contenido_texto = f'Hola {customer}, ¡gracias por unirte a nuestra familia tecnológica!'
            
            contenido_html = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Bienvenido a Celupro Co</title>
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div style="width: 100%; padding: 40px 20px;">
                    <div style="max-width: 650px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); overflow: hidden;">
                        
                        <!-- Header con Logo -->
                        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #60a5fa 100%); padding: 40px 30px; text-align: center; position: relative;">
                            <img src="https://raw.githubusercontent.com/Kevin25DC/celupro-assets/refs/heads/main/logo%20de%20prueba%20dos.png" 
                                 alt="Celupro Co Logo" 
                                 style="max-width: 180px; height: auto; margin-bottom: 20px; background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                            <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                ¡Bienvenido a Celupro Co!
                            </h1>
                            <p style="margin: 10px 0 0; color: rgba(255,255,255,0.95); font-size: 16px; font-weight: 300;">
                                Tu destino tecnológico #1
                            </p>
                        </div>
                        
                        <!-- Contenido Principal -->
                        <div style="padding: 40px 30px;">
                            
                            <!-- Icono de Bienvenida -->
                            <div style="text-align: center; margin-bottom: 30px;">
                                <div style="width: 90px; height: 90px; background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); border-radius: 50%; margin: 0 auto; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 8px 20px rgba(251, 191, 36, 0.3);">
                                    <span style="font-size: 45px;">🎉</span>
                                </div>
                            </div>
                            
                            <!-- Saludo -->
                            <h2 style="color: #1e293b; font-size: 26px; text-align: center; margin-bottom: 20px; font-weight: 700;">
                                ¡Hola, {customer.name if hasattr(customer, 'name') else customer}!
                            </h2>
                            
                            <p style="color: #475569; font-size: 16px; line-height: 1.8; text-align: center; margin-bottom: 25px;">
                                Nos emociona darte la bienvenida a <strong style="color: #1e3a8a;">Celupro Co</strong>, 
                                tu tienda de confianza para todo lo relacionado con <strong>tecnología, celulares, relojes inteligentes</strong> 
                                y los últimos accesorios del mercado.
                            </p>
                            
                            <!-- Cards de Beneficios -->
                            <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 12px; padding: 25px; margin: 30px 0; border-left: 4px solid #3b82f6;">
                                <h3 style="color: #1e3a8a; font-size: 18px; margin: 0 0 15px; font-weight: 700;">
                                    🎁 ¿Qué puedes esperar?
                                </h3>
                                <ul style="margin: 0; padding-left: 20px; color: #475569; font-size: 14px; line-height: 1.8;">
                                    <li style="margin-bottom: 8px;">📱 <strong>Últimos modelos</strong> en smartphones y tablets</li>
                                    <li style="margin-bottom: 8px;">⌚ <strong>Relojes inteligentes</strong> de las mejores marcas</li>
                                    <li style="margin-bottom: 8px;">🎧 <strong>Accesorios premium</strong> y tecnología de punta</li>
                                    <li style="margin-bottom: 8px;">🚚 <strong>Envíos rápidos</strong> y seguros a todo el país</li>
                                    <li>💎 <strong>Precios competitivos</strong> y ofertas exclusivas</li>
                                </ul>
                            </div>
                            
                            <!-- Botón CTA -->
                            <div style="text-align: center; margin: 35px 0;">
                                <a href="https://celuproco.com.co/" 
                                   style="display: inline-block; 
                                          background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%); 
                                          color: #ffffff; 
                                          text-decoration: none; 
                                          padding: 18px 45px; 
                                          border-radius: 50px; 
                                          font-weight: 700; 
                                          font-size: 17px; 
                                          box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
                                          letter-spacing: 0.5px;">
                                    🛒 Explorar Productos
                                </a>
                            </div>
                            
                            <!-- Sección de Destacados -->
                            <div style="background: #f8fafc; border-radius: 12px; padding: 25px; margin: 30px 0;">
                                <div style="text-align: center; margin-bottom: 20px;">
                                    <h3 style="color: #1e293b; font-size: 20px; margin: 0 0 10px; font-weight: 700;">
                                        ⭐ Categorías Destacadas
                                    </h3>
                                </div>
                                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; text-align: center;">
                                    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                                        <span style="font-size: 32px; display: block; margin-bottom: 8px;">📱</span>
                                        <strong style="color: #1e293b; font-size: 14px;">Smartphones</strong>
                                    </div>
                                    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                                        <span style="font-size: 32px; display: block; margin-bottom: 8px;">⌚</span>
                                        <strong style="color: #1e293b; font-size: 14px;">Smartwatches</strong>
                                    </div>
                                    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                                        <span style="font-size: 32px; display: block; margin-bottom: 8px;">🎧</span>
                                        <strong style="color: #1e293b; font-size: 14px;">Audio</strong>
                                    </div>
                                    <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                                        <span style="font-size: 32px; display: block; margin-bottom: 8px;">💻</span>
                                        <strong style="color: #1e293b; font-size: 14px;">Tech & Más</strong>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Contacto -->
                            <div style="text-align: center; margin: 30px 0 20px; padding: 20px; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 10px;">
                                <p style="color: #78350f; font-size: 15px; margin: 0; line-height: 1.6;">
                                    <strong>¿Necesitas ayuda?</strong><br>
                                    Nuestro equipo está listo para atenderte<br>
                                    📞 <strong>Contáctanos</strong> en cualquier momento
                                </p>
                            </div>
                            
                            <p style="color: #64748b; font-size: 14px; text-align: center; margin: 25px 0 0; line-height: 1.6;">
                                Gracias por confiar en nosotros. Estamos comprometidos en brindarte 
                                la mejor experiencia de compra y los productos de más alta calidad.
                            </p>
                        </div>
                        
                        <!-- Footer -->
                        <div style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 35px 30px; text-align: center;">
                            <p style="color: #e2e8f0; margin: 0 0 20px; font-size: 16px; font-weight: 600;">
                                ¡Bienvenido a la familia Celupro Co! 🎊
                            </p>
                            
                            <!-- Redes Sociales -->
                            <div style="margin: 25px 0;">
                                <a href="#" style="display: inline-block; margin: 0 8px; width: 40px; height: 40px; background: linear-gradient(135deg, #3b82f6, #1e40af); border-radius: 50%; text-align: center; line-height: 40px; color: white; text-decoration: none; font-size: 18px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">f</a>
                                <a href="#" style="display: inline-block; margin: 0 8px; width: 40px; height: 40px; background: linear-gradient(135deg, #ec4899, #be185d); border-radius: 50%; text-align: center; line-height: 40px; color: white; text-decoration: none; font-size: 18px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">📷</a>
                                <a href="#" style="display: inline-block; margin: 0 8px; width: 40px; height: 40px; background: linear-gradient(135deg, #10b981, #059669); border-radius: 50%; text-align: center; line-height: 40px; color: white; text-decoration: none; font-size: 18px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">💬</a>
                            </div>
                            
                            <!-- Divisor -->
                            <div style="height: 1px; background: rgba(255,255,255,0.1); margin: 25px auto; max-width: 300px;"></div>
                            
                            <!-- Links del footer -->
                            <div style="margin: 20px 0;">
                                <a href="https://celuproco.com.co/" style="color: #94a3b8; text-decoration: none; margin: 0 12px; font-size: 12px; transition: color 0.3s;">Tienda</a>
                                <span style="color: #475569;">•</span>
                                <a href="https://celuproco.com.co/" style="color: #94a3b8; text-decoration: none; margin: 0 12px; font-size: 12px;">Política de Privacidad</a>
                                <span style="color: #475569;">•</span>
                                <a href="https://celuproco.com.co/" style="color: #94a3b8; text-decoration: none; margin: 0 12px; font-size: 12px;">Contáctanos</a>
                            </div>
                            
                            <p style="color: #64748b; font-size: 11px; margin: 20px 0 0; line-height: 1.6;">
                                Este correo fue generado automáticamente por nuestro sistema.<br>
                                Por favor, no respondas a este mensaje.
                            </p>
                            
                            <p style="color: #64748b; font-size: 11px; margin: 15px 0 0; line-height: 1.6;">
                                © 2025 <a href="https://berserkerdev.com/" style="color: #3b82f6; text-decoration: none; font-weight: 600;">BerserkerDev</a> - Todos los derechos reservados<br>
                                Soledad, Atlántico, Colombia
                            </p>
                            
                            <!-- Logo pequeño -->
                            <div style="margin-top: 20px; opacity: 0.7;">
                                <img src="https://raw.githubusercontent.com/Kevin25DC/celupro-assets/refs/heads/main/logo%20de%20prueba%20dos.png" 
                                     alt="Logo" 
                                     style="max-width: 80px; height: auto;">
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

