from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coa', '0011_coa_created_at_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='coaresult',
            name='position',
            field=models.IntegerField(default=0, help_text="Row order on the printed COA, shared with COACustomField.order so custom fields/headings can be interleaved with parameters."),
        ),
        migrations.AlterModelOptions(
            name='coaresult',
            options={'ordering': ['position', 'id']},
        ),
    ]
