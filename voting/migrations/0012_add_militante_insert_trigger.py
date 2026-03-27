from django.db import migrations


TRIGGER_BLOCK_INSERT_UNLESS_AUTHORIZED = """
CREATE TRIGGER trg_militante_block_insert
BEFORE INSERT ON voting_militante
FOR EACH ROW
BEGIN
    IF COALESCE(@allow_militante_insert, 0) <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Los militantes no pueden ser agregados por SQL: INSERT no permitido.';
    END IF;
END
"""

DROP_TRIGGER_INSERT = "DROP TRIGGER IF EXISTS trg_militante_block_insert"


def _is_mysql(schema_editor):
    return schema_editor.connection.vendor == 'mysql'


def add_insert_trigger(apps, schema_editor):
    if not _is_mysql(schema_editor):
        return
    schema_editor.execute(DROP_TRIGGER_INSERT)
    schema_editor.execute(TRIGGER_BLOCK_INSERT_UNLESS_AUTHORIZED)


def remove_insert_trigger(apps, schema_editor):
    if not _is_mysql(schema_editor):
        return
    schema_editor.execute(DROP_TRIGGER_INSERT)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("voting", "0011_harden_votingrecord_update_trigger"),
    ]

    operations = [
        migrations.RunPython(add_insert_trigger, remove_insert_trigger),
    ]
