from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coa', '0010_merge_20260525_1605'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coa',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
