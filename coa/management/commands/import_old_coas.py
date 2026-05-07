# coa/management/commands/import_old_coas.py
# Imports all 7375 old COA records from COA_Standards_Data.xlsx
# Uses ONLY openpyxl — no pandas required
# Run: python manage.py import_old_coas

import os, json, openpyxl
from django.core.management.base import BaseCommand
from coa.models import OldCOA

# Skip these column indices — they are metadata/dates/batch nos
SKIP_COLS = {
    0, 6, 7, 8, 74, 75, 76, 77, 209, 210, 211, 212,
    404, 405, 415, 478, 479, 480, 481, 505, 539, 586,
    599, 600, 603, 655, 656, 657, 706, 713, 714, 749,
    755, 756, 757, 758, 787, 814, 815, 816, 817, 818,
    819, 820, 825, 858, 859, 908
}


def clean(val):
    if val is None: return ''
    s = str(val).strip()
    return '' if s in ['–', '-', 'None', 'nan', ''] else s


class Command(BaseCommand):
    help = 'Import old COA archive from COA_Standards_Data.xlsx'

    def add_arguments(self, parser):
        parser.add_argument('--file', default='COA_Standards_Data.xlsx')
        parser.add_argument('--clear', action='store_true',
                            help='Clear existing old COAs before importing')

    def handle(self, *args, **options):
        base      = os.path.dirname(os.path.abspath('manage.py'))
        file_path = os.path.join(base, options['file'])

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(
                f'❌ Cannot find: {file_path}\n'
                f'   Copy {options["file"]} to the same folder as manage.py'
            ))
            return

        if options['clear']:
            count = OldCOA.objects.count()
            OldCOA.objects.all().delete()
            self.stdout.write(f'🗑️  Cleared {count} existing records')

        self.stdout.write(f'📖 Reading {options["file"]}...')

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            ws = wb['COA Data']
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Could not open: {e}'))
            return

        headers = [
            clean(h) for h in
            next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        ]

        batch_size = 200
        to_create  = []
        created = skipped = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]: continue

            file_name = clean(row[1])
            customer  = clean(row[2])
            prod_raw  = clean(row[3])
            product   = clean(row[4]) or prod_raw
            batch     = clean(row[6])
            mfg_date  = clean(row[7])
            botanical = clean(row[5]) or clean(row[10])
            part_used = clean(row[9])

            if not file_name and not product:
                skipped += 1
                continue

            # Collect all standard fields
            fields = {}
            for i, val in enumerate(row):
                if i in SKIP_COLS or i < 11: continue
                v = clean(val)
                if not v or len(v) > 300: continue
                h = headers[i] if i < len(headers) else ''
                h = clean(h)
                if not h or len(h) > 150: continue
                fields[h] = v

            to_create.append(OldCOA(
                file_name = file_name,
                customer  = customer,
                product   = product,
                batch     = batch,
                mfg_date  = mfg_date,
                botanical = botanical,
                part_used = part_used,
                fields    = json.dumps(fields, ensure_ascii=False),
            ))
            created += 1

            # Bulk insert in batches
            if len(to_create) >= batch_size:
                OldCOA.objects.bulk_create(to_create, ignore_conflicts=True)
                to_create = []
                self.stdout.write(f'   Saved {created} records so far...')

        # Save remaining
        if to_create:
            OldCOA.objects.bulk_create(to_create, ignore_conflicts=True)

        wb.close()
        self.stdout.write(self.style.SUCCESS(
            f'✅ Done: {created} old COAs imported, {skipped} skipped'
        ))
        self.stdout.write(self.style.SUCCESS('🎉 Old COA archive ready!'))