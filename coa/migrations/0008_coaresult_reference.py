from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coa', '0007_coacustomfield_is_heading_userprofile'),
    ]

    operations = [
        # Add reference field to COAResult
        migrations.AddField(
            model_name='coaresult',
            name='reference',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=300,
                help_text='Reference column — shown only for Dry Extract COAs',
            ),
        ),
        # Add reference field to COACustomField
        migrations.AddField(
            model_name='coacustomfield',
            name='reference',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=300,
                help_text='Reference column — shown only for Dry Extract COAs',
            ),
        ),
    ]