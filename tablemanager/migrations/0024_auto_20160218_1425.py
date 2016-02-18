# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tablemanager', '0023_publishstyle_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='publishstyle',
            name='description',
            field=models.CharField(max_length=512, null=True, blank=True),
            preserve_default=True,
        ),
    ]
