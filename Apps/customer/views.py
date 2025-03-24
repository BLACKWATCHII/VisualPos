from django.shortcuts import render, redirect
from .forms import ClienteForm
from django.contrib.auth.decorators import login_required
from models import Cliente


