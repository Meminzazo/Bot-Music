# Plan de Implementación - Bot DJ Discord

## Resumen
Bot de Discord en Python que funciona como DJ por voz, ejecutable localmente con `python bot.py`.

## Stack Tecnológico
- **Lenguaje**: Python 3.10+
- **Librería Discord**: `discord.py` (v2.x)
- **Audio**: `yt-dlp` (descarga de YouTube/SoundCloud), `ffmpeg` (procesamiento de audio)
- **Conexión de voz**: `discord.py` voice client nativo
- **Configuración**: `python-dotenv` (variables de entorno)

## Arquitectura

```
bot/
├── main.py              # Punto de entrada
├── config.py            # Configuración y variables de entorno
├── music/
│   ├── __init__.py
│   ├── player.py        # Lógica de reproducción (queue, play, pause, skip)
│   ├── downloader.py    # Descarga de audio con yt-dlp
│   └── queue.py         # Gestión de cola de reproducción
├── commands/
│   ├── __init__.py
│   ├── music.py         # Comandos de música (!play, !pause, !skip, !queue)
│   └── voice.py         # Comandos de voz (!join, !leave)
├── utils/
│   ├── __init__.py
│   └── helpers.py       # Funciones auxiliares
├── requirements.txt     # Dependencias
├── .env.example         # Plantilla de configuración
└── README.md            # Documentación
```

## Funcionalidades MVP

### 1. Conexión de Voz
- `!join` - Bot se une al canal de voz del usuario
- `!leave` - Bot sale del canal de voz

### 2. Reproducción de Música
- `!play <url/búsqueda>` - Reproducir música de YouTube o añadir a cola
- `!pause` - Pausar reproducción actual
- `!resume` - Reanudar reproducción pausada
- `!skip` - Saltar canción actual
- `!queue` - Mostrar cola de reproducción
- `!nowplaying` - Mostrar canción actual
- `!stop` - Detener y limpiar cola

### 3. Gestión de Cola
- Cola FIFO (First In, First Out)
- Soporte para múltiples servidores (guilds) simultáneos
- Persistencia en memoria (se pierde al reiniciar)

## Dependencias Principales

```txt
discord.py>=2.3.0
yt-dlp>=2024.1.0
python-dotenv>=1.0.0
PyNaCl>=1.5.0  # Para voz en Discord
```

## Requisitos del Sistema
- **Python 3.10+**
- **FFmpeg** instalado y en PATH del sistema
- **Token de bot de Discord** (desde Developer Portal)

## Pasos de Implementación

### Fase 1: Configuración Base
1. Crear estructura de carpetas
2. Configurar `requirements.txt`
3. Crear `.env.example` y `config.py`
4. Configurar `main.py` con bot básico

### Fase 2: Sistema de Voz
1. Implementar comandos `join` y `leave`
2. Manejo de conexión/desconexión de voz
3. Gestión de voice clients por guild

### Fase 3: Descarga de Audio
1. Implementar `downloader.py` con yt-dlp
2. Extraer info de video (título, duración, thumbnail, URL de audio)
3. Manejo de errores y timeouts

### Fase 4: Reproductor y Cola
1. Implementar `queue.py` - Cola por guild
2. Implementar `player.py` - Lógica de reproducción con ffmpeg
3. Callbacks de fin de canción (auto-siguiente)

### Fase 5: Comandos de Música
1. Implementar comandos en `commands/music.py`
2. Implementar comandos de voz en `commands/voice.py`
3. Registrar comandos en el bot

### Fase 6: Testing y Pulido
1. Probar en servidor de desarrollo
2. Manejo de edge cases
3. Documentación en README

## Variables de Entorno (.env)

```env
DISCORD_TOKEN=tu_token_aqui
PREFIX=!                    # Prefijo de comandos
MAX_QUEUE_SIZE=50          # Límite de cola
DEFAULT_VOLUME=0.5         # Volumen por defecto (0.0 - 1.0)
```

## Comandos de Inicio

```bash
# Instalar dependencias
pip install -r requirements.txt

# Copiar y configurar .env
cp .env.example .env
# Editar .env con tu token

# Ejecutar
python main.py
```

## Consideraciones Importantes

1. **FFmpeg**: Debe estar instalado en el sistema y accesible desde PATH
   - Windows: Descargar de https://ffmpeg.org/download.html y añadir a PATH
   - Verificar: `ffmpeg -version` en terminal

2. **Permisos del Bot**: En Discord Developer Portal, habilitar:
   - `Message Content Intent`
   - `Server Members Intent` (opcional)
   - `Voice` permissions en el servidor

3. **Intents necesarios**:
   ```python
   intents = discord.Intents.default()
   intents.message_content = True
   intents.voice_states = True
   intents.guilds = True
   ```

4. **Manejo de errores**:
   - Usuario no en canal de voz
   - Bot ya en otro canal
   - URL inválida
   - Error de descarga/ffmpeg
   - Cola llena