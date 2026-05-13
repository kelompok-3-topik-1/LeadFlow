from django.shortcuts import render, redirect
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from django.utils import timezone
import re

from .models import (
    Users,
    LoginLogs,
    Leads,
    Assignment,
    CampaignLeads,
    Tag,
    LeadsTag,
    CustomFields,
)

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = Users.objects.get(email=email)

            if password == user.password:
                request.session['user_id'] = user.id_user
                request.session['user_name'] = user.nama

                log = LoginLogs(
                    id_user=user,
                    login_time=timezone.now()
                )
                log.save()

                return redirect('login_berhasil')

            else:
                return render(request, "leads/login.html", {
                    "error": "Wrong password"
                })

        except Users.DoesNotExist:
            return render(request, "leads/login.html", {
                "error": "User not found"
            })
    return render(request, 'leads/login.html')


from django.contrib.auth.models import User
from django.contrib import messages

def register_view(request):
    role = request.GET.get("role", "admin")

    if request.method == 'POST':
        nama = request.POST['nama']
        email = request.POST.get("email")
        asal_perusahaan = request.POST.get("asal_perusahaan")
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            if User.objects.filter(email=email).exists():
                return render(request, 'leads/register.html', {'error': 'Username sudah ada'})
            else:
                user = Users.objects.create(
                    nama=nama,
                    email=email,
                    password=password,
                    role=role,
                    asal_perusahaan=asal_perusahaan
                )
                user.save()

                return redirect('login')
        else:
            return render(request, 'leads/register.html', {'error': 'Password tidak sama'})

    return render(request, 'leads/register.html')

def home(request):
    return render(request, "leads/home_page.html")

def loginberhasil(request):
    return render(request, "leads/login_berhasil.html")

def dashboard_analisis(request):
    return render(request, "leads/dashboard_analisis.html")

def distribusi_lead_page(request):
    return render(request, "leads/distribusi_lead.html")

def update_leads_page(request):
    return render(request, "leads/update_leads.html")


def generate_id(model, field_name, prefix):
    values = model.objects.filter(
        **{f"{field_name}__startswith": prefix}
    ).values_list(field_name, flat=True)

    max_number = 0

    for value in values:
        match = re.search(r'(\d+)$', str(value))
        if match:
            number = int(match.group(1))
            if number > max_number:
                max_number = number

    new_number = max_number + 1
    return f"{prefix}{new_number:03d}"

@csrf_exempt
def api_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body)

    email = data.get("email")
    password = data.get("password")

    try:
        user = Users.objects.get(email=email)
    except Users.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    if user.password != password:
        return JsonResponse({"error": "Wrong password"}, status=401)

    LoginLogs.objects.create(
        id_user=user,
        login_time=timezone.now()
    )

    return JsonResponse({
        "message": "Login berhasil",
        "user": {
            "id_user": user.id_user,
            "nama": user.nama,
            "email": user.email,
            "role": user.role,
            "asal_perusahaan": user.asal_perusahaan,
        }
    })

@csrf_exempt
def api_create_lead(request):
    if request.method == "GET":
        leads = Leads.objects.all()

        data = []
        for lead in leads:
            campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()
            assignment = Assignment.objects.filter(id_lead=lead).first()

            data.append({
                "id_lead": lead.id_lead,
                "nama": lead.nama,
                "email": lead.email,
                "no_whatsapp": lead.no_whatsapp,
                "source": campaign_lead.source if campaign_lead else None,
                "status": campaign_lead.funnel_position if campaign_lead else "New",
                "assigned_to": assignment.id_user.nama if assignment and assignment.id_user else None,
            })

        return JsonResponse({"leads": data})

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body)

    lead = Leads.objects.create(
        id_lead=generate_id(Leads, "id_lead", "LED"),
        nama=data.get("nama"),
        email=data.get("email"),
        no_whatsapp=data.get("no_whatsapp")
    )

    CampaignLeads.objects.create(
        id=generate_id(CampaignLeads, "id", "PIP"),
        id_lead=lead,
        funnel_position=data.get("status", "New"),
        source=data.get("source")
    )

    if data.get("produk"):
        CustomFields.objects.create(
            id=generate_id(CustomFields, "id", "CFD"),
            id_lead=lead,
            field_name="produk",
            value=data.get("produk")
        )

    if data.get("prioritas"):
        CustomFields.objects.create(
            id=generate_id(CustomFields, "id", "CFD"),
            id_lead=lead,
            field_name="prioritas",
            value=data.get("prioritas")
        )

    if data.get("catatan"):
        CustomFields.objects.create(
            id=generate_id(CustomFields, "id", "CFD"),
            id_lead=lead,
            field_name="catatan",
            value=data.get("catatan")
        )

    return JsonResponse({
        "message": "Lead berhasil dibuat",
        "id_lead": lead.id_lead
    }, status=201)

@csrf_exempt
def api_assign_lead(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body)

    id_lead = data.get("id_lead")
    id_user = data.get("id_user")

    try:
        lead = Leads.objects.get(id_lead=id_lead)
        user = Users.objects.get(id_user=id_user)
    except Leads.DoesNotExist:
        return JsonResponse({"error": "Lead tidak ditemukan"}, status=404)
    except Users.DoesNotExist:
        return JsonResponse({"error": "User sales tidak ditemukan"}, status=404)

    assignment = Assignment.objects.create(
        id_assignment=generate_id(Assignment, "id_assignment", "ASN"),
        id_lead=lead,
        id_user=user,
        assigned_at=timezone.now()
    )

    return JsonResponse({
        "message": "Lead berhasil di-assign",
        "id_assignment": assignment.id_assignment,
        "lead": lead.nama,
        "sales": user.nama
    }, status=201)

@csrf_exempt
def api_update_lead_status(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body)

    id_lead = data.get("id_lead")
    status = data.get("status")
    tags = data.get("tags", [])
    notes = data.get("notes")

    try:
        lead = Leads.objects.get(id_lead=id_lead)
    except Leads.DoesNotExist:
        return JsonResponse({"error": "Lead tidak ditemukan"}, status=404)

    campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()

    if campaign_lead:
        campaign_lead.funnel_position = status
        campaign_lead.save()
    else:
        CampaignLeads.objects.create(
            id=generate_id(CampaignLeads, "id", "CLD"),
            id_lead=lead,
            funnel_position=status
        )

    for label in tags:
        tag, created = Tag.objects.get_or_create(
            label_tag=label,
            defaults={"id_tag": generate_id(Tag, "id_tag", "TAG")}
        )

        exists = LeadsTag.objects.filter(id_leads=lead, id_tag=tag).exists()
        if not exists:
            LeadsTag.objects.create(
                id=generate_id(LeadsTag, "id", "LDT"),
                id_leads=lead,
                id_tag=tag
            )

    if notes:
        CustomFields.objects.create(
            id=generate_id(CustomFields, "id", "CFD"),
            id_lead=lead,
            field_name="update_notes",
            value=notes
        )

    return JsonResponse({
        "message": "Status dan tag berhasil diperbarui",
        "id_lead": lead.id_lead,
        "status": status,
        "tags": tags
    })

def api_dashboard(request):
    total_leads = Leads.objects.count()
    assigned = Assignment.objects.count()
    unassigned = total_leads - assigned

    status_counts = (
        CampaignLeads.objects
        .values("funnel_position")
        .annotate(total=Count("id"))
    )

    source_counts = (
        CampaignLeads.objects
        .values("source")
        .annotate(total=Count("id"))
    )

    return JsonResponse({
        "total_leads": total_leads,
        "assigned": assigned,
        "unassigned": unassigned,
        "status_counts": list(status_counts),
        "source_counts": list(source_counts),
    })


# ─────────────────────────────────────────────────────────────
#  API BARU untuk halaman Distribusi Lead
# ─────────────────────────────────────────────────────────────

def api_distribusi_stats(request):
    """
    Endpoint: GET /api/distribusi/stats/
    Mengembalikan stat cards: total leads, pending (New), qualified.
    """
    total_leads = Leads.objects.count()

    # Hitung berdasarkan funnel_position di campaign_leads
    pending_count = CampaignLeads.objects.filter(
        funnel_position__in=["New"]
    ).count()

    qualified_count = CampaignLeads.objects.filter(
        funnel_position="Qualified"
    ).count()

    # Jumlah per status untuk tab
    status_counts = {}
    for row in CampaignLeads.objects.values("funnel_position").annotate(total=Count("id")):
        status_counts[row["funnel_position"]] = row["total"]

    return JsonResponse({
        "total_leads": total_leads,
        "pending": pending_count,
        "qualified": qualified_count,
        "status_counts": status_counts,
    })


def api_distribusi_leads(request):
    """
    Endpoint: GET /api/distribusi/leads/?status=&search=&page=&per_page=
    Mengembalikan daftar leads dengan filter status dan pencarian nama/WA.
    """
    status_filter = request.GET.get("status", "")     # e.g. "New", "Contacted", …
    search_query  = request.GET.get("search", "").strip()
    page          = int(request.GET.get("page", 1))
    per_page      = int(request.GET.get("per_page", 10))

    # Base queryset: ambil semua leads
    leads_qs = Leads.objects.all()

    # Filter pencarian (nama atau no_whatsapp)
    if search_query:
        leads_qs = leads_qs.filter(
            Q(nama__icontains=search_query) |
            Q(no_whatsapp__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Filter berdasarkan status funnel
    if status_filter and status_filter.lower() != "all":
        # Ambil id_lead yang sesuai status dari campaign_leads
        lead_ids = CampaignLeads.objects.filter(
            funnel_position=status_filter
        ).values_list("id_lead_id", flat=True)
        leads_qs = leads_qs.filter(id_lead__in=lead_ids)

    total = leads_qs.count()
    start = (page - 1) * per_page
    end   = start + per_page
    leads_page = leads_qs[start:end]

    data = []
    for lead in leads_page:
        campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()
        # Ambil assignment terbaru
        assignment    = Assignment.objects.filter(id_lead=lead).order_by("-assigned_at").first()

        data.append({
            "id_lead":     lead.id_lead,
            "nama":        lead.nama,
            "email":       lead.email,
            "no_whatsapp": lead.no_whatsapp,
            "source":      campaign_lead.source          if campaign_lead else None,
            "status":      campaign_lead.funnel_position if campaign_lead else "New",
            "assigned_to": assignment.id_user.nama       if assignment and assignment.id_user else None,
            "assigned_id": assignment.id_user.id_user    if assignment and assignment.id_user else None,
        })

    return JsonResponse({
        "leads":    data,
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
    })


def api_sales_list(request):
    """
    Endpoint: GET /api/sales/
    Mengembalikan daftar user role=sales beserta jumlah lead aktif masing-masing.
    """
    sales_users = Users.objects.filter(role="sales")

    data = []
    for user in sales_users:
        lead_count = Assignment.objects.filter(id_user=user).count()
        data.append({
            "id_user":   user.id_user,
            "nama":      user.nama,
            "email":     user.email,
            "lead_aktif": lead_count,
        })

    return JsonResponse({"sales": data})