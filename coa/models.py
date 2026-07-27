from django.db import models, transaction, IntegrityError
from datetime import date
from dateutil.relativedelta import relativedelta


STATUS_CHOICES = [
    ('DRAFT',     'Draft'),
    ('SUBMITTED', 'Submitted'),
    ('APPROVED',  'Approved'),
]

CATEGORY_CODES = {
    'carrier oil':           'FO',
    'fixed oil':             'FO',
    'essential oil':         'EO',
    'oil soluble extract':   'OS',
    'oil soluble':           'OS',
    'fragrance':             'FR',
    'water soluble extract': 'WS',
    'water soluble':         'WS',
    'hydrosol':              'HS',
    'flavour':               'FL',
    'flavor':                'FL',
    'crystal':               'CR',
    'dry extract':           'DE',
    'soft extract':          'SE',
    'powder':                'PW',
    'raw herb':              'RH',
    'raw herbs':             'RH',
    'ayurvedic oil':         'AO',
    'aroma chemicals':       'AC',
    'other':                 'OT',
}


# ── Customer master ──
class Customer(models.Model):
    name = models.CharField(max_length=300, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ── Item master ──
class ItemMaster(models.Model):
    item_category  = models.CharField(max_length=500, blank=True)
    item_name      = models.CharField(max_length=300, unique=True)
    botanical_name = models.CharField(max_length=500, blank=True)
    plant_part     = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['item_name']

    def __str__(self):
        return self.item_name


class Category(models.Model):
    name = models.CharField(max_length=500)
    code = models.CharField(max_length=10, blank=True,
        help_text="Short code used in Batch No. e.g. FO, EO, OS")

    def __str__(self):
        return self.name

    def get_code(self):
        if self.code:
            return self.code.upper()
        name_lower = self.name.lower().strip()
        for key, code in CATEGORY_CODES.items():
            if key in name_lower:
                return code
        return 'XX'

    def is_dry_extract(self):
        """Returns True if this is a Dry Extract category."""
        return 'dry extract' in self.name.lower() or 'dry-extract' in self.name.lower()

    def is_one_year_expiry(self):
        """Returns True if this category should have 1-year expiry."""
        name_lower = self.name.lower().strip()
        return any(kw in name_lower for kw in ['water soluble', 'water-soluble', 'hydrosol'])


class TestGroup(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="groups")
    name     = models.CharField(max_length=200)
    order    = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.category.name} → {self.name}"


class TestParameter(models.Model):
    category      = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="parameters")
    group         = models.ForeignKey(TestGroup, on_delete=models.CASCADE,
                                       null=True, blank=True, related_name="parameters")
    name          = models.CharField(max_length=200)
    specification = models.CharField(max_length=300, blank=True, null=True)
    order         = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.category.name} | {self.name}"


class COA(models.Model):

    def ordered_rows(self, include_untested_params=False):
        """Returns a single ordered list of dicts describing every row that
        should appear on this COA, in the exact order they should print —
        test-parameter results, custom fields, and section headings are all
        interleaved by their saved position, instead of parameters always
        being printed first and custom fields/headings always last.

        Each item is one of:
          {'kind': 'group',  'name': <TestGroup name>}
          {'kind': 'param',  'parameter': <TestParameter>, 'result': <COAResult or None>}
          {'kind': 'custom' or 'heading', 'cf': <COACustomField>}

        include_untested_params=True also appends any TestParameter in this
        COA's category that has no saved result yet (used by the edit form
        so every possible parameter is still available to fill in).
        """
        results = list(
            self.results.select_related('parameter', 'parameter__group').order_by('position', 'id')
        )
        customs = list(self.custom_fields.all().order_by('order', 'id'))

        rows = []
        seen_groups = set()
        max_pos = -1
        seen_param_ids = set()

        for r in results:
            grp = r.parameter.group
            if grp and grp.id not in seen_groups:
                rows.append({'kind': 'group', 'position': r.position, 'name': grp.name})
                seen_groups.add(grp.id)
            rows.append({'kind': 'param', 'position': r.position, 'parameter': r.parameter, 'result': r})
            seen_param_ids.add(r.parameter_id)
            max_pos = max(max_pos, r.position)

        for cf in customs:
            rows.append({'kind': 'heading' if cf.is_heading else 'custom', 'position': cf.order, 'cf': cf})
            max_pos = max(max_pos, cf.order)

        if include_untested_params:
            remaining = (TestParameter.objects.filter(category_id=self.category_id)
                         .exclude(id__in=seen_param_ids)
                         .select_related('group').order_by('order'))
            next_pos = max_pos + 1
            for p in remaining:
                grp = p.group
                if grp and grp.id not in seen_groups:
                    rows.append({'kind': 'group', 'position': next_pos, 'name': grp.name})
                    seen_groups.add(grp.id)
                    next_pos += 1
                rows.append({'kind': 'param', 'position': next_pos, 'parameter': p, 'result': None})
                next_pos += 1

        rows.sort(key=lambda x: x['position'])
        return rows

    # ── Product Info ──
    product_name   = models.CharField(max_length=200)
    category       = models.ForeignKey(Category, on_delete=models.CASCADE)
    botanical_name = models.CharField(max_length=500, blank=True, null=True)
    plant_part     = models.CharField(max_length=300, blank=True, null=True)

    # ── Customer (for search/records only — NOT printed on COA) ──
    customer_name  = models.CharField(max_length=300, blank=True, null=True,
                                       help_text="For records only. Not printed on COA.")

    # ── Batch & Dates ──
    batch_no           = models.CharField(max_length=50, unique=True, blank=True)
    manufacturing_date = models.DateField(default=date.today)
    expiry_date        = models.DateField(blank=True, null=True)

    # ── Workflow ──
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # ── Audit: who created this COA (records only — not on PDF) ──
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='coas_created',
                                    help_text='User who created this COA. Not printed on COA.')

    def save(self, *args, **kwargs):
        # Auto Expiry:
        # Water Soluble / Hydrosol → 1 year
        # Dry Extract              → 3 years
        # Everything else          → 2 years minus 1 month
        if self.manufacturing_date and not self.expiry_date:
            if self.category.is_one_year_expiry():
                self.expiry_date = self.manufacturing_date + relativedelta(years=1)
            elif self.category.is_dry_extract():
                self.expiry_date = self.manufacturing_date + relativedelta(years=3)
            else:
                self.expiry_date = self.manufacturing_date + relativedelta(years=2, months=-1)

        if self.batch_no:
            # Batch number already set (edit, or explicitly provided) — save normally.
            super().save(*args, **kwargs)
            return

        # Auto Batch Number — generated and saved inside a transaction, and
        # retried a few times if two COAs are saved at nearly the same moment
        # and would otherwise collide on the same batch number.
        cat_code = self.category.get_code()
        date_str = date.today().strftime("%y%m%d")
        prefix   = f"HI/{cat_code}/{date_str}"

        last_error = None
        for attempt in range(5):
            with transaction.atomic():
                # Lock the Category row itself (it always exists, even when
                # this is the first COA of the day for it) so two requests
                # generating a batch number for the same category+day can't
                # both read the same count and collide.
                Category.objects.select_for_update().get(pk=self.category_id)
                count = COA.objects.filter(batch_no__startswith=prefix).count()
                self.batch_no = f"{prefix}{count + 1 + attempt:02d}"
                try:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    return
                except IntegrityError as e:
                    last_error = e
                    self.batch_no = ''  # reset and try the next number
                    continue
        # If we somehow still collided 5 times in a row, surface the error.
        raise last_error

    def __str__(self):
        return f"{self.product_name} | {self.batch_no}"


class COAResult(models.Model):
    coa               = models.ForeignKey(COA, on_delete=models.CASCADE, related_name="results")
    parameter         = models.ForeignKey(TestParameter, on_delete=models.CASCADE)
    result            = models.CharField(max_length=300, blank=True, null=True)
    reference         = models.CharField(max_length=300, blank=True, null=True,
                                          help_text="Reference column — shown only for Dry Extract COAs")
    standard_override = models.CharField(max_length=300, blank=True, null=True)
    position          = models.IntegerField(default=0,
                                             help_text="Row order on the printed COA, shared with COACustomField.order "
                                                        "so custom fields/headings can be interleaved with parameters.")

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f"{self.coa.batch_no} | {self.parameter.name}"


class COACustomField(models.Model):
    coa           = models.ForeignKey(COA, on_delete=models.CASCADE, related_name="custom_fields")
    field_name    = models.CharField(max_length=200)
    specification = models.CharField(max_length=300, blank=True, null=True)
    result        = models.CharField(max_length=300, blank=True, null=True)
    reference     = models.CharField(max_length=300, blank=True, null=True,
                                      help_text="Reference column — shown only for Dry Extract COAs")
    order         = models.IntegerField(default=0)
    is_heading    = models.BooleanField(default=False,
                        help_text="If True, renders as a bold section heading row in the COA table")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.coa.batch_no} | {'[HEADING] ' if self.is_heading else ''}Custom: {self.field_name}"


class COALabel(models.Model):
    coa          = models.OneToOneField(COA, on_delete=models.CASCADE, related_name="label")
    invoice_no   = models.CharField(max_length=500, blank=True, null=True)
    gross_weight = models.CharField(max_length=50, blank=True, null=True)
    tare_weight  = models.CharField(max_length=50, blank=True, null=True)
    net_weight   = models.CharField(max_length=50, blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Label for {self.coa.batch_no}"


class ProductStandard(models.Model):
    product_name = models.CharField(max_length=300, unique=True, db_index=True)
    standards    = models.TextField(help_text="JSON: {field_name: standard_value, ...}")
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product_name']

    def get_standards(self):
        import json
        try:
            return json.loads(self.standards)
        except Exception:
            return {}

    def __str__(self):
        return self.product_name


class OldCOA(models.Model):
    file_name = models.CharField(max_length=500, db_index=True,
                                  help_text="Original file name — used for searching")
    customer  = models.CharField(max_length=300, blank=True, db_index=True)
    product   = models.CharField(max_length=300, blank=True, db_index=True)
    batch     = models.CharField(max_length=500, blank=True)
    mfg_date  = models.CharField(max_length=50,  blank=True)
    botanical = models.CharField(max_length=500, blank=True)
    part_used = models.CharField(max_length=300, blank=True)
    fields    = models.TextField(help_text="JSON: {parameter_name: standard_value, ...}")

    class Meta:
        ordering = ['file_name']
        verbose_name        = 'Old COA (Archive)'
        verbose_name_plural = 'Old COAs (Archive)'

    def get_fields(self):
        import json
        try:
            return json.loads(self.fields)
        except Exception:
            return {}

    def __str__(self):
        return self.file_name or self.product


# ── User Profile ──
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin',    'Admin'),
        ('analyst',  'Analyst'),
        ('viewer',   'Viewer'),
    ]
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='analyst')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='created_profiles')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"