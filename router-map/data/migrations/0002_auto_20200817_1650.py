# Generated by Django 2.2 on 2020-08-17 14:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('data', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='chassis_id',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='device',
            name='connection_type',
            field=models.CharField(choices=[('snmp', 'snmp'), ('netconf', 'netconf')], default='snmp', max_length=20),
        ),
        migrations.RenameField(
            model_name='device',
            old_name='snmp_connection',
            new_name='connection',
        ),
    ]
