import pandas as pd
from voting.models import UserData


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
    def export_voting_results(voting):
        """
        Exporta los resultados de una votación a un archivo Excel
        
        Args:
            voting: Instancia de Voting
            
        Returns:
            pd.DataFrame: DataFrame con los resultados
        """
        from voting.models import VotingRecord
        
        records = VotingRecord.objects.filter(id_voting=voting).values(
            'rut', 'mail', 'id_subject__name', 'voted_at'
        )
        
        df = pd.DataFrame(list(records))
        return df
