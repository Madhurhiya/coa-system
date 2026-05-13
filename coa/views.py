import os, json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.conf import settings
from xhtml2pdf import pisa
from itertools import groupby

from django.contrib.auth.models import User
from django.contrib import messages
from .models import (Category, TestParameter, COA, COAResult,
                     COACustomField, COALabel, ItemMaster, Customer, UserProfile)
from .forms import COAForm


# ================================================================
# LINK CALLBACK — makes images work in xhtml2pdf
# ================================================================
def link_callback(uri, rel):
    if uri.startswith(settings.STATIC_URL):
        relative = uri[len(settings.STATIC_URL):]
        for static_dir in getattr(settings, 'STATICFILES_DIRS', []):
            path = os.path.join(static_dir, relative)
            if os.path.exists(path):
                return path
        if getattr(settings, 'STATIC_ROOT', None):
            path = os.path.join(settings.STATIC_ROOT, relative)
            if os.path.exists(path):
                return path
    if hasattr(settings, 'MEDIA_URL') and uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri[len(settings.MEDIA_URL):])
        if os.path.exists(path):
            return path
    return uri


# ================================================================
# AJAX — Item Lookup
# ================================================================
@login_required
def item_lookup(request):
    name = request.GET.get('name', '').strip()
    if not name:
        return JsonResponse({})
    try:
        item = ItemMaster.objects.get(item_name__iexact=name)
        return JsonResponse({
            'botanical_name': item.botanical_name,
            'plant_part':     item.plant_part,
            'item_category':  item.item_category,
        })
    except ItemMaster.DoesNotExist:
        return JsonResponse({})


# ================================================================
# AJAX — Item Search autocomplete
# ================================================================
@login_required
def item_search(request):
    q     = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    if not q:
        return JsonResponse({'results': []})
    items = ItemMaster.objects.filter(
        item_name__icontains=q
    ).values('item_name', 'item_category', 'botanical_name', 'plant_part')[:limit]
    return JsonResponse({'results': list(items)})


# ================================================================
# AJAX — Customer Search autocomplete
# ================================================================
@login_required
def customer_search(request):
    q     = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    if not q:
        return JsonResponse({'results': []})
    customers = Customer.objects.filter(
        name__icontains=q
    ).values_list('name', flat=True)[:limit]
    return JsonResponse({'results': list(customers)})


# ================================================================
# COA LIST
# ================================================================
@login_required
def coa_list(request):
    query    = request.GET.get('q', '').strip()
    customer = request.GET.get('customer', '').strip()
    item     = request.GET.get('item', '').strip()
    coas     = COA.objects.all().order_by('-created_at')

    if query:
        coas = coas.filter(
            Q(product_name__icontains=query)  |
            Q(batch_no__icontains=query)       |
            Q(customer_name__icontains=query)  |
            Q(botanical_name__icontains=query)
        )
    if customer:
        coas = coas.filter(customer_name__icontains=customer)
    if item:
        coas = coas.filter(product_name__icontains=item)

    return render(request, 'coa/coa_list.html', {
        'coas':     coas,
        'query':    query,
        'customer': customer,
        'item':     item,
    })


# ================================================================
# DELETE COA
# ================================================================
@login_required
def delete_coa(request, coa_id):
    coa = get_object_or_404(COA, id=coa_id)
    if request.method == 'POST':
        coa.delete()
        return redirect('coa_list')
    return render(request, 'coa/confirm_delete.html', {'coa': coa})


# ================================================================
# CREATE COA
# — FIX 1: reads custom_is_heading (not custom_field_is_heading)
# — FIX 2: saves created_by
# ================================================================
@login_required
def create_coa(request):
    form = COAForm(request.POST or None)
    grouped_parameters = []

    if request.method == 'POST':

        if 'load_fields' in request.POST:
            category_id = request.POST.get('category')
            if category_id:
                parameters = TestParameter.objects.filter(
                    category_id=category_id
                ).select_related('group').order_by('group__order', 'order')
                for group_key, group_items in groupby(parameters, key=lambda p: p.group):
                    grouped_parameters.append({'group': group_key, 'params': list(group_items)})

        elif 'save_coa' in request.POST:
            if form.is_valid():
                # FIX 2: save created_by
                coa = form.save(commit=False)
                coa.created_by = request.user
                coa.save()

                category_id = request.POST.get('category')
                parameters  = TestParameter.objects.filter(category_id=category_id)

                for param in parameters:
                    value             = request.POST.get(f'param_{param.id}', '').strip()
                    standard_override = request.POST.get(f'standard_{param.id}', '').strip()
                    if value:
                        COAResult.objects.create(
                            coa=coa, parameter=param, result=value,
                            standard_override=standard_override if standard_override != param.specification else ''
                        )

                # FIX 1: read custom_is_heading
                names    = request.POST.getlist('custom_field_name')
                specs    = request.POST.getlist('custom_field_spec')
                results  = request.POST.getlist('custom_field_result')
                headings = request.POST.getlist('custom_is_heading')
                for i, name in enumerate(names):
                    name = name.strip()
                    if name:
                        is_heading = (headings[i] == '1') if i < len(headings) else False
                        COACustomField.objects.create(
                            coa=coa, field_name=name,
                            specification=specs[i]   if i < len(specs)   else '',
                            result=results[i]         if i < len(results) else '',
                            order=i,
                            is_heading=is_heading,
                        )
                return redirect('coa_detail', coa_id=coa.id)

            else:
                category_id = request.POST.get('category')
                if category_id:
                    parameters = TestParameter.objects.filter(
                        category_id=category_id
                    ).select_related('group').order_by('group__order', 'order')
                    for group_key, group_items in groupby(parameters, key=lambda p: p.group):
                        grouped_parameters.append({'group': group_key, 'params': list(group_items)})

    return render(request, 'coa/create_coa.html', {
        'form':               form,
        'grouped_parameters': grouped_parameters,
        'posted_data':        request.POST if request.method == 'POST' else {},
        'prev_results':       {},
        'prev_custom':        [],
        'is_clone':           False,
    })


# ================================================================
# CLONE COA
# — FIX 1: reads custom_is_heading (not custom_field_is_heading)
# — FIX 2: saves created_by
# — FIX 3: passes is_heading in prev_custom
# ================================================================
@login_required
def clone_coa(request, coa_id):
    original = get_object_or_404(COA, id=coa_id)

    parameters = TestParameter.objects.filter(
        category=original.category
    ).select_related('group').order_by('group__order', 'order')

    grouped_parameters = []
    for group_key, group_items in groupby(parameters, key=lambda p: p.group):
        grouped_parameters.append({'group': group_key, 'params': list(group_items)})

    prev_results = {
        r.parameter_id: {
            'result':   r.result,
            'standard': r.standard_override or r.parameter.specification,
        }
        for r in original.results.all().select_related('parameter')
    }

    # FIX 3: include is_heading so clone shows headings correctly
    prev_custom = list(original.custom_fields.values(
        'field_name', 'specification', 'result', 'is_heading'
    ))

    if request.method == 'POST':
        form = COAForm(request.POST)
        if 'save_coa' in request.POST and form.is_valid():
            # FIX 2: save created_by
            coa = form.save(commit=False)
            coa.created_by = request.user
            coa.save()

            category_id = request.POST.get('category')
            parameters  = TestParameter.objects.filter(category_id=category_id)

            for param in parameters:
                value             = request.POST.get(f'param_{param.id}', '').strip()
                standard_override = request.POST.get(f'standard_{param.id}', '').strip()
                if value:
                    COAResult.objects.create(
                        coa=coa, parameter=param, result=value,
                        standard_override=standard_override if standard_override != param.specification else ''
                    )

            # FIX 1: read custom_is_heading
            names    = request.POST.getlist('custom_field_name')
            specs    = request.POST.getlist('custom_field_spec')
            results  = request.POST.getlist('custom_field_result')
            headings = request.POST.getlist('custom_is_heading')
            for i, name in enumerate(names):
                name = name.strip()
                if name:
                    is_heading = (headings[i] == '1') if i < len(headings) else False
                    COACustomField.objects.create(
                        coa=coa, field_name=name,
                        specification=specs[i]   if i < len(specs)   else '',
                        result=results[i]         if i < len(results) else '',
                        order=i,
                        is_heading=is_heading,
                    )
            return redirect('coa_detail', coa_id=coa.id)
    else:
        form = COAForm(initial={
            'product_name':   original.product_name,
            'category':       original.category,
            'botanical_name': original.botanical_name,
            'plant_part':     original.plant_part,
            'customer_name':  original.customer_name,
        })

    return render(request, 'coa/create_coa.html', {
        'form':               form,
        'grouped_parameters': grouped_parameters,
        'posted_data':        {},
        'prev_results':       prev_results,
        'prev_custom':        prev_custom,
        'is_clone':           True,
        'original':           original,
    })


# ================================================================
# COA DETAIL
# ================================================================
@login_required
def coa_detail(request, coa_id):
    coa           = get_object_or_404(COA, id=coa_id)
    results       = coa.results.all().select_related(
        'parameter', 'parameter__group'
    ).order_by('parameter__group__order', 'parameter__order')
    custom_fields = coa.custom_fields.all()
    return render(request, 'coa/coa_detail.html', {
        'coa':           coa,
        'results':       results,
        'custom_fields': custom_fields,
    })


# ================================================================
# DOWNLOAD COA PDF
# ================================================================
@login_required
def download_coa_pdf(request, coa_id):
    coa     = get_object_or_404(COA, id=coa_id)
    results = coa.results.all().select_related(
        'parameter', 'parameter__group'
    ).order_by('parameter__group__order', 'parameter__order')

    # Group results — no serial numbers needed
    grouped_results = []
    for group_key, group_items in groupby(results, key=lambda r: r.parameter.group):
        grouped_results.append({'group': group_key, 'items': list(group_items)})

    # Custom fields — just fetch, no counter logic needed
    custom_fields = list(coa.custom_fields.all())

    STATIC = settings.STATIC_URL
    def s(f): return f"{STATIC}images/{f}"

    template = get_template('coa/coa_pdf.html')
    html = template.render({
        'coa':             coa,
        'grouped_results': grouped_results,
        'custom_fields':   custom_fields,
        'logo_url':        s('logo.png'),
        'halal_badge_url': s('halal_badge.png'),
        'iso_badge_url':   s('iso_badge.png'),
        'gmp_badge_url':   s('gmp_badge.png'),
        'stamp_url':       s('stamp.png'),
    })

    response = HttpResponse(content_type='application/pdf')
    safe_batch    = coa.batch_no.replace('/', '-')
    safe_product  = coa.product_name.replace(' ', '_').replace('/', '-')
    safe_customer = (coa.customer_name or 'General').replace(' ', '_').replace('/', '-')
    response['Content-Disposition'] = f'attachment; filename="COA_{safe_product}_{safe_customer}_{safe_batch}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response, link_callback=link_callback)
    if pisa_status.err:
        return HttpResponse(f'<h2>PDF Error: {pisa_status.err}</h2>', status=500)
    return response


# ================================================================
# GENERATE LABEL
# ================================================================
@login_required
def generate_label(request, coa_id):
    coa = get_object_or_404(COA, id=coa_id)
    try:
        label = coa.label
    except Exception:
        label = None

    if request.method == 'POST':
        data = {
            'invoice_no':   request.POST.get('invoice_no', '').strip(),
            'gross_weight': request.POST.get('gross_weight', '').strip(),
            'tare_weight':  request.POST.get('tare_weight', '').strip(),
            'net_weight':   request.POST.get('net_weight', '').strip(),
        }
        if label:
            for k, v in data.items():
                setattr(label, k, v)
            label.save()
        else:
            label = COALabel.objects.create(coa=coa, **data)
        return redirect('download_label_pdf', coa_id=coa.id)

    return render(request, 'coa/generate_label.html', {'coa': coa, 'label': label})


# ================================================================
# DOWNLOAD LABEL PDF
# ================================================================
@login_required
def download_label_pdf(request, coa_id):
    coa = get_object_or_404(COA, id=coa_id)
    try:
        label = coa.label
    except Exception:
        return redirect('generate_label', coa_id=coa_id)

    STATIC = settings.STATIC_URL
    def s(f): return f"{STATIC}images/{f}"

    template = get_template('coa/label_pdf.html')
    html = template.render({
        'coa':             coa,
        'label':           label,
        'logo_url':        s('logo.png'),
        'halal_badge_url': s('halal_badge.png'),
        'iso_badge_url':   s('iso_badge.png'),
        'gmp_badge_url':   s('gmp_badge.png'),
    })

    response = HttpResponse(content_type='application/pdf')
    safe_batch   = coa.batch_no.replace('/', '-')
    safe_product = coa.product_name.replace(' ', '_').replace('/', '-')
    response['Content-Disposition'] = f'attachment; filename="LABEL_{safe_batch}_{safe_product}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response, link_callback=link_callback)
    if pisa_status.err:
        return HttpResponse(f'<h2>Label PDF Error: {pisa_status.err}</h2>', status=500)
    return response


# ================================================================
# EDIT COA
# — already correct: reads custom_is_heading
# ================================================================
@login_required
def edit_coa(request, coa_id):
    coa = get_object_or_404(COA, id=coa_id)

    existing_results = {
        r.parameter_id: {
            'result':   r.result or '',
            'standard': r.standard_override or r.parameter.specification or '',
            'obj':      r,
        }
        for r in coa.results.all().select_related('parameter')
    }

    parameters = TestParameter.objects.filter(
        category=coa.category
    ).select_related('group').order_by('group__order', 'order')

    grouped_parameters = []
    for group_key, group_items in groupby(parameters, key=lambda p: p.group):
        grouped_parameters.append({'group': group_key, 'params': list(group_items)})

    custom_fields = list(coa.custom_fields.all())

    if request.method == 'POST':
        coa.product_name   = request.POST.get('product_name', coa.product_name).strip()
        coa.botanical_name = request.POST.get('botanical_name', '').strip()
        coa.plant_part     = request.POST.get('plant_part', '').strip()
        coa.customer_name  = request.POST.get('customer_name', '').strip()

        mfg_date_str = request.POST.get('manufacturing_date', '')
        if mfg_date_str:
            from datetime import datetime
            try:
                coa.manufacturing_date = datetime.strptime(mfg_date_str, '%Y-%m-%d').date()
                coa.expiry_date = None
            except ValueError:
                pass
        coa.save()

        for param in TestParameter.objects.filter(category=coa.category):
            value    = request.POST.get(f'param_{param.id}', '').strip()
            standard = request.POST.get(f'standard_{param.id}', '').strip()

            if param.id in existing_results:
                r = existing_results[param.id]['obj']
                r.result            = value
                r.standard_override = standard if standard != param.specification else ''
                r.save()
            elif value:
                COAResult.objects.create(
                    coa=coa, parameter=param, result=value,
                    standard_override=standard if standard != param.specification else ''
                )

        coa.custom_fields.all().delete()
        names    = request.POST.getlist('custom_field_name')
        specs    = request.POST.getlist('custom_field_spec')
        results  = request.POST.getlist('custom_field_result')
        headings = request.POST.getlist('custom_is_heading')
        for i, name in enumerate(names):
            name = name.strip()
            if name:
                is_heading = (headings[i] == '1') if i < len(headings) else False
                COACustomField.objects.create(
                    coa=coa, field_name=name,
                    specification=specs[i].strip()   if i < len(specs)   else '',
                    result=results[i].strip()         if i < len(results) else '',
                    order=i,
                    is_heading=is_heading,
                )

        return redirect('coa_detail', coa_id=coa.id)

    return render(request, 'coa/edit_coa.html', {
        'coa':                coa,
        'grouped_parameters': grouped_parameters,
        'existing_results':   existing_results,
        'custom_fields':      custom_fields,
    })


# ================================================================
# AJAX — Out of range check
# ================================================================
@login_required
def check_result(request):
    import re
    standard = request.POST.get('standard', '').strip()
    result   = request.POST.get('result', '').strip()

    if not standard or not result:
        return JsonResponse({'status': 'unknown'})

    result_nums = re.findall(r'[-+]?\d*\.?\d+', result)
    if not result_nums:
        return JsonResponse({'status': 'unknown', 'message': 'Non-numeric result'})

    result_val  = float(result_nums[0])
    range_match = re.findall(r'[-+]?\d*\.?\d+', standard)

    if len(range_match) >= 2:
        lo, hi = float(range_match[0]), float(range_match[-1])
        if lo > hi:
            lo, hi = hi, lo
        if lo <= result_val <= hi:
            return JsonResponse({'status': 'pass', 'message': f'Within range {lo}–{hi}'})
        else:
            return JsonResponse({'status': 'fail',
                'message': f'Out of range! Expected {lo}–{hi}, got {result_val}'})

    max_match = re.search(r'(?:max|nmt|not more than|≤|<)\s*([\d.]+)', standard, re.I)
    if max_match:
        limit = float(max_match.group(1))
        if result_val <= limit:
            return JsonResponse({'status': 'pass'})
        return JsonResponse({'status': 'fail', 'message': f'Exceeds max {limit}!'})

    min_match = re.search(r'(?:min|nlt|not less than|≥|>)\s*([\d.]+)', standard, re.I)
    if min_match:
        limit = float(min_match.group(1))
        if result_val >= limit:
            return JsonResponse({'status': 'pass'})
        return JsonResponse({'status': 'fail', 'message': f'Below minimum {limit}!'})

    return JsonResponse({'status': 'unknown', 'message': 'Could not parse standard'})


# ================================================================
# AJAX — Product standards
# ================================================================
@login_required
def product_standards(request):
    name = request.GET.get('name', '').strip()
    if not name:
        return JsonResponse({'standards': {}})
    from .models import ProductStandard
    try:
        ps = ProductStandard.objects.get(product_name__iexact=name)
        return JsonResponse({'standards': ps.get_standards(), 'found': True})
    except ProductStandard.DoesNotExist:
        qs = ProductStandard.objects.filter(product_name__icontains=name).first()
        if qs:
            return JsonResponse({'standards': qs.get_standards(), 'found': True, 'matched': qs.product_name})
        return JsonResponse({'standards': {}, 'found': False})


# ================================================================
# AJAX — Standards search autocomplete
# ================================================================
@login_required
def standards_search(request):
    from .models import ProductStandard
    q     = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    if not q:
        return JsonResponse({'results': []})
    results = ProductStandard.objects.filter(
        product_name__icontains=q
    ).values_list('product_name', flat=True)[:limit]
    return JsonResponse({'results': list(results)})


# ================================================================
# OLD COA SEARCH
# ================================================================
@login_required
def old_coa_search(request):
    from .models import OldCOA
    query    = request.GET.get('q', '').strip()
    customer = request.GET.get('customer', '').strip()
    item     = request.GET.get('item', '').strip()
    results  = []

    qs = OldCOA.objects.all()
    if query:
        qs = qs.filter(
            Q(file_name__icontains=query) |
            Q(product__icontains=query)   |
            Q(customer__icontains=query)  |
            Q(batch__icontains=query)
        )
    if customer:
        qs = qs.filter(customer__icontains=customer)
    if item:
        qs = qs.filter(product__icontains=item)

    if query or customer or item:
        results = qs.order_by('file_name')[:100]

    return render(request, 'coa/old_coa_search.html', {
        'query':    query,
        'customer': customer,
        'item':     item,
        'results':  results,
    })


# ================================================================
# OLD COA DETAIL
# ================================================================
@login_required
def old_coa_detail(request, old_id):
    from .models import OldCOA
    old_coa = get_object_or_404(OldCOA, id=old_id)
    return render(request, 'coa/old_coa_detail.html', {
        'old_coa': old_coa,
        'fields':  old_coa.get_fields(),
    })


# ================================================================
# CLONE FROM OLD COA
# — FIX: reads custom_is_heading (not custom_field_is_heading)
# — FIX: saves created_by
# ================================================================
@login_required
def clone_from_old(request, old_id):
    from .models import OldCOA
    old_coa    = get_object_or_404(OldCOA, id=old_id)
    old_fields = old_coa.get_fields()
    categories = Category.objects.all().order_by('name')

    if request.method == 'POST' and 'save_coa' in request.POST:
        form = COAForm(request.POST)
        if form.is_valid():
            # FIX: save created_by
            coa = form.save(commit=False)
            coa.created_by = request.user
            coa.save()

            category_id = request.POST.get('category')
            if category_id:
                for param in TestParameter.objects.filter(category_id=category_id):
                    value    = request.POST.get(f'param_{param.id}', '').strip()
                    standard = request.POST.get(f'standard_{param.id}', '').strip()
                    if value:
                        COAResult.objects.create(
                            coa=coa, parameter=param, result=value,
                            standard_override=standard if standard != param.specification else ''
                        )

            # FIX: read custom_is_heading
            names    = request.POST.getlist('custom_field_name')
            specs    = request.POST.getlist('custom_field_spec')
            results  = request.POST.getlist('custom_field_result')
            headings = request.POST.getlist('custom_is_heading')
            for i, name in enumerate(names):
                name = name.strip()
                if name:
                    is_heading = (headings[i] == '1') if i < len(headings) else False
                    COACustomField.objects.create(
                        coa=coa, field_name=name,
                        specification=specs[i].strip()   if i < len(specs)   else '',
                        result=results[i].strip()         if i < len(results) else '',
                        order=i,
                        is_heading=is_heading,
                    )
            return redirect('coa_detail', coa_id=coa.id)

    else:
        form = COAForm(initial={
            'product_name':   old_coa.product,
            'botanical_name': old_coa.botanical,
            'plant_part':     old_coa.part_used,
            'customer_name':  old_coa.customer,
        })

    grouped_parameters = []
    prev_results       = {}
    selected_cat_id    = request.POST.get('category') if request.method == 'POST' else ''

    if 'load_fields' in request.POST:
        selected_cat_id = request.POST.get('category')

    if selected_cat_id:
        parameters = TestParameter.objects.filter(
            category_id=selected_cat_id
        ).select_related('group').order_by('group__order', 'order')
        for param in parameters:
            for old_key, old_val in old_fields.items():
                if (param.name.lower().strip() == old_key.lower().strip() or
                    param.name.lower() in old_key.lower() or
                    old_key.lower() in param.name.lower()):
                    prev_results[param.id] = {'result': '', 'standard': old_val}
                    break
        for group_key, group_items in groupby(parameters, key=lambda p: p.group):
            grouped_parameters.append({'group': group_key, 'params': list(group_items)})

    return render(request, 'coa/clone_from_old.html', {
        'form':               form,
        'old_coa':            old_coa,
        'old_fields':         old_fields,
        'categories':         categories,
        'grouped_parameters': grouped_parameters,
        'prev_results':       prev_results,
        'selected_cat_id':    selected_cat_id or '',
    })


# ================================================================
# USER MANAGEMENT — Admin only
# ================================================================

def admin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            if request.user.is_superuser or request.user.profile.role == 'admin':
                return view_func(request, *args, **kwargs)
        except Exception:
            pass
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(
            "<h2>Access Denied</h2><p>Only admin users can manage accounts.</p>"
            "<a href='/coa/'>← Back</a>"
        )
    return wrapper


@admin_required
def user_list(request):
    users = User.objects.select_related('profile').order_by('username')
    return render(request, 'coa/user_list.html', {'users': users})


@admin_required
def user_create(request):
    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        password   = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        role       = request.POST.get('role', 'analyst')

        if not username or not password:
            messages.error(request, 'Username and password are required.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
        else:
            user = User.objects.create_user(
                username=username, password=password,
                first_name=first_name, last_name=last_name, email=email,
            )
            UserProfile.objects.create(user=user, role=role, created_by=request.user)
            messages.success(request, f'User "{username}" created successfully.')
            return redirect('user_list')

    return render(request, 'coa/user_create.html', {
        'role_choices': UserProfile.ROLE_CHOICES,
    })


@admin_required
def user_edit(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    try:
        profile = target_user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=target_user, role='analyst')

    if request.method == 'POST':
        target_user.first_name = request.POST.get('first_name', '').strip()
        target_user.last_name  = request.POST.get('last_name', '').strip()
        target_user.email      = request.POST.get('email', '').strip()
        new_password = request.POST.get('password', '').strip()
        if new_password:
            target_user.set_password(new_password)
        target_user.save()

        profile.role = request.POST.get('role', profile.role)
        profile.save()
        messages.success(request, f'User "{target_user.username}" updated.')
        return redirect('user_list')

    return render(request, 'coa/user_edit.html', {
        'target_user':  target_user,
        'profile':      profile,
        'role_choices': UserProfile.ROLE_CHOICES,
    })


@admin_required
def user_delete(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    if request.method == 'POST':
        username = target_user.username
        target_user.delete()
        messages.success(request, f'User "{username}" deleted.')
        return redirect('user_list')
    return render(request, 'coa/user_confirm_delete.html', {'target_user': target_user})