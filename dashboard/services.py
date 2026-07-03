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
        Importa datos de militantes desde un archivo Excel para envío de correos.
        
        Si un RUT ya existe como Militante y el mail del Excel es distinto,
        actualiza el mail del Militante y lo marca para reenvío de invitación.
        
        Columnas:
        - A: RUT (se formatea)
        - B: Nombre
        - C: Mail
        
        Args:
            excel_file: Archivo Excel subido
            
        Returns:
            dict: {'new_users': [...], 'updated_users': [...]}
                  Cada elemento es un dict con {nombre, rut, mail}
        """
        from voting.models import MilitanteRegistrationToken
        
        try:
            df = pd.read_excel(excel_file, header=None)
            
            if len(df.columns) < 3:
                raise ValueError("El archivo debe tener al menos 3 columnas: RUT (A), Nombre (B), Mail (C)")
            
            rows_data = []
            ruts_in_df = set()
            
            for index, row in df.iterrows():
                rut_raw = row[0]  # Columna A
                nombre = str(row[1]).strip() if pd.notna(row[1]) else ''  # Columna B
                mail = str(row[2]).strip().lower() if pd.notna(row[2]) else ''  # Columna C
                
                if pd.isna(rut_raw) or not nombre or not mail:
                    continue
                
                # Formatear RUT
                rut = format_rut(rut_raw)
                if rut:
                    rows_data.append({
                        'nombre': nombre,
                        'rut': rut,
                        'mail': mail
                    })
                    ruts_in_df.add(rut)
            
            # Consultar militantes existentes con sus mails (evita N+1 queries)
            existing_militantes = {
                m.rut: m for m in Militante.objects.filter(rut__in=ruts_in_df)
            }
            
            new_users = []
            updated_users = []
            
            for data in rows_data:
                if data['rut'] not in existing_militantes:
                    # RUT no existe → nuevo usuario
                    new_users.append(data)
                else:
                    # RUT existe → verificar si el mail cambió
                    militante = existing_militantes[data['rut']]
                    if militante.mail.lower() != data['mail'].lower():
                        # Mail distinto → actualizar mail del militante
                        militante.mail = data['mail']
                        militante.save()
                        
                        # Invalidar tokens de registro anteriores para este RUT
                        MilitanteRegistrationToken.objects.filter(
                            rut=data['rut'], used=False
                        ).update(used=True)
                        
                        updated_users.append(data)
            
            return {'new_users': new_users, 'updated_users': updated_users}
        
        except Exception as e:
            raise Exception(f"Error al procesar el archivo Excel: {str(e)}")

