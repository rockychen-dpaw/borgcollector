# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import re
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tablemanager', '0021_auto_20160216_1431'),
    ]

    operations = [
        migrations.AlterField(
            model_name='publishstyle',
            name='name',
            field=models.SlugField(help_text='Name of Publish', max_length=255, validators=[django.core.validators.RegexValidator(re.compile('^[a-z0-9_]+$'), 'Slug can only contain lowercase letters, numbers and underscores', 'invalid')]),
            preserve_default=True,
        ),
    ]
