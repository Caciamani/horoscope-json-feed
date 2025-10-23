#!/usr/bin/env python3
"""
Generador de JSONs para BLOQUE 1 — versión mejorada (ajuste: energy usa mood)
- Determinismo total por date+sign+secret_salt
- Tips sin repetición por signo (hasta agotar pool)
- Guarda contexto mínimo para la IA (ai_prompt_context)
- Valida esquema mínimo y agrega hash al metadata
- Escritura atómica (tmp -> replace)
Requisitos: Python 3.9+ (zoneinfo). Cambia secret_salt por uno propio.
"""
from pathlib import Path
import os, json, hashlib, random, datetime, tempfile, shutil, sys, traceback

# Config ---------------------------------------------------------
SIGNS = ["aries","tauro","geminis","cancer","leo","virgo","libra","escorpio","sagitario","capricornio","acuario","piscis"]
MOODS = ["decidido","relajado","nostálgico","enérgico","pensativo","optimista","reservado","ansioso","valiente","curioso","indeciso","romántico","melancólico","motivado","sereno","aventurero","reflexivo","inspirado"]
CATEGORIES = ["general","love","friendship","energy","work","health","family","money","studies","creativity"]
CATEGORY_STATES = ["favorable","neutral","tenso","prometedor","precaucion","desafiante","estable","incierto","equilibrado"]
TIPS_POOL = [
    "Actúa en pequeñas metas para construir impulso",
    "Reserva 20 minutos para calmar la mente antes de actuar",
    "Comunica lo que sientes con claridad y sin agresión",
    "Prioriza lo urgente, delega lo demás",
    "Haz una caminata corta para resetear energía",
    "Escribe una lista de 3 cosas que sí puedes controlar hoy",
    "Envía un mensaje sincero a alguien que aprecias",
    "Hidrátate y respira profundo al menos 3 veces al día",
    "Evita decisiones grandes antes de las 15:00",
    "Haz una pausa creativa: dibuja o escucha 5 minutos de música",
    # Nuevos, más ambiguos y generalistas:
    "Confía en que lo que hoy parece confuso tendrá sentido más adelante",
    "Escucha más de lo que hablas, alguien cercano puede darte una pista valiosa",
    "No ignores las señales pequeñas, suelen anticipar cambios grandes",
    "Recuerda que no todo requiere una respuesta inmediata",
    "Un gesto sencillo puede abrir una puerta inesperada",
    "Lo que hoy postergas puede transformarse en claridad mañana",
    "Permítete cambiar de opinión sin sentir culpa",
    "El silencio también es una forma de comunicación",
    "A veces avanzar significa soltar lo que pesa",
    "No subestimes el poder de una pausa breve",
    "Lo que buscas afuera puede estar más cerca de lo que imaginas",
    "Un detalle cotidiano puede inspirarte más de lo que crees",
    "No necesitas resolver todo hoy, solo dar el siguiente paso",
    "La intuición puede ser tan válida como la lógica",
    "Un pequeño ajuste en tu rutina puede traer un gran alivio",
    "Lo que parece un obstáculo puede ser un desvío necesario",
    "Escucha tu cuerpo, suele hablar antes que tu mente",
    "Un cambio de perspectiva puede transformar la misma situación",
    "No temas pedir ayuda, incluso los más fuertes lo hacen",
    "Recuerda que cada día trae una oportunidad distinta",
    "Lo que hoy te incomoda puede ser la semilla de un aprendizaje",
    "Un inicio modesto puede llevar a un resultado inesperado",
    "No todo lo que brilla es urgente, ni todo lo simple es menor",
    "A veces la mejor decisión es esperar un poco más",
    "Lo que das sin esperar puede regresar multiplicado",
    "Un espacio ordenado puede traer claridad mental",
    "No ignores esa idea que vuelve una y otra vez",
    "El equilibrio no siempre es estático, a veces es movimiento",
    "Lo que hoy parece pequeño puede crecer con constancia",
    "Abraza lo desconocido, podría revelar caminos inesperados",
    "Reflexiona sobre un recuerdo positivo para ganar perspectiva",
    "Conecta con alguien del pasado, podría sorprenderte",
    "Practica la gratitud por algo pequeño cada mañana",
    "Suelta expectativas y fluye con lo que llega",
    "Busca equilibrio entre acción y descanso",
    "Confía en tus instintos, rara vez se equivocan",
    "Rodéate de energías que te eleven",
    "Nutre una idea creativa que has pospuesto",
    "Sé receptivo a señales del entorno",
    "Encuentra paz en momentos de soledad",
    "Cultiva paciencia en situaciones ambiguas",
    "Expresa lo que sientes de forma sutil",
    "Perdona un error propio para avanzar ligero",
    "Mantén curiosidad por lo cotidiano",
    "Prioriza tu bienestar en decisiones diarias",
    "Adáptate a lo nuevo sin resistir",
    "Comparte una sonrisa, puede cambiar un día",
    "Enfócate en el presente, el futuro se moldea ahí",
    "Celebra un logro modesto con alegría",
    "Explora una ruta diferente en tu rutina",
    "Escucha el silencio, a veces dice mucho",
    "Libera espacio mental eliminando lo innecesario",
    "Acepta que no todo tiene explicación inmediata",
    "Un gesto amable puede generar conexiones profundas",
    "Visualiza un outcome positivo antes de actuar",
    "No fuerces respuestas, llegan en su momento",
    "Encuentra inspiración en la naturaleza cercana",
    "Permite que las emociones fluyan sin juzgar",
    "Un cambio sutil puede alterar el curso",
    "Recuerda que la resiliencia se construye paso a paso",
    "Busca armonía en opuestos aparentes",
    "Ignora distracciones y enfócate en lo esencial",
    "Un momento de reflexión puede aclarar dudas",
    "Sé flexible, la rigidez limita oportunidades",
    "Agradece las lecciones disfrazadas de desafíos",
    "Conecta con tu esencia en tiempos turbulentos",
    "No subestimes el impacto de palabras amables",
    "Explora lo familiar con ojos nuevos",
    "Libera cargas emocionales para ganar libertad",
    "Acepta invitaciones inesperadas con apertura",
    "Un respiro consciente puede renovar energías",
    "Busca patrones en lo que parece aleatorio",
    "Permítete soñar sin límites por un rato",
    "Encuentra fuerza en vulnerabilidades compartidas",
    "No apresures procesos, maduran con tiempo",
    "Celebra la diversidad en opiniones ajenas",
    "Un detalle atento puede fortalecer lazos",
    "Reflexiona sobre lo que realmente valoras",
    "Sé paciente con el crecimiento personal",
    "Libera juicios y observa con neutralidad",
    "Encuentra belleza en imperfecciones diarias",
    "Conecta ideas dispersas para innovar",
    "Acepta que el cambio es constante y necesario",
    "Un paso atrás puede impulsar dos adelante",
    "Nutre relaciones con presencia auténtica",
    "Ignora el ruido y escucha tu voz interior",
    "Celebra el progreso, no solo el destino",
    "Busca claridad en la simplicidad",
    "Permítete descansar sin remordimientos",
    "Explora curiosidades que surjan espontáneamente",
    "Libera miedos infundados para avanzar",
    "Encuentra equilibrio en el dar y recibir",
    "Sé abierto a retroalimentación constructiva",
    "Un momento de juego puede aligerar cargas",
    "Reflexiona sobre sincronías en tu vida",
    "Acepta lo impredecible como parte del viaje",
    "Conecta con pasiones olvidadas para revivir",
    "No temas la quietud, trae revelaciones",
    "Celebra tu unicidad en un mundo diverso",
    "Busca inspiración en historias ajenas",
    "Permítete evolucionar sin presiones externas",
    "Encuentra paz en rutinas mindful",
    "Libera apegos que ya no sirven",
    "Sé compasivo contigo en días difíciles",
    "Explora nuevos ángulos en problemas viejos",
    "Un gesto de bondad puede ripplear lejos",
    "Reflexiona sobre gratitudes nocturnas",
    "Acepta transiciones como puertas a lo nuevo",
    "Conecta con el flujo natural de la vida",
    "Ignora comparaciones y enfócate en tu camino",
    "Celebra momentos de conexión genuina",
    "Busca sabiduría en experiencias pasadas",
    "Permítete pausas para recargar",
    "Encuentra motivación en metas personales",
    "Libera tensiones con movimientos suaves",
    "Sé curioso sobre posibilidades futuras",
    "Un cambio de enfoque puede desbloquear soluciones",
    "Reflexiona sobre lecciones aprendidas recientemente",
    "Acepta que la perfección es ilusoria",
    "Conecta con otros desde la empatía",
    "No subestimes el poder de la consistencia",
    "Celebra avances sutiles en tu jornada",
    "Busca armonía en el caos aparente",
    "Permítete experimentar sin expectativas",
    "Encuentra fuerza en comunidades afines",
    "Libera dudas y actúa con convicción",
    "Sé atento a oportunidades disfrazadas"
]

# Ajustes operativos (modificá según necesites)
secret_salt = "CHANGE_THIS_SECRET_SALT_FOR_PRODUCTION"
base_path = Path(r"C:\Users\Aspire Lite\OneDrive\Escritorio\Horoscopo-app\horoscope-json-app\daily")
open_folder_after = True   # True = intenta abrir carpeta en Windows al final
write_pretty = True        # True = indentado para lectura humana

# Zona horaria
try:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Argentina/Mendoza")
except Exception:
    tz = datetime.timezone.utc

now = datetime.datetime.now(tz)
date_str = now.date().isoformat()

# Helpers --------------------------------------------------------
def deterministic_seed(*parts) -> int:
    h = hashlib.sha256(("_".join(parts)).encode("utf-8")).hexdigest()
    return int(h, 16)

def compute_sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def safe_atomic_write(path: Path, data_bytes: bytes):
    dirpath = path.parent
    dirpath.mkdir(parents=True, exist_ok=True)
    fd, tmpname = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "wb") as tmpf:
            tmpf.write(data_bytes)
        os.replace(tmpname, str(path))
    except Exception:
        try:
            os.remove(tmpname)
        except Exception:
            pass
        raise

def minimal_validate_structure(d: dict) -> (bool, str):
    required = ["date","version","sign","mood","header_summary","categories","metadata"]
    for k in required:
        if k not in d:
            return False, f"Falta campo obligatorio: {k}"
    if not isinstance(d["categories"], dict):
        return False, "categories debe ser un objeto/dict"
    for cat, v in d["categories"].items():
        if not isinstance(v, dict):
            return False, f"categories.{cat} debe ser objeto"
        for sub in ("state","text","tips"):
            if sub not in v:
                return False, f"categories.{cat} falta {sub}"
        if not isinstance(v["tips"], list):
            return False, f"categories.{cat}.tips debe ser lista"
    return True, "OK"

# Lógica principal ----------------------------------------------
def generate_for_sign(sign: str):
    seed_int = deterministic_seed(date_str, sign, secret_salt)
    rnd = random.Random(seed_int)

    mood = rnd.choice(MOODS)

    category_states = {}
    for i, cat in enumerate(CATEGORIES):
        category_states[cat] = random.Random(seed_int + i * 97).choice(CATEGORY_STATES)

    tips_ordered = random.Random(seed_int + 12345).sample(TIPS_POOL, k=len(TIPS_POOL))
    total_slots = len(CATEGORIES) * 2
    if total_slots <= len(tips_ordered):
        tips_extended = tips_ordered
    else:
        extra_needed = total_slots - len(tips_ordered)
        second = random.Random(seed_int + 54321).sample(TIPS_POOL, k=len(TIPS_POOL))
        tips_extended = tips_ordered + second[:extra_needed]

    categories_obj = {}
    tip_idx = 0
    for cat in CATEGORIES:
        n_tips = 2 if len(TIPS_POOL) >= 2 else 1
        chosen = []
        for _ in range(n_tips):
            if tip_idx >= len(tips_extended):
                tip_idx = 0
            chosen.append(tips_extended[tip_idx] + " [Placeholder]")
            tip_idx += 1
        # --- Cambio solicitado: para la categoría 'energy' mostrar el mood como estado energético ---
        text = f"Estado energético: {category_states[cat]}. [Placeholder]"
        categories_obj[cat] = {
            "state": category_states[cat],
            "text": text,
            "tips": chosen
        }

    flat_tips = []
    for cat in CATEGORIES:
        for t in categories_obj[cat]["tips"]:
            if t not in flat_tips:
                flat_tips.append(t)
    tips_for_ai = [t.replace(" [Placeholder]", "") for t in flat_tips[:3]]

    ai_prompt_context = {
        "sign": sign,
        "mood": mood,
        "top_tips": tips_for_ai,
        "sample_category_states": {cat: category_states[cat] for cat in list(CATEGORIES)[:3]}
    }

    prompt_short = f"Genera un texto de 1–2 oraciones, tono: breve y empático. Contexto: sign={sign}, mood={mood}, tips={';'.join(tips_for_ai)}, categories={ai_prompt_context['sample_category_states']}. Produce un encabezado que resuma el día para el usuario dirigido a '{sign}' empezando por el nombre del signo y sin etiquetas."

    header = f"[IA] {sign.capitalize()}, hoy tu energía va a estar {mood}; prioriza lo esencial y evita dispersarte."

    metadata = {
        "author": "team_astrology",
        "seed": hashlib.sha256(f"{date_str}_{sign}_{secret_salt}".encode()).hexdigest(),
        "last_updated": now.replace(microsecond=0).isoformat(),
        "ai_prompt": prompt_short
    }

    obj = {
        "date": date_str,
        "version": "1.0",
        "sign": sign,
        "mood": mood,
        "header_summary": header,
        "categories": categories_obj,
        "ai_prompt_context": ai_prompt_context,
        "target_advice_summary": {
            "default_strategy": "align_with_mood",
            "note": "Ver compatibility/ para detalles por par"
        },
        "metadata": metadata
    }

    ok, msg = minimal_validate_structure(obj)
    if not ok:
        raise ValueError(f"Validation failed for {sign}: {msg}")

    if write_pretty:
        json_bytes = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    else:
        json_bytes = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    file_hash = compute_sha256_bytes(json_bytes)
    obj["metadata"]["hash"] = file_hash
    if write_pretty:
        json_bytes = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    else:
        json_bytes = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    out_path = base_path / f"{sign}_today.json"
    safe_atomic_write(out_path, json_bytes)

    return out_path, obj

# Runner --------------------------------------------------------
def main():
    created = []
    errors = []
    try:
        base_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print("No pude crear base_path:", base_path, "->", e)
        raise

    for sign in SIGNS:
        try:
            p, obj = generate_for_sign(sign)
            created.append(p)
        except Exception as e:
            tb = traceback.format_exc()
            errors.append((sign, str(e), tb))
            print(f"[ERROR] {sign}: {e}", file=sys.stderr)

    print(f"Archivos generados: {len(created)}. Carpeta: {base_path}")
    for p in created:
        print(" -", p)

    if errors:
        print("\nAlgunos signos fallaron:")
        for s, msg, tb in errors:
            print(f" * {s}: {msg}")
            with open(base_path / "errors.log", "a", encoding="utf-8") as ef:
                ef.write(f"\n\n[{datetime.datetime.now().isoformat()}] {s} error: {msg}\n{tb}\n")

    if open_folder_after:
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(base_path))
            else:
                print("No intento abrir la carpeta automáticamente fuera de Windows. Ruta:", base_path)
        except Exception as e:
            print("No pude abrir la carpeta automáticamente:", e)

if __name__ == "__main__":
    main()
