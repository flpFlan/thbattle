# Generated by Django 3.2.13 on 2022-06-04 06:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(help_text='标题', max_length=50, unique=True, verbose_name='标题')),
                ('description', models.CharField(help_text='描述', max_length=200, verbose_name='描述')),
                ('icon', models.ImageField(help_text='图标', upload_to='', verbose_name='图标')),
                ('icon2x', models.ImageField(help_text='图标@2x', upload_to='', verbose_name='图标@2x')),
            ],
            options={
                'verbose_name': '勋章定义',
                'verbose_name_plural': '勋章定义',
            },
        ),
        migrations.CreateModel(
            name='PlayerBadge',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('granted_at', models.DateTimeField(auto_now_add=True, help_text='获得日期', verbose_name='获得日期')),
                ('badge', models.ForeignKey(help_text='勋章', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='badge.badge')),
            ],
            options={
                'verbose_name': '玩家的勋章',
                'verbose_name_plural': '玩家的勋章',
            },
        ),
    ]
