# Auditoría de Seguridad — Integridad y Anonimato de Votos

Este documento describe los mecanismos técnicos que garantizan que **ningún actor** —incluidos los administradores del sistema pueden alterar los votos registrados.

Todos los puntos aquí descritos son **verificables directamente en el código fuente** de este repositorio.

---

## 1. Los votos son INMUTABLES a nivel de código

**Archivo:** [`voting/models.py`](voting/models.py)

El modelo `VotingRecord` (tabla `voting_votingrecord` en la base de datos) es el registro permanente de cada voto.

### 1.1 No se puede modificar un voto existente

```python
# voting/models.py — clase VotingRecord, método save()

def save(self, *args, **kwargs):
    # Bloquear cualquier actualización posterior a la creación inicial
    if self.pk and not kwargs.get('update_fields') == ['integrity_hash']:
        existing = VotingRecord.objects.filter(pk=self.pk).exists()
        if existing:
            raise PermissionError(
                "Los registros de votos son inmutables y no pueden ser modificados."
            )
```

Cualquier intento de llamar `.save()` sobre un registro existente **lanza `PermissionError`**, sin importar quién lo invoque (usuario, administrador, script, etc.).

### 1.2 No se puede eliminar un voto

```python
# voting/models.py — clase VotingRecord, método delete()

def delete(self, *args, **kwargs):
    raise PermissionError(
        "Los registros de votos son inmutables y no pueden ser eliminados."
    )
```

Llamar `.delete()` siempre lanza un error. El registro **nunca se borra** a través del ORM de Django.

---

## 2. Integridad criptográfica: HMAC + cadena de bloques

**Archivo:** [`voting/models.py`](voting/models.py)

Cada `VotingRecord` tiene dos campos de hash:

| Campo | Descripción |
|---|---|
| `integrity_hash` | HMAC-SHA256 del contenido del voto |
| `chain_hash` | HMAC que incluye el hash del **voto anterior** de esa votación |

### 2.1 ¿Qué cubre el HMAC?

```python
# voting/models.py — generate_hash()

message = f"{self.id_voting_id}:{self.id_subject_id}:{self.pk}:{prev_chain_hash}"
return hmac.new(
    settings.SECRET_KEY.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()
```

El hash cubre: `id_voting` + `id_subject` + `pk` + **hash del registro anterior**.

Esto significa que:
- Modificar **cualquier campo** invalida el hash → detectable con `verify_integrity()`
- Insertar o borrar **cualquier voto en medio de la cadena** invalida todos los hashes posteriores → detectable con `verify_chain()`

### 2.2 Verificación de la cadena completa

```python
# voting/models.py — verify_chain()

@staticmethod
def verify_chain(voting_id):
    records = list(VotingRecord.objects.filter(id_voting_id=voting_id).order_by('pk'))
    prev_hash = '0' * 64
    for record in records:
        expected = hmac.new(
            settings.SECRET_KEY.encode(),
            f"{record.id_voting_id}:{record.id_subject_id}:{record.pk}:{prev_hash}".encode(),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(record.integrity_hash, expected):
            return False, record.pk
        prev_hash = record.integrity_hash
    return True, None
```

Cualquier auditor puede ejecutar `VotingRecord.verify_chain(voting_id)` en una consola de Django para verificar que **toda la secuencia de votos** de una votación es íntegra.

---

## 3. El panel de administración no puede modificar votos

**Archivo:** [`voting/admin.py`](voting/admin.py)

Los dos modelos críticos `VotingRecord` y `Count` están registrados con la clase `ReadOnlyMixin`:

```python
# voting/admin.py

class ReadOnlyMixin(NoDeleteMixin, NoAddMixin):
    """Hace un modelo completamente de solo lectura en el admin"""
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(VotingRecord)
class VotingRecordAdmin(ReadOnlyMixin, admin.ModelAdmin):
    """Registros de votos - SOLO LECTURA. No se pueden crear, editar ni eliminar."""
    ...

@admin.register(Count)
class CountAdmin(ReadOnlyMixin, admin.ModelAdmin):
    """Conteos de votos - SOLO LECTURA. Los conteos se derivan de VotingRecords."""
    ...
```

Un administrador que ingrese al panel de Django:
- **No verá** botón de "Agregar"
- **No podrá** hacer clic para editar un registro
- **No verá** botón de "Eliminar"

---

## 4. El conteo real siempre proviene de VotingRecord (no de Count)

**Archivo:** [`voting/models.py`](voting/models.py)

La tabla `Count` es un **caché** del conteo, pero en **nunca es la fuente de verdad**. El conteo real siempre se obtiene contando directamente los `VotingRecord`:

```python
# voting/models.py — Subject.get_vote_count()

def get_vote_count(self):
    """Obtiene el total de votos para este subject (fuente de verdad: VotingRecords)"""
    return VotingRecord.objects.filter(id_subject=self).count()
```

```python
# voting/models.py — Count.get_verified_count()

def get_verified_count(self):
    """Obtiene el conteo real basado en VotingRecords (fuente de verdad)"""
    return VotingRecord.objects.filter(id_subject=self.id_subject).count()

def is_consistent(self):
    """Verifica que el contador coincide con los registros reales"""
    return self.number == self.get_verified_count()
```

Si `Count.number` difiere de `get_verified_count()`, `is_consistent()` retorna `False`, señalando una manipulación.

Además, en el panel de administración, la columna **"Íntegro"** muestra visualmente si el contador es consistente con los votos reales.

---

## 5. Los votos son ANÓNIMOS: no se vinculan al votante

**Archivo:** [`voting/models.py`](voting/models.py)

`VotingRecord` **no contiene ningún dato de identidad**:

```python
class VotingRecord(models.Model):
    id_voting = models.ForeignKey(Voting, ...)   # ¿en qué votación?
    id_subject = models.ForeignKey(Subject, ...)  # ¿por quién/qué se votó?
    integrity_hash = models.CharField(...)         # hash HMAC
    chain_hash = models.CharField(...)             # hash encadenado
    # ← NO hay: rut, nombre, correo, user_id, militante_id
```

La relación entre el votante y el voto funciona así:

```
Militante (votante) ──login──→ UserData.has_voted = True
                                       ↕
                              (sin enlace directo)
                                       ↕
                          VotingRecord (voto anónimo)
```

`UserData` solo registra `has_voted = True` (el RUT ya votó), pero **no almacena a qué `VotingRecord` corresponde ese voto**. Esta desvinculación es irreversible: **es imposible saber por qué opción votó un RUT específico**.

---

## 6. Tests automatizados de seguridad

**Archivo:** [`voting/tests.py`](voting/tests.py)

Se incluyen tests automatizados que verifican todo lo anterior:

| Test | Qué verifica |
|---|---|
| `VotingRecordImmutabilityTest` | `save()` y `delete()` lanzan `PermissionError` |
| `VotingRecordIntegrityTest` | HMAC falla si el registro es manipulado; `verify_chain()` detecta la rotura |
| `CountTableIntegrityTest` | `get_verified_count()` es independiente de `Count.number`; `is_consistent()` detecta manipulaciones |
| `VoteAnonymityTest` | `VotingRecord` no tiene campos de identidad; no hay enlace entre RUT y voto específico |
| `AdminReadOnlyTest` | El admin de Django no permite add/change/delete en `VotingRecord` ni `Count` |

Para ejecutar los tests:

```bash
python manage.py test voting.tests -v 2
```

Para validar **enforcement real de triggers SQL** (MySQL/MariaDB, fuera del frontend):

```bash
python manage.py test voting.tests.MySQLDirectSQLEnforcementTest -v 2
```

---

## 7. Protección activa a nivel de base de datos y frontend

Actualmente existen controles adicionales:

- **Trigger DB para `VotingRecord` (DELETE condicionado):**
  - `DELETE` está bloqueado por defecto.
  - Solo se permite cuando la app habilita explícitamente `@allow_votingrecord_delete = 1` en la sesión SQL durante una operación autorizada.

- **Trigger DB para `VotingRecord` (UPDATE condicionado):**
  - `UPDATE` está bloqueado por defecto.
  - Solo se permite para el sellado técnico inicial de `integrity_hash`/`chain_hash`, cuando la app habilita temporalmente `@allow_votingrecord_update = 1`.

- **Token de eliminación por sesión (12 horas):**
  - La eliminación de una votación desde dashboard exige un token de seguridad por sesión.
  - El token expira a las 12 horas.
  - Si el token está expirado, la sesión se cierra y se fuerza nuevo login.

- **Trigger DB para `Count` (solo `+1`):**
  - Solo se acepta `UPDATE` cuando `NEW.number = OLD.number + 1`.
  - Cualquier otro cambio en `number` se rechaza.

---

## Resumen

| Amenaza | ¿Está protegida? | Mecanismo |
|---|---|---|
| Admin modifica un voto desde el panel | Sí | `ReadOnlyMixin` en admin |
| Código Python modifica/borra un voto | Sí | `PermissionError` en `save()` y `delete()` |
| Voto modificado directamente en BD | Detectable | HMAC + `verify_chain()` |
| Voto insertado falsamente en la cadena | Detectable | `chain_hash` invalida registros posteriores |
| Eliminación de votos sin autorización | Bloqueada | Trigger DB + variable SQL temporal autorizada |
| Modificación arbitraria de `Count.number` | Bloqueada | Trigger DB (`number` solo puede subir `+1`) |
| Admin infla `Count.number` | Detectable | `is_consistent()` + `get_verified_count()` |
| Rastrear quién votó por qué opción | Imposible | Sin campos de identidad en `VotingRecord` |
