from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_default_categories'),
    ]

    operations = [
        # Its rows were copied into Transaction by 0003.
        migrations.DeleteModel(name='Expense'),
    ]
