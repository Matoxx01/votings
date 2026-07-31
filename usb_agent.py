import asyncio
import json
import os
import websockets
import psutil
from pathlib import Path

# =====================================================================
# AGENTE LOCAL DE USB PARA DESBLOQUEO DE REPORTES
# Requisitos: pip install websockets psutil
# Ejecución: python usb_agent.py
# =====================================================================

KEY_FILE_NAME = ".security_key.json"

def get_removable_drives():
    """Retorna una lista de rutas (ej. ['E:\\', 'F:\\']) que son pendrives."""
    drives = []
    # psutil.disk_partitions en Windows detecta los USB como 'removable'
    for partition in psutil.disk_partitions(all=False):
        if 'removable' in partition.opts.lower():
            drives.append(partition.device)
    return drives

def read_keys():
    """Busca y lee las llaves en todos los pendrives conectados."""
    keys = []
    drives = get_removable_drives()
    for drive in drives:
        key_path = Path(drive) / KEY_FILE_NAME
        if key_path.exists():
            try:
                with open(key_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "token" in data:
                        keys.append(data["token"])
            except Exception as e:
                print(f"Error leyendo {key_path}: {e}")
    return keys

def write_key(drive_letter, token_data):
    """Escribe el archivo de llave en un pendrive específico."""
    drives = get_removable_drives()
    # Asegurar formato correcto (ej: E:\)
    if not drive_letter.endswith('\\'):
         drive_letter += '\\'
         
    if drive_letter not in drives:
        return {"success": False, "error": f"El disco {drive_letter} no es un dispositivo extraible válido."}
    
    key_path = Path(drive_letter) / KEY_FILE_NAME
    try:
        # En Windows, si el archivo ya existe y tiene el atributo OCULTO (HIDDEN) o SOLO LECTURA,
        # open(..., 'w') arroja [Errno 13] Permission denied.
        if os.name == 'nt' and key_path.exists():
            import ctypes
            FILE_ATTRIBUTE_NORMAL = 0x80
            ctypes.windll.kernel32.SetFileAttributesW(str(key_path), FILE_ATTRIBUTE_NORMAL)
            try:
                os.remove(key_path)
            except Exception as e_rem:
                print(f"Aviso al remover archivo previo: {e_rem}")

        with open(key_path, 'w', encoding='utf-8') as f:
            json.dump({"token": token_data}, f)
        
        # Ocultar el archivo en Windows (opcional)
        if os.name == 'nt':
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ctypes.windll.kernel32.SetFileAttributesW(str(key_path), FILE_ATTRIBUTE_HIDDEN)
            
        return {"success": True, "message": "Llave escrita correctamente."}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def handler(websocket, *args):
    print("Cliente (Navegador) conectado.")
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")
            
            if action == "SCAN":
                # Lista pendrives conectados
                drives = get_removable_drives()
                await websocket.send(json.dumps({"action": "SCAN_RESULT", "drives": drives}))
                
            elif action == "WRITE":
                # Escribe llave en un pendrive
                drive = data.get("drive")
                token = data.get("token")
                result = write_key(drive, token)
                await websocket.send(json.dumps({"action": "WRITE_RESULT", **result}))
                
            elif action == "POLL_KEYS":
                # Lee las llaves actualmente conectadas
                keys = read_keys()
                await websocket.send(json.dumps({"action": "KEYS_RESULT", "keys": keys}))
                
    except websockets.exceptions.ConnectionClosed:
        print("Cliente desconectado.")
    except Exception as e:
        print(f"Error en websocket: {e}")

async def main():
    port = 8765
    print(f"Iniciando Agente USB en ws://localhost:{port}")
    print("Asegúrate de que este programa esté corriendo cuando uses el Dashboard o la Pantalla de Desbloqueo.")
    async with websockets.serve(handler, "localhost", port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
