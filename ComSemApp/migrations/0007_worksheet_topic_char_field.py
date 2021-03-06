# Generated by Django 2.0 on 2018-07-28 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ComSemApp', '0006_auto_20180728_1614'),
    ]

    def move_topic_table_to_charfield(apps, schema_editor):
        Worksheet = apps.get_model("ComSemApp", "Worksheet")
        worksheets = Worksheet.objects.all()
        for worksheet in worksheets:
            topic = worksheet.topic
            if topic:
                worksheet.topic_char_field = topic.topic
                worksheet.save()

    def reverse_func(apps, schema_editor):
        pass

    operations = [
        migrations.AddField(
            model_name='worksheet',
            name='topic_char_field',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.RunPython(move_topic_table_to_charfield, reverse_func),
    ]
