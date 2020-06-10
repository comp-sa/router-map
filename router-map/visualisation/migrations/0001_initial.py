# Generated by Django 2.2 on 2020-06-09 10:16

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Visualisation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=127)),
                ('display_link_descriptions', models.BooleanField(default=True)),
                ('links_default_width', models.PositiveIntegerField(default=3, validators=[
                    django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(15)])),
                ('highlighted_links_width', models.PositiveIntegerField(blank=True, default=None, null=True,
                                                                        validators=[
                                                                            django.core.validators.MinValueValidator(1),
                                                                            django.core.validators.MaxValueValidator(
                                                                                15)])),
                ('highlighted_links_range_min', models.PositiveIntegerField(blank=True, default=None,
                                                                            help_text='links with higher or equal speed will be highlighted',
                                                                            null=True)),
                ('highlighted_links_range_max', models.PositiveIntegerField(blank=True, default=None,
                                                                            help_text='links with lower or equal speed will be highlighted',
                                                                            null=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                             related_name='children', to='visualisation.Visualisation')),

            ],
        ),
    ]
