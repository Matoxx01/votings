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
            
            count = 0
            for index, row in df.iterrows():
                rut = str(row['rut']).strip().upper()
                
                if rut:
                    user_data, created = UserData.objects.get_or_create(
                        id_voting=voting,
                        rut=rut,
                        defaults={'register': False, 'has_voted': False}
                    )
                    if created:
                        count += 1
            
            return count
        
        except Exception as e:
            raise Exception(f"Error al procesar el archivo Excel: {str(e)}")

    @staticmethod
    def import_militantes_from_excel(excel_file):
        """
        Importa datos de militantes desde un archivo Excel para envío de correos
        
        Columnas:
        - A: RUT (se formatea)
        - B: Nombre
        - C: Mail
        
        Args:
            excel_file: Archivo Excel subido
            
        Returns:
            list: Lista de diccionarios con {nombre, rut, mail}
        """
        try:
            df = pd.read_excel(excel_file, header=None)
            
            if len(df.columns) < 3:
                raise ValueError("El archivo debe tener al menos 3 columnas: RUT (A), Nombre (B), Mail (C)")
            
            users = []
            for index, row in df.iterrows():
                rut_raw = row[0]  # Columna A
                nombre = str(row[1]).strip() if pd.notna(row[1]) else ''  # Columna B
                mail = str(row[2]).strip().lower() if pd.notna(row[2]) else ''  # Columna C
                
                if pd.isna(rut_raw) or not nombre or not mail:
                    continue
                
                # Formatear RUT
                rut = format_rut(rut_raw)
                
                # Validar que no existe ya como militante
                if Militante.objects.filter(rut=rut).exists():
                    continue  # Saltar si ya existe
                
                users.append({
                    'nombre': nombre,
                    'rut': rut,
                    'mail': mail
                })
            
            return users
        
        except Exception as e:
            raise Exception(f"Error al procesar el archivo Excel: {str(e)}")

