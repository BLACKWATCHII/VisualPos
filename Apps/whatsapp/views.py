import os

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from Invoice.models import Invoice
from Invoice.views import generate_temp_invoice_pdf_safe


def _baileys_base_url() -> str:
	return getattr(settings, 'BAILEYS_URL', 'http://127.0.0.1:3030')


def _normalize_phone_for_whatsapp(raw_phone: str) -> str:
	"""Return digits-only international number.

	If phone has 10 digits, assumes default country code from settings (CO=57).
	"""

	digits = ''.join(ch for ch in str(raw_phone or '') if ch.isdigit())
	if not digits:
		return ''

	default_cc = getattr(settings, 'WHATSAPP_DEFAULT_COUNTRY_CODE', '57')
	if len(digits) == 10 and default_cc and not digits.startswith(default_cc):
		return f"{default_cc}{digits}"
	return digits


@login_required
@require_GET
def conexion_whatsapp(request):
	return render(request, 'whatsapp/conexion_whatsapp.html')


@login_required
@require_GET
def whatsapp_qr_status(request):
	"""Proxy to Node service to avoid CORS and keep a single origin."""
	try:
		resp = requests.get(f"{_baileys_base_url()}/api/qr", timeout=3)
		return JsonResponse(resp.json(), status=resp.status_code)
	except Exception as e:
		return JsonResponse(
			{
				'connected': False,
				'connection': 'down',
				'qr_data_url': None,
				'error': str(e),
			},
			status=503,
		)


@login_required
@require_POST
def whatsapp_logout(request):
	"""Disconnect WhatsApp session (logout) and clear auth state in Node service."""
	try:
		resp = requests.post(f"{_baileys_base_url()}/api/logout", timeout=10)
		try:
			payload = resp.json()
		except Exception:
			payload = {'raw': resp.text}
		return JsonResponse(payload, status=resp.status_code)
	except Exception as e:
		return JsonResponse({'ok': False, 'error': str(e)}, status=503)


@login_required
@require_POST
def send_invoice_whatsapp(request, invoice_id: int):
	"""Generate a temp PDF and send it via Baileys as document."""
	invoice = get_object_or_404(Invoice, id=invoice_id)
	customer = invoice.customer
	if not customer:
		return JsonResponse({'success': False, 'message': 'La factura no tiene cliente asignado.'}, status=400)

	phone = _normalize_phone_for_whatsapp(getattr(customer, 'phone', ''))
	if not phone:
		return JsonResponse({'success': False, 'message': 'El cliente no tiene teléfono registrado.'}, status=400)

	pdf_path = None
	try:
		pdf_path = generate_temp_invoice_pdf_safe(invoice)
		filename = f"Factura_{invoice.invoice_number}.pdf"

		with open(pdf_path, 'rb') as f:
			resp = requests.post(
				f"{_baileys_base_url()}/api/send",
				data={'to': phone, 'filename': filename},
				files={'file': (filename, f, 'application/pdf')},
				timeout=60,
			)

		if resp.status_code >= 400:
			try:
				payload = resp.json()
			except Exception:
				payload = {'error': resp.text}
			return JsonResponse(
				{
					'success': False,
					'message': payload.get('error') or 'Error enviando por WhatsApp',
					'details': payload,
				},
				status=resp.status_code,
			)

		return JsonResponse({'success': True, 'message': f'Factura enviada por WhatsApp a {phone}.'})
	except Exception as e:
		return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)
	finally:
		try:
			if pdf_path and os.path.exists(pdf_path):
				os.remove(pdf_path)
		except Exception:
			pass


@login_required
@require_POST
def send_file_whatsapp(request):
	"""Send an uploaded file (PDF) with fixed message.

	Expects multipart/form-data: phone, file
	"""
	phone = _normalize_phone_for_whatsapp(request.POST.get('phone'))
	if not phone:
		return JsonResponse({'success': False, 'message': 'Teléfono inválido.'}, status=400)

	up = request.FILES.get('file')
	if not up:
		return JsonResponse({'success': False, 'message': 'Falta el archivo.'}, status=400)

	filename = up.name or 'Factura.pdf'
	try:
		resp = requests.post(
			f"{_baileys_base_url()}/api/send",
			data={'to': phone, 'filename': filename},
			files={'file': (filename, up.read(), up.content_type or 'application/pdf')},
			timeout=60,
		)
		if resp.status_code >= 400:
			try:
				payload = resp.json()
			except Exception:
				payload = {'error': resp.text}
			return JsonResponse(
				{'success': False, 'message': payload.get('error') or 'Error enviando', 'details': payload},
				status=resp.status_code,
			)

		return JsonResponse({'success': True, 'message': f'Enviado por WhatsApp a {phone}.'})
	except Exception as e:
		return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_GET
def ping_evolution(request):
	"""Keeps existing route name; now pings Baileys service."""
	try:
		resp = requests.get(f"{_baileys_base_url()}/health", timeout=2)
		return JsonResponse(resp.json(), status=resp.status_code)
	except Exception as e:
		return JsonResponse({'ok': False, 'error': str(e)}, status=503)
