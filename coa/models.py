from django.db import models
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

# 1-year expiry categories
ONE_YEAR_EXPIRY_KEYWORDS = ['water soluble', 'water-soluble', 'hydrosol']


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

    def is_one_year_expiry(self):
        """Returns True if this category should have 1-year expiry."""
        name_lower = self.name.lower().strip()
        return any(kw in name_lower for kw in ONE_YEAR_EXPIRY_KEYWORDS)


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
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Audit: who created this COA (records only — not on PDF) ──
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='coas_created',
                                    help_text='User who created this COA. Not printed on COA.')

    def save(self, *args, **kwargs):
        # Auto Batch Number
        if not self.batch_no:
            cat_code = self.category.get_code()
            date_str = date.today().strftime("%y%m%d")
            prefix   = f"HI/{cat_code}/{date_str}"
            count    = COA.objects.filter(batch_no__startswith=prefix).count() + 1
            self.batch_no = f"{prefix}{count:02d}"

        # Auto Expiry:
        # Water Soluble / Hydrosol → 1 year exactly
        # Everything else → 2 years minus 1 month
        if self.manufacturing_date and not self.expiry_date:
            if self.category.is_one_year_expiry():
                self.expiry_date = self.manufacturing_date + relativedelta(years=1)
            else:
                self.expiry_date = self.manufacturing_date + relativedelta(years=2, months=-1)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name} | {self.batch_no}"


class COAResult(models.Model):
    coa               = models.ForeignKey(COA, on_delete=models.CASCADE, related_name="results")
    parameter         = models.ForeignKey(TestParameter, on_delete=models.CASCADE)
    result            = models.CharField(max_length=300, blank=True, null=True)
    standard_override = models.CharField(max_length=300, blank=True, null=True)

    def __str__(self):
        return f"{self.coa.batch_no} | {self.parameter.name}"


class COACustomField(models.Model):
    coa           = models.ForeignKey(COA, on_delete=models.CASCADE, related_name="custom_fields")
    field_name    = models.CharField(max_length=200)
    specification = models.CharField(max_length=300, blank=True, null=True)
    result        = models.CharField(max_length=300, blank=True, null=True)
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