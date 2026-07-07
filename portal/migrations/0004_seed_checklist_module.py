from django.db import migrations

def create_checklist_module(apps, schema_editor):
    Module = apps.get_model('portal', 'Module')
    Module.objects.update_or_create(
        key='Checklist',
        defaults={
            'label': 'Checklist',
            'description': 'Manage department shift checklists, inspections, and actions',
            'icon': 'clipboard-list',
            'color_class': 'module-checklist',
            'redirect_url_template': '/delays/department/{dept_id}/?tab=checklist_summary',
            'is_active': True,
            'sort_order': 6,
        }
    )

def remove_checklist_module(apps, schema_editor):
    Module = apps.get_model('portal', 'Module')
    Module.objects.filter(key='Checklist').delete()

class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0003_portalnotification"),
    ]

    operations = [
        migrations.RunPython(create_checklist_module, remove_checklist_module),
    ]
