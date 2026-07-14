import pandas as pd
import re
from voting.models import UserData, Militante


def format_rut(rut_raw):
    """
    Formatea un RUT quitando puntos y guiones, y agregando el guión antes del dígito verificador.
    
    Args:
        rut_raw: RUT en cualquier formato (12.345.678-K, 12345678K, etc.)
        
    Returns:
        str: RUT formateado como 12345678-K
    """
    # Quitar espacios, puntos y guiones
    rut_clean = str(rut_raw).strip().replace('.', '').replace('-', '').replace(' ', '')
    
    if len(rut_clean) < 2:
        return rut_clean.upper()
    
    # Separar cuerpo y dígito verificador
    cuerpo = rut_clean[:-1]
    dv = rut_clean[-1]
    
    return f"{cuerpo}-{dv.upper()}"


class ExcelService:
    """Servicio para importar datos desde archivos Excel"""

    @staticmethod
    def import_user_data(voting, excel_file):
        """
        Importa datos de usuarios desde un archivo Excel
        
        El archivo Excel debe tener las columnas: rut
        
        Args:
            voting: Instancia de Voting
            excel_file: Archivo Excel subido
            
        Returns:
            int: Cantidad de usuarios importados
        """
        try:
            df = pd.read_excel(excel_file)
            
            if 'rut' not in df.columns:
                raise ValueError("El archivo debe contener una columna 'rut'")
            
            ruts_in_df = set()
            for index, row in df.iterrows():
                rut_raw = row['rut']
                if pd.notna(rut_raw):
                    rut = format_rut(rut_raw)
                    if rut:
                        ruts_in_df.add(rut)
            
            # Consultar los RUTs existentes para esta votación en una sola consulta
            existing_ruts = set(UserData.objects.filter(id_voting=voting, rut__in=ruts_in_df).values_list('rut', flat=True))
            new_ruts = ruts_in_df - existing_ruts
            
            if new_ruts:
                user_data_objects = [
                    UserData(id_voting=voting, rut=rut, register=False, has_voted=False)
                    for rut in new_ruts
                ]
                UserData.objects.bulk_create(user_data_objects, batch_size=1000)
            
            return len(new_ruts)
        
        except Exception as e:
            raise Exception(f"Error al procesar el archivo Excel: {str(e)}")

    @staticmethod
    def import_militantes_from_excel(excel_file):
        """
        Importa datos de militantes desde un archivo Excel para actualizar el padrón.
        
        Columnas:
        - A: RUT (se formatea)
        - B: Nombre
        - C: Mail (opcional)
        - D: Región (número 1-17, opcional)
        
        Lógica:
        1. RUT existe en Militante (activo) → solo actualiza región si viene en el Excel
        2. RUT existe en MilitanteRegistrationToken (pendiente) → actualiza mail/región;
           si el mail cambió, marca para reenvío de invitación
        3. RUT no existe → crea nuevo MilitanteRegistrationToken; incluye en envío solo si tiene mail
        
        Args:
            excel_file: Archivo Excel subido
            
        Returns:
            dict: {
                'new_users': [...],           # nuevos con mail (para envío)
                'updated_users': [...],       # pendientes con mail cambiado (para reenvío)
                'updated_active_count': int,  # activos con región actualizada
                'partial_count': int          # nuevos sin mail (solo padrón)
            }
        """
        from voting.models import MilitanteRegistrationToken
        
        try:
            df = pd.read_excel(excel_file, header=None)
            
            if len(df.columns) < 1:
                raise ValueError("El archivo debe tener al menos 1 columna: RUT (A)")
            
            rows_data = []
            ruts_in_df = set()
            
            for index, row in df.iterrows():
                rut_raw = row[0]  # Columna A
                
                if pd.isna(rut_raw):
                    continue
                
                nombre = str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ''  # Columna B
                mail = str(row[2]).strip().lower() if len(row) > 2 and pd.notna(row[2]) else ''  # Columna C
                
                # Parsear región (columna D): int 1-17, None si vacío/inválido
                region = None
                if len(row) > 3 and pd.notna(row[3]):
                    try:
                        region_val = int(float(row[3]))
                        if 1 <= region_val <= 17:
                            region = region_val
                    except (ValueError, TypeError):
                        pass
                
                # Formatear RUT
                rut = format_rut(rut_raw)
                if rut:
                    rows_data.append({
                        'nombre': nombre,
                        'rut': rut,
                        'mail': mail,
                        'region': region
                    })
                    ruts_in_df.add(rut)
            
            # Consultar militantes activos existentes
            existing_militantes = {
                m.rut: m for m in Militante.objects.filter(rut__in=ruts_in_df)
            }
            
            # Consultar tokens de registro pendientes (no usados)
            existing_tokens = {
                t.rut: t for t in MilitanteRegistrationToken.objects.filter(
                    rut__in=ruts_in_df, used=False
                )
            }
            
            new_users = []
            updated_users = []
            updated_active_count = 0
            partial_count = 0
            
            for data in rows_data:
                rut = data['rut']
                
                if rut in existing_militantes:
                    # 1. RUT existe como Militante activo → solo actualizar región
                    militante = existing_militantes[rut]
                    if data['region'] is not None and militante.region != data['region']:
                        militante.region = data['region']
                        militante.save()
                        updated_active_count += 1
                
                elif rut in existing_tokens:
                    # 2. RUT existe como token pendiente → actualizar mail y/o región
                    token = existing_tokens[rut]
                    mail_changed = False
                    
                    if data['mail'] and token.mail.lower() != data['mail'].lower():
                        token.mail = data['mail']
                        mail_changed = True
                    
                    if data['region'] is not None:
                        token.region = data['region']
                    
                    if data['nombre']:
                        token.nombre = data['nombre']
                    
                    token.save()
                    
                    if mail_changed and data['mail']:
                        updated_users.append(data)
                
                else:
                    # 3. RUT no existe → crear nuevo MilitanteRegistrationToken
                    MilitanteRegistrationToken.create_token(
                        nombre=data['nombre'],
                        rut=rut,
                        mail=data['mail']
                    )
                    # Actualizar región en el token recién creado
                    if data['region'] is not None:
                        new_token = MilitanteRegistrationToken.objects.filter(
                            rut=rut, used=False
                        ).order_by('-created_at').first()
                        if new_token:
                            new_token.region = data['region']
                            new_token.save()
                    
                    if data['mail']:
                        new_users.append(data)
                    else:
                        partial_count += 1
            
            return {
                'new_users': new_users,
                'updated_users': updated_users,
                'updated_active_count': updated_active_count,
                'partial_count': partial_count
            }
        
        except Exception as e:
            raise Exception(f"Error al procesar el archivo Excel: {str(e)}")

