from django.shortcuts import render, redirect
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from django.utils import timezone
import re
from django.db.models import Count

from .models import (
    Users,
    LoginLogs,
    Leads,
    Assignment,
    Campaign,
    CampaignLeads,
    Tag,
    LeadsTag,
    CustomFields,
    CustomColumn,
)

# ─────────────────────────────────────────────────────────────
#  Helper: ambil atau buat CustomColumn untuk field bawaan
#  (produk, prioritas, catatan)
# ─────────────────────────────────────────────────────────────

BUILTIN_COL_DEFS = {
    "produk":    {"col_type": "text",    "options": []},
    "prioritas": {"col_type": "dropdown","options": ["Tinggi", "Sedang", "Rendah"]},
    "catatan":   {"col_type": "text",    "options": []},
}

def get_builtin_col(name: str) -> CustomColumn:
    """Kembalikan CustomColumn untuk field bawaan."""
    try:
        return CustomColumn.objects.get(name=name)
    except CustomColumn.DoesNotExist:
        raise Exception(f"Kolom bawaan '{name}' belum ada di database.")
    


def get_cf_value(lead, col_name: str):
    """Ambil value CustomFields berdasarkan nama kolom bawaan."""
    col = get_builtin_col(col_name)
    cf  = CustomFields.objects.filter(id_lead=lead, id_col=col).first()
    return cf.value if cf else None

def set_cf_value(lead, col_name: str, value):
    """Simpan / update CustomFields berdasarkan nama kolom bawaan."""
    col = get_builtin_col(col_name)
    cf  = CustomFields.objects.filter(id_lead=lead, id_col=col).first()
    if cf:
        cf.value = value
        cf.save()
    else:
        CustomFields.objects.create(
            id=generate_id(CustomFields, "id", "CFD"),
            id_lead=lead,
            id_col=col,
            value=value,
        )


# ─────────────────────────────────────────────────────────────
#  Auth views
# ─────────────────────────────────────────────────────────────

def login_view(request):
    if request.method == "POST":
        email    = request.POST.get("email")
        password = request.POST.get("password")
        try:
            user = Users.objects.get(email=email)
            if password == user.password:
                request.session['user_id']   = user.id_user
                request.session['user_name'] = user.nama
                request.session['user_role'] = user.role
                log = LoginLogs(id_user=user, login_time=timezone.now())
                log.save()
                return redirect('login_berhasil')
            else:
                return render(request, "leads/login.html", {"error": "Wrong password"})
        except Users.DoesNotExist:
            return render(request, "leads/login.html", {"error": "User not found"})
    return render(request, 'leads/login.html')


from django.contrib.auth.models import User
from django.contrib import messages

def register_view(request):
    role = request.GET.get("role", "admin")

    if request.method == 'POST':
        nama             = request.POST['nama']
        email            = request.POST.get("email")
        asal_perusahaan  = request.POST.get("asal_perusahaan")
        password         = request.POST['password']
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


# ─────────────────────────────────────────────────────────────
#  Page views
# ─────────────────────────────────────────────────────────────

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

def input_manual_page(request):
    if not request.session.get('user_id'):
        return redirect('login')
    if request.session.get('user_role') != 'admin':
        return redirect('dashboard_analisis')
    return render(request, "leads/input_manual.html")

def input_otomatis_page(request):
    if not request.session.get('user_id'):
        return redirect('login')
    if request.session.get('user_role') != 'admin':
        return redirect('dashboard_analisis')
    return render(request, "leads/input_otomatis.html")


# ─────────────────────────────────────────────────────────────
#  Utility
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
#  API Auth
# ─────────────────────────────────────────────────────────────

@csrf_exempt
def api_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data     = json.loads(request.body)
    email    = data.get("email")
    password = data.get("password")

    try:
        user = Users.objects.get(email=email)
    except Users.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    if user.password != password:
        return JsonResponse({"error": "Wrong password"}, status=401)

    LoginLogs.objects.create(id_user=user, login_time=timezone.now())

    return JsonResponse({
        "message": "Login berhasil",
        "user": {
            "id_user":        user.id_user,
            "nama":           user.nama,
            "email":          user.email,
            "role":           user.role,
            "asal_perusahaan": user.asal_perusahaan,
        }
    })


# ─────────────────────────────────────────────────────────────
#  API Leads (input manual / otomatis)
# ─────────────────────────────────────────────────────────────

@csrf_exempt
def api_create_lead(request):
    if request.method == "GET":
        leads = Leads.objects.all()
        data  = []
        for lead in leads:
            campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()
            assignment    = Assignment.objects.filter(id_lead=lead).first()
            data.append({
                "id_lead":     lead.id_lead,
                "nama":        lead.nama,
                "email":       lead.email,
                "no_whatsapp": lead.no_whatsapp,
                "source":      campaign_lead.source          if campaign_lead else None,
                "status":      campaign_lead.funnel_position if campaign_lead else "New",
                "assigned_to": assignment.id_user.nama       if assignment and assignment.id_user else None,
            })
        return JsonResponse({"leads": data})

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body)

    lead = Leads.objects.create(
        id_lead      = generate_id(Leads, "id_lead", "LED"),
        nama         = data.get("nama"),
        email        = data.get("email"),
        no_whatsapp  = data.get("no_whatsapp"),
    )

    CampaignLeads.objects.create(
        id             = generate_id(CampaignLeads, "id", "PIP"),
        id_lead        = lead,
        funnel_position= data.get("status", "New"),
        source         = data.get("source"),
    )

    # Simpan field bawaan melalui helper
    for field in ["produk", "prioritas", "catatan"]:
        if data.get(field):
            set_cf_value(lead, field, data.get(field))

    return JsonResponse({
        "message": "Lead berhasil dibuat",
        "id_lead": lead.id_lead,
    }, status=201)


@csrf_exempt
def api_assign_lead(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data    = json.loads(request.body)
    id_lead = data.get("id_lead")
    id_user = data.get("id_user")

    try:
        lead = Leads.objects.get(id_lead=id_lead)
        user = Users.objects.get(id_user=id_user)
    except Leads.DoesNotExist:
        return JsonResponse({"error": "Lead tidak ditemukan"}, status=404)
    except Users.DoesNotExist:
        return JsonResponse({"error": "User sales tidak ditemukan"}, status=404)

    # Hapus assignment lama jika sudah ada (re-assign)
    Assignment.objects.filter(id_lead=lead).delete()

    assignment = Assignment.objects.create(
        id_assignment = generate_id(Assignment, "id_assignment", "ASN"),
        id_lead       = lead,
        id_user       = user,
        assigned_at   = timezone.now(),
    )

    return JsonResponse({
        "message":       "Lead berhasil di-assign",
        "id_assignment": assignment.id_assignment,
        "lead":          lead.nama,
        "sales":         user.nama,
    }, status=201)


@csrf_exempt
def api_auto_assign(request):
    """
    POST /api/auto-assign/
    Auto-assign semua lead yang belum di-assign ke sales dengan lead paling sedikit.
    Jika ada seri (jumlah lead sama), dipilih secara acak.
    Hanya bisa diakses oleh admin.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # Ambil semua lead yang belum punya assignment
    assigned_lead_ids = Assignment.objects.values_list("id_lead_id", flat=True)
    unassigned_leads  = Leads.objects.exclude(id_lead__in=assigned_lead_ids)

    if not unassigned_leads.exists():
        return JsonResponse({"message": "Tidak ada lead yang perlu di-assign", "assigned_count": 0})

    # Ambil semua sales
    sales_users = list(Users.objects.filter(role="sales"))
    if not sales_users:
        return JsonResponse({"error": "Tidak ada sales yang tersedia"}, status=400)

    assigned_count = 0

    for lead in unassigned_leads:
        # Hitung jumlah lead tiap sales
        sales_counts = []
        for user in sales_users:
            count = Assignment.objects.filter(id_user=user).count()
            sales_counts.append((user, count))

        # Cari jumlah minimum
        min_count = min(c for _, c in sales_counts)

        # Ambil semua sales dengan jumlah minimum (untuk random jika seri)
        candidates = [u for u, c in sales_counts if c == min_count]

        import random
        chosen_sales = random.choice(candidates)

        Assignment.objects.create(
            id_assignment = generate_id(Assignment, "id_assignment", "ASN"),
            id_lead       = lead,
            id_user       = chosen_sales,
            assigned_at   = timezone.now(),
        )
        assigned_count += 1

    return JsonResponse({
        "message":       f"{assigned_count} lead berhasil di-assign secara otomatis",
        "assigned_count": assigned_count,
    })


@csrf_exempt
def api_update_lead_status(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data      = json.loads(request.body)
    id_lead   = data.get("id_lead")
    status    = data.get("status")
    tags      = data.get("tags", [])
    notes     = data.get("notes")
    prioritas = data.get("prioritas")

    try:
        lead = Leads.objects.get(id_lead=id_lead)
    except Leads.DoesNotExist:
        return JsonResponse({"error": "Lead tidak ditemukan"}, status=404)

    # Update funnel position
    campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()
    if campaign_lead:
        campaign_lead.funnel_position = status
        campaign_lead.save()
    else:
        CampaignLeads.objects.create(
            id              = generate_id(CampaignLeads, "id", "CLD"),
            id_lead         = lead,
            funnel_position = status,
        )

    # Update prioritas via helper
    if prioritas:
        set_cf_value(lead, "prioritas", prioritas)

    # Update tags
    for label in tags:
        tag, created = Tag.objects.get_or_create(
            label_tag=label,
            defaults={"id_tag": generate_id(Tag, "id_tag", "TAG")}
        )
        if not LeadsTag.objects.filter(id_leads=lead, id_tag=tag).exists():
            LeadsTag.objects.create(
                id       = generate_id(LeadsTag, "id", "LDT"),
                id_leads = lead,
                id_tag   = tag,
            )

    # Simpan catatan update sebagai custom field bawaan "update_notes"
    if notes:
        col = get_builtin_col("update_notes")
        CustomFields.objects.create(
            id      = generate_id(CustomFields, "id", "CFD"),
            id_lead = lead,
            id_col  = col,
            value   = notes,
        )
        CustomFields.objects.create(
            id     = generate_id(CustomFields, "id", "CFD"),
            id_lead= lead,
            id_col = col,
            value  = notes,
        )

    return JsonResponse({
        "message":   "Status, prioritas, dan tag berhasil diperbarui",
        "id_lead":   lead.id_lead,
        "status":    status,
        "prioritas": prioritas,
        "tags":      tags,
    })


# ─────────────────────────────────────────────────────────────
#  API Dashboard
# ─────────────────────────────────────────────────────────────

def api_dashboard(request):
    from django.db.models import Sum

    total_leads = Leads.objects.count()
    assigned    = Assignment.objects.count()
    unassigned  = total_leads - assigned

    closed_won_count = CampaignLeads.objects.filter(funnel_position="Closed Won").count()
    conversion_rate  = round((closed_won_count / total_leads * 100), 1) if total_leads > 0 else 0

    total_campaign_cost = Campaign.objects.aggregate(total=Sum('production_cost'))['total'] or 0
    cost_per_lead = round(float(total_campaign_cost) / total_leads, 0) if total_leads > 0 else 0

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

    # product_counts: pakai id_col FK ke kolom "produk"
    produk_col = get_builtin_col("produk")
    campaign_counts = (
        CampaignLeads.objects
        .filter(id_camp__isnull=False)
        .values('id_camp__id_campaign', 'id_camp__nama_camp')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return JsonResponse({
        "total_leads":     total_leads,
        "assigned":        assigned,
        "unassigned":      unassigned,
        "conversion_rate": conversion_rate,
        "cost_per_lead":   int(cost_per_lead),
        "status_counts":   list(status_counts),
        "source_counts":   list(source_counts),
        "campaign_counts": list(campaign_counts),
    })

# ─────────────────────────────────────────────────────────────
#  API Campaign
# ─────────────────────────────────────────────────────────────

@csrf_exempt
def api_campaign_list(request):
    if request.method == 'GET':
        campaigns = Campaign.objects.all().order_by('start_date')
        data = []
        for c in campaigns:
            lead_count = CampaignLeads.objects.filter(id_camp=c).count()
            data.append({
                'id_campaign':      c.id_campaign,
                'nama_camp':        c.nama_camp,
                'source':           c.source,
                'production_cost':  float(c.production_cost) if c.production_cost else None,
                'start_date':       str(c.start_date)  if c.start_date  else None,
                'end_date':         str(c.end_date)    if c.end_date    else None,
                'total_leads':      lead_count,
            })
        return JsonResponse({'campaigns': data})

    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Body tidak valid'}, status=400)

        nama_camp       = (payload.get('nama_camp') or '').strip()
        source          = (payload.get('source') or '').strip()
        production_cost = payload.get('production_cost')
        start_date      = payload.get('start_date') or None
        end_date        = payload.get('end_date')   or None

        if not nama_camp:
            return JsonResponse({'error': 'Nama campaign wajib diisi'}, status=400)

        campaign = Campaign.objects.create(
            id_campaign     = generate_id(Campaign, 'id_campaign', 'CMP'),
            nama_camp       = nama_camp,
            source          = source or None,
            production_cost = production_cost or None,
            start_date      = start_date,
            end_date        = end_date,
        )
        return JsonResponse({
            'message':     'Campaign berhasil ditambahkan',
            'id_campaign': campaign.id_campaign,
        }, status=201)

    return JsonResponse({'error': 'Method tidak didukung'}, status=405)


@csrf_exempt
def api_campaign_detail(request, id_campaign):
    try:
        campaign = Campaign.objects.get(id_campaign=id_campaign)
    except Campaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign tidak ditemukan'}, status=404)

    if request.method == 'DELETE':
        # Hapus hanya campaign-nya, CampaignLeads tidak ikut terhapus
        campaign.delete()
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Method tidak didukung'}, status=405)

# ─────────────────────────────────────────────────────────────
#  API Distribusi Lead
# ─────────────────────────────────────────────────────────────

def api_distribusi_stats(request):
    total_leads     = Leads.objects.count()
    pending_count   = CampaignLeads.objects.filter(funnel_position__in=["New"]).count()
    qualified_count = CampaignLeads.objects.filter(funnel_position="Qualified").count()
    status_counts   = {}
    for row in CampaignLeads.objects.values("funnel_position").annotate(total=Count("id")):
        status_counts[row["funnel_position"]] = row["total"]

    return JsonResponse({
        "total_leads": total_leads,
        "pending":     pending_count,
        "qualified":   qualified_count,
        "status_counts": status_counts,
    })

def api_distribusi_leads(request):
    status_filter   = request.GET.get("status", "")
    search_query    = request.GET.get("search", "").strip()
    assigned_filter = request.GET.get("assigned", "")   # "assigned" | "unassigned" | ""
    source_filter   = request.GET.get("source", "")
    prioritas_filter= request.GET.get("prioritas", "")
    sales_filter    = request.GET.get("sales", "")      # id_user
    page            = int(request.GET.get("page", 1))
    per_page        = int(request.GET.get("per_page", 10))

    leads_qs = Leads.objects.prefetch_related('customfields_set__id_col').all()

    if search_query:
        leads_qs = leads_qs.filter(
            Q(nama__icontains=search_query) |
            Q(no_whatsapp__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if status_filter and status_filter.lower() != "all":
        lead_ids = CampaignLeads.objects.filter(
            funnel_position=status_filter
        ).values_list("id_lead_id", flat=True)
        leads_qs = leads_qs.filter(id_lead__in=lead_ids)

    # Filter assigned / unassigned
    if assigned_filter == "assigned":
        assigned_ids = Assignment.objects.values_list("id_lead_id", flat=True)
        leads_qs = leads_qs.filter(id_lead__in=assigned_ids)
    elif assigned_filter == "unassigned":
        assigned_ids = Assignment.objects.values_list("id_lead_id", flat=True)
        leads_qs = leads_qs.exclude(id_lead__in=assigned_ids)

    # Filter by source
    if source_filter:
        lead_ids = CampaignLeads.objects.filter(
            source__iexact=source_filter
        ).values_list("id_lead_id", flat=True)
        leads_qs = leads_qs.filter(id_lead__in=lead_ids)

    # Filter by sales
    if sales_filter:
        lead_ids = Assignment.objects.filter(
            id_user__id_user=sales_filter
        ).values_list("id_lead_id", flat=True)
        leads_qs = leads_qs.filter(id_lead__in=lead_ids)

    # Filter by prioritas
    if prioritas_filter:
        prioritas_col = get_builtin_col("prioritas")
        lead_ids = CustomFields.objects.filter(
            id_col=prioritas_col,
            value__iexact=prioritas_filter
        ).values_list("id_lead_id", flat=True)
        leads_qs = leads_qs.filter(id_lead__in=lead_ids)

    total      = leads_qs.count()
    start      = (page - 1) * per_page
    leads_page = leads_qs[start: start + per_page]

    data = []
    for lead in leads_page:
        campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()
        assignment    = Assignment.objects.filter(id_lead=lead).order_by("-assigned_at").first()

        cf_by_name = {}
        cf_by_id   = {}
        for cf in lead.customfields_set.all():
            if cf.id_col_id is not None:
                col_name = cf.id_col.name if cf.id_col else None
                if col_name in BUILTIN_COL_DEFS:
                    cf_by_name[col_name] = cf.value
                else:
                    cf_by_id[str(cf.id_col_id)] = cf.value

        data.append({
            "id_lead":       lead.id_lead,
            "nama":          lead.nama,
            "email":         lead.email,
            "no_whatsapp":   lead.no_whatsapp,
            "source":        campaign_lead.source          if campaign_lead else None,
            "status":        campaign_lead.funnel_position if campaign_lead else "New",
            "assigned_to":   assignment.id_user.nama       if assignment and assignment.id_user else None,
            "assigned_id":   assignment.id_user.id_user    if assignment and assignment.id_user else None,
            "prioritas":     cf_by_name.get("prioritas"),
            "produk":        cf_by_name.get("produk"),      
            "catatan":       cf_by_name.get("catatan"),     
            "custom_fields": cf_by_id,
            "id_campaign":   campaign_lead.id_camp.id_campaign if campaign_lead and campaign_lead.id_camp else None,
            "nama_campaign": campaign_lead.id_camp.nama_camp   if campaign_lead and campaign_lead.id_camp else None,
        })

    return JsonResponse({
        "leads":    data,
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
    })



def api_sales_list(request):
    sales_users = Users.objects.filter(role="sales")
    data = []
    for user in sales_users:
        lead_count = Assignment.objects.filter(id_user=user).count()
        data.append({
            "id_user":    user.id_user,
            "nama":       user.nama,
            "email":      user.email,
            "lead_aktif": lead_count,
        })
    return JsonResponse({"sales": data})


# ─────────────────────────────────────────────────────────────
#  API Kanban
# ─────────────────────────────────────────────────────────────

FUNNEL_ORDER = ["New", "Contacted", "Qualified", "Proposal", "Closed Won", "Closed Lost"]

def api_kanban_leads(request):
    search_query = request.GET.get("search", "").strip()

    leads_qs = Leads.objects.all()
    if search_query:
        leads_qs = leads_qs.filter(
            Q(nama__icontains=search_query) |
            Q(no_whatsapp__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    prioritas_col = get_builtin_col("prioritas")
    columns       = {col: [] for col in FUNNEL_ORDER}

    for lead in leads_qs:
        campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()
        assignment    = Assignment.objects.filter(id_lead=lead).order_by("-assigned_at").first()

        # Ambil prioritas via FK
        prioritas_cf = CustomFields.objects.filter(id_lead=lead, id_col=prioritas_col).first()
        prioritas    = prioritas_cf.value if prioritas_cf else None

        lead_tags = list(
            LeadsTag.objects.filter(id_leads=lead)
            .select_related("id_tag")
            .values_list("id_tag__label_tag", flat=True)
        )

        funnel = campaign_lead.funnel_position if campaign_lead else "New"
        if funnel not in columns:
            funnel = "New"

        columns[funnel].append({
            "id_lead":     lead.id_lead,
            "nama":        lead.nama,
            "email":       lead.email,
            "no_whatsapp": lead.no_whatsapp,
            "source":      campaign_lead.source if campaign_lead else None,
            "status":      funnel,
            "prioritas":   prioritas,
            "tags":        lead_tags,
            "assigned_to": assignment.id_user.nama    if assignment and assignment.id_user else None,
            "assigned_id": assignment.id_user.id_user if assignment and assignment.id_user else None,
        })

    result = [{"column": col, "leads": columns[col]} for col in FUNNEL_ORDER]
    return JsonResponse({"columns": result})


def api_tags_list(request):
    tags = Tag.objects.all().values("id_tag", "label_tag")
    return JsonResponse({"tags": list(tags)})


# ─────────────────────────────────────────────────────────────
#  API Lead Detail (GET / PATCH / DELETE)
# ─────────────────────────────────────────────────────────────

@csrf_exempt
def lead_detail(request, id):
    try:
        lead = Leads.objects.get(id_lead=id)
    except Leads.DoesNotExist:
        return JsonResponse({'error': 'Lead tidak ditemukan'}, status=404)

    if request.method == 'GET':
        campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()
        assignment    = Assignment.objects.filter(id_lead=lead).order_by("-assigned_at").first()
        return JsonResponse({
        'id_lead':     lead.id_lead,
        'nama':        lead.nama,
        'no_whatsapp': lead.no_whatsapp,
        'email':       lead.email,
        'source':      campaign_lead.source          if campaign_lead else None,
        'status':      campaign_lead.funnel_position if campaign_lead else 'New',
        'produk':      get_cf_value(lead, 'produk'),
        'prioritas':   get_cf_value(lead, 'prioritas'),
        'catatan':     get_cf_value(lead, 'catatan'),
        'assigned_id': assignment.id_user.id_user if assignment and assignment.id_user else None,
        'assigned_to': assignment.id_user.nama    if assignment and assignment.id_user else None,
        'id_campaign':   campaign_lead.id_camp.id_campaign if campaign_lead and campaign_lead.id_camp else None,
        'nama_campaign': campaign_lead.id_camp.nama_camp   if campaign_lead and campaign_lead.id_camp else None,
        })

    elif request.method in ['PATCH', 'PUT']:
        data = json.loads(request.body)

        for field in ['nama', 'no_whatsapp', 'email']:
            if field in data:
                setattr(lead, field, data[field])
        lead.save()

        # Di dalam elif request.method in ['PATCH', 'PUT']:
        if 'id_campaign' in data:
            campaign_id = data['id_campaign']
            campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()
            if campaign_id:
                try:
                    campaign = Campaign.objects.get(id_campaign=campaign_id)
                    if campaign_lead:
                        campaign_lead.id_camp = campaign
                        campaign_lead.save()
                    else:
                        CampaignLeads.objects.create(
                            id=generate_id(CampaignLeads, "id", "PIP"),
                            id_lead=lead,
                            id_camp=campaign,
                            funnel_position='New',
                        )
                except Campaign.DoesNotExist:
                    pass
            else:
                # Kosongkan campaign
                if campaign_lead:
                    campaign_lead.id_camp = None
                    campaign_lead.save()

        campaign_lead = CampaignLeads.objects.filter(id_lead=lead).first()
        if campaign_lead:
            if 'source' in data:
                campaign_lead.source = data['source']
            if 'status' in data:
                campaign_lead.funnel_position = data['status']
            campaign_lead.save()
        else:
            CampaignLeads.objects.create(
                id              = generate_id(CampaignLeads, "id", "PIP"),
                id_lead         = lead,
                funnel_position = data.get('status', 'New'),
                source          = data.get('source'),
            )

        # Update field bawaan via helper
        for field in ['produk', 'prioritas', 'catatan']:
            if field in data:
                set_cf_value(lead, field, data[field])

        return JsonResponse({'ok': True})

    elif request.method == 'DELETE':
        Assignment.objects.filter(id_lead=lead).delete()
        CampaignLeads.objects.filter(id_lead=lead).delete()
        CustomFields.objects.filter(id_lead=lead).delete()
        LeadsTag.objects.filter(id_leads=lead).delete()
        lead.delete()
        return JsonResponse({'ok': True})


# ─────────────────────────────────────────────────────────────
#  API Custom Columns
# ─────────────────────────────────────────────────────────────

def _col_to_dict(col):
    return {
        'id':      str(col.id_col),
        'name':    col.name,
        'type':    col.col_type,
        'options': col.options or [],
        'order':   col.col_order,
    }

def _get_builtin_prefs(request):
    return request.session.get('col_builtin_prefs', {
        'nama': True, 'status': True, 'prioritas': True,
        'source': True, 'assigned_to': True,
    })

def _set_builtin_prefs(request, prefs):
    request.session['col_builtin_prefs'] = prefs
    request.session.modified = True


@csrf_exempt
def columns_list(request):
    if request.method == 'GET':
        # Tampilkan hanya kolom kustom (col_order >= 0), bukan kolom bawaan
        return JsonResponse({
            'builtin': _get_builtin_prefs(request),
            'custom':  [_col_to_dict(c) for c in CustomColumn.objects.filter(col_order__gte=0)],
        })

    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Body tidak valid'}, status=400)

        action = payload.get('action')

        if action == 'toggle_builtin':
            key     = payload.get('key', '')
            visible = bool(payload.get('visible', True))
            VALID   = {'nama', 'status', 'prioritas', 'source', 'assigned_to'}
            if key not in VALID:
                return JsonResponse({'error': f'Key tidak valid: {key}'}, status=400)
            if key == 'nama' and not visible:
                return JsonResponse({'error': 'Kolom nama tidak bisa dinonaktifkan'}, status=400)
            prefs      = _get_builtin_prefs(request)
            prefs[key] = visible
            _set_builtin_prefs(request, prefs)
            return JsonResponse({'ok': True, 'key': key, 'visible': visible})

        elif action == 'add_custom':
            name     = (payload.get('name') or '').strip()
            col_type = payload.get('type', 'text')
            options  = payload.get('options', [])

            if not name:
                return JsonResponse({'error': 'Nama kolom wajib diisi'}, status=400)
            if len(name) > 100:
                return JsonResponse({'error': 'Nama kolom maksimal 100 karakter'}, status=400)
            if col_type not in ('text', 'date', 'dropdown'):
                return JsonResponse({'error': 'Tipe tidak valid'}, status=400)
            if col_type == 'dropdown' and not options:
                return JsonResponse({'error': 'Dropdown butuh minimal 1 pilihan'}, status=400)
            if CustomColumn.objects.filter(name__iexact=name).exists():
                return JsonResponse({'error': f'Kolom "{name}" sudah ada'}, status=400)

            col = CustomColumn.objects.create(
                name      = name,
                col_type  = col_type,
                options   = [str(o).strip() for o in options if str(o).strip()],
                col_order = CustomColumn.objects.filter(col_order__gte=0).count(),
            )
            return JsonResponse({'ok': True, 'column': _col_to_dict(col)}, status=201)

        elif action == 'reorder':
            for idx, col_id in enumerate(payload.get('ids', [])):
                try:
                    CustomColumn.objects.filter(id_col=col_id).update(col_order=idx)
                except Exception:
                    pass
            return JsonResponse({'ok': True})

        return JsonResponse({'error': f'Action tidak dikenal: {action}'}, status=400)

    return JsonResponse({'error': 'Method tidak didukung'}, status=405)


@csrf_exempt
def column_detail(request, col_id):
    try:
        col = CustomColumn.objects.get(id_col=col_id)
    except CustomColumn.DoesNotExist:
        return JsonResponse({'error': 'Kolom tidak ditemukan'}, status=404)

    if request.method == 'GET':
        return JsonResponse(_col_to_dict(col))

    if request.method == 'PATCH':
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Body tidak valid'}, status=400)

        if 'name' in payload:
            name = payload['name'].strip()
            if not name:
                return JsonResponse({'error': 'Nama tidak boleh kosong'}, status=400)
            if CustomColumn.objects.filter(name__iexact=name).exclude(id_col=col.id_col).exists():
                return JsonResponse({'error': f'Nama "{name}" sudah dipakai'}, status=400)
            col.name = name

        if 'options' in payload and col.col_type == 'dropdown':
            opts = [str(o).strip() for o in payload['options'] if str(o).strip()]
            if not opts:
                return JsonResponse({'error': 'Dropdown butuh minimal 1 pilihan'}, status=400)
            col.options = opts

        col.save()
        return JsonResponse({'ok': True, 'column': _col_to_dict(col)})

    if request.method == 'DELETE':
        # Hapus semua CustomFields yang merujuk kolom ini (via FK)
        deleted_count = CustomFields.objects.filter(id_col=col).delete()[0]
        col.delete()
        return JsonResponse({'ok': True, 'deleted_fields': deleted_count})

    return JsonResponse({'error': 'Method tidak didukung'}, status=405)


@csrf_exempt
def lead_custom_fields(request, lead_id):
    if request.method not in ('PATCH', 'PUT', 'POST'):
        return JsonResponse({'error': 'Method tidak didukung'}, status=405)

    try:
        lead = Leads.objects.get(id_lead=lead_id)
    except Leads.DoesNotExist:
        return JsonResponse({'error': 'Lead tidak ditemukan'}, status=404)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Body tidak valid'}, status=400)

    updated = {}
    for col_id_str, value in payload.items():
        try:
            col = CustomColumn.objects.get(id_col=int(col_id_str))
        except (CustomColumn.DoesNotExist, ValueError):
            continue

        value_str = str(value).strip() if value is not None else ''

        if col.col_type == 'dropdown' and value_str and value_str not in col.options:
            continue

        existing = CustomFields.objects.filter(id_lead=lead, id_col=col).first()
        if existing:
            existing.value = value_str
            existing.save()
        else:
            CustomFields.objects.create(
                id      = generate_id(CustomFields, "id", "CFD"),
                id_lead = lead,
                id_col  = col,
                value   = value_str,
            )

        updated[col_id_str] = value_str

    return JsonResponse({'ok': True, 'updated': updated})