import os
import time
import httpx  # Reemplazamos 'requests' por 'httpx' para Fish Audio
from flask import Flask, request, send_file
from groq import Groq
from pydub import AudioSegment 

# 1. TUS CREDENCIALES
cliente_groq = Groq(api_key="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")
FISH_API_KEY = "be69c5fec5b540019d7692f7d0998dbb"
ID_VOZ = "9f708cd9d8184a5c9781da535149e650"  # Tu ID de voz de Goku/Woody

# --- 🧸 CONFIGURACIÓN DEL PERSONAJE ---
NOMBRE_PERSONAJE = "Woody"
PERSONALIDAD = "amigable, sincero, divertido, toma la referencia de la pelicula de toy Story, tú eres el personaje woody"
PUBLICO = "un niño pequeño"

INSTRUCCION_SISTEMA = f"""Actúa 100% como {NOMBRE_PERSONAJE}, {PERSONALIDAD}. Estás hablando con {PUBLICO}.
Regla 1: Tus respuestas deben ser MUY cortas, fáciles de entender y al momento de que alguien diga su nombre, tú debes de saludar a esa persona con su nombre y continuar.
Regla 2: NUNCA digas que eres una inteligencia artificial. Eres el personaje real.
Regla 3 OBLIGATORIA: Al final de CADA respuesta, SIEMPRE debes hacer UNA pregunta corta, alegre y relacionada al tema para que el niño te siga hablando."""

app = Flask(__name__)

historial_chat = []
MAX_RECUERDOS = 10 

@app.route("/transcribir", methods=["POST"])
def transcribir():
    global historial_chat
    tiempo_inicio = time.time()
    audio_path = "temp.wav"
    
    with open(audio_path, "wb") as f:
        f.write(request.data)

    try:
        # ==========================================
        # 1. OÍDOS (GROQ - Whisper)
        # ==========================================
        with open(audio_path, "rb") as archivo_audio:
            transcripcion = cliente_groq.audio.transcriptions.create(
                file=("temp.wav", archivo_audio.read()),
                model="whisper-large-v3",
                language="es"
            )
        texto_usuario = transcripcion.text
        print(f"\n🧒 [NIÑO DICE]: {texto_usuario}")

        historial_chat.append({"role": "user", "content": texto_usuario})

        if len(historial_chat) > MAX_RECUERDOS:
            historial_chat = historial_chat[-MAX_RECUERDOS:]

        # ==========================================
        # 2. CEREBRO CON PERSONALIDAD (GROQ - Llama)
        # ==========================================
        mensajes_para_ia = [{"role": "system", "content": INSTRUCCION_SISTEMA}] + historial_chat

        respuesta_ia = cliente_groq.chat.completions.create(
            messages=mensajes_para_ia,
            model="llama-3.1-8b-instant",
        )
        
        texto_final = respuesta_ia.choices[0].message.content
        print(f"🧸 [{NOMBRE_PERSONAJE.upper()} RESPONDE]: {texto_final}")

        historial_chat.append({"role": "assistant", "content": texto_final})

        # ==========================================
        # 3. VOZ (HTTPX INTEGRADO CON FISH AUDIO)
        # ==========================================
        ruta_mp3 = "respuesta_temporal.mp3"
        ruta_respuesta = "respuesta.wav"
        print("🔊 [GENERANDO AUDIO CON FISH AUDIO...]")
        
        # El cuerpo de la petición con la opción de velocidad incluida
        body = {
            "text": texto_final,
            "reference_id": ID_VOZ, 
            "format": "mp3",
            "speed": 1.0  # <-- Si el ESP32 reproduce muy rápido a Woody, bájalo a 0.85
        }

        # Petición HTTP usando httpx (con timeout de seguridad de 30s)
        with httpx.Client(timeout=30.0) as client:
            respuesta_fish = client.post(
                "https://api.fish.audio/v1/tts",
                headers={
                    "Authorization": f"Bearer {FISH_API_KEY}",
                    "Content-Type": "application/json",
                    "model": "s2.1-pro-free", 
                },
                json=body,
            )

        if respuesta_fish.status_code == 200:
            # Guardamos el archivo MP3 entrante
            with open(ruta_mp3, "wb") as f:
                f.write(respuesta_fish.content)
                
            print("⚙️ [CONVIRTIENDO MP3 A WAV PARA EL ESP32...]")
            
            # Conversión: Adaptamos el MP3 a un formato WAV Mono a 8000Hz compatible con el DAC
            audio = AudioSegment.from_file(ruta_mp3, format="mp3")
            audio = audio.set_frame_rate(18000).set_channels(1) # O prueba con 16000 si 44100 falla
            audio.export(ruta_respuesta, format="wav")

            tiempo_total = round(time.time() - tiempo_inicio, 2)
            print(f"⏱️ [TIEMPO TOTAL]: {tiempo_total} segundos")

            # Enviamos el archivo WAV final de vuelta al microcontrolador ESP32
            return send_file(ruta_respuesta, mimetype="audio/wav")
            
        else:
            print(f"❌ [ERROR FISH AUDIO]: Código {respuesta_fish.status_code}")
            print(respuesta_fish.text)
            return "Error en el servicio de voz", 500

    except Exception as e:
        print(f"❌ [ERROR GENERAL]: {e}")
        return "Error interno", 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, threaded=False)