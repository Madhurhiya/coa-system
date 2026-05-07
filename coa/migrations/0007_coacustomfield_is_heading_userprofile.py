from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coa', '0006_oldcoa_productstandard'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add is_heading field to COACustomField
        migrations.AddField(
            model_name='coacustomfield',
            name='is_heading',
            field=models.BooleanField(
                default=False,
                help_text='If True, renders as a bold section heading row in the COA table',
            ),
        ),
        # Create UserProfile model
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('admin', 'Admin'), ('analyst', 'Analyst'), ('viewer', 'Viewer')],
                    default='analyst',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_profiles',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
