
#!/usr/bin/env python3
"""
Generador de JSONs para BLOQUE 1 — versión final (ruta relativa a ../Daily)
- Guarda en ../Daily relativo a la ubicación del script.
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
TIPS_GENERAL = [
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
TIPS_LOVE = [
    "Confía en que un encuentro inesperado podría encender una chispa duradera",
    "Permite que el corazón guíe sin apresurar juicios",
    "Un gesto sutil puede reavivar conexiones pasadas",
    "Escucha lo no dicho en las palabras de quien amas",
    "Lo que parece un desacuerdo podría ser el puente a una mayor intimidad",
    "Suelta expectativas y abraza el flujo natural del afecto",
    "Un momento de vulnerabilidad puede fortalecer lazos profundos",
    "Recuerda que el amor verdadero florece con paciencia",
    "No ignores señales pequeñas en el romance, podrían guiarte",
    "Un cambio de perspectiva podría transformar una relación estancada",
    "Permítete soñar con posibilidades románticas sin límites",
    "Lo que das con autenticidad regresa de formas inesperadas",
    "Encuentra equilibrio entre dar y recibir en el amor",
    "Un silencio compartido puede decir más que mil palabras",
    "A veces, soltar lo viejo abre espacio para lo nuevo en el corazón",
    "Confía en tu intuición para navegar emociones complejas",
    "Celebra detalles cotidianos que nutren el vínculo",
    "No temas expresar deseos, podría sorprender positivamente",
    "Lo que hoy parece confuso en el amor aclarará con tiempo",
    "Un gesto de bondad puede ripplear en olas de cariño"
]

TIPS_FRIENDSHIP = [
    "Un mensaje casual podría fortalecer un lazo olvidado",
    "Escucha con empatía, un amigo podría necesitarlo más de lo que dice",
    "Permite que las diferencias enriquezcan la conexión compartida",
    "Un encuentro espontáneo puede revivir alegrías pasadas",
    "Suelta rencores para dar espacio a nuevas aventuras juntas",
    "Confía en que la lealtad verdadera resiste pruebas sutiles",
    "Comparte una risa, puede disipar tensiones acumuladas",
    "No subestimes el poder de un apoyo silencioso",
    "Un gesto de gratitud puede deepenar amistades existentes",
    "Permítete ser vulnerable, atrae conexiones auténticas",
    "Lo que parece un malentendido podría ser una lección en comprensión",
    "Celebra éxitos ajenos como propios para nutrir el vínculo",
    "Un cambio en la rutina compartida podría traer frescura",
    "Escucha señales no verbales en interacciones diarias",
    "Confía en el flujo natural de las amistades evolutivas",
    "Un momento de reflexión puede aclarar dinámicas confusas",
    "No apresures reconciliaciones, llegan en su tiempo",
    "Lo que das en amistad regresa multiplicado inesperadamente",
    "Permite que el espacio temporal fortalezca lazos",
    "Un gesto simple puede abrir puertas a confidencias profundas"
]

TIPS_ENERGY = [
    "Respira profundo para recargar fuerzas internas",
    "Un paseo breve puede resetear vibraciones estancadas",
    "Permite que el descanso sea parte de tu flujo diario",
    "Confía en que la fatiga temporal precede a un surge de vitalidad",
    "Escucha a tu cuerpo, sabe cuándo pausar",
    "Un cambio sutil en hábitos puede elevar niveles generales",
    "Suelta lo que drena para invitar renovación",
    "Celebra momentos de calma como fuentes de poder",
    "No ignores señales de agotamiento, son guías valiosas",
    "Un pensamiento positivo puede amplificar reservas ocultas",
    "Permítete fluir con ritmos naturales del día",
    "Lo que parece bajo podría ser preparación para un pico",
    "Encuentra equilibrio entre actividad y reposo",
    "Un momento mindful puede transformar energías dispersas",
    "Confía en la intuición para elegir tareas energizantes",
    "Libera tensiones acumuladas con movimientos suaves",
    "Celebra progresos pequeños que acumulan momentum",
    "No subestimes el impacto de hidratación y nutrición",
    "Un ajuste en el entorno puede revitalizar el espíritu",
    "Permite que la naturaleza inspire un flujo renovado"
]

TIPS_WORK = [
    "Un enfoque paso a paso puede desbloquear avances inesperados",
    "Permite que la colaboración revele soluciones ocultas",
    "Confía en que un desafío actual forja habilidades futuras",
    "Escucha ideas ajenas, podrían complementar las tuyas",
    "Suelta perfeccionismo para ganar eficiencia",
    "Un pausa breve puede aclarar metas confusas",
    "Celebra logros modestos en la jornada laboral",
    "No ignores intuiciones sobre decisiones profesionales",
    "Un cambio en la rutina podría impulsar productividad",
    "Permítete delegar para equilibrar cargas",
    "Lo que parece un obstáculo podría ser una oportunidad disfrazada",
    "Encuentra inspiración en tareas cotidianas",
    "Confía en el timing para acciones clave",
    "Libera distracciones para enfocar energías",
    "Un gesto de reconocimiento puede motivar equipos",
    "No subestimes el poder de listas organizadas",
    "Celebra transiciones como puertas a crecimiento",
    "Permite que la flexibilidad adapte planes rígidos",
    "Un momento de reflexión puede alinear objetivos",
    "Suelta lo innecesario para priorizar lo esencial"
]

TIPS_HEALTH = [
    "Escucha señales sutiles de tu cuerpo para mantener equilibrio",
    "Un hábito pequeño puede transformar bienestar general",
    "Permite que el descanso sea prioridad sin culpas",
    "Confía en que la consistencia trae resultados duraderos",
    "Suelta tensiones con respiraciones conscientes",
    "Celebra elecciones nutritivas como inversiones en ti",
    "No ignores el rol de la mente en la vitalidad física",
    "Un movimiento diario puede elevar ánimos y fuerzas",
    "Permítete pausas para recargar reservas internas",
    "Lo que parece un retroceso podría ser un ajuste necesario",
    "Encuentra armonía entre actividad y reposo",
    "Confía en intuiciones sobre cambios saludables",
    "Libera hábitos drenantes para invitar frescura",
    "Un pensamiento positivo puede apoyar curaciones",
    "Celebra progresos sutiles en el viaje del bienestar",
    "No subestimes el impacto de hidratación diaria",
    "Permite que la naturaleza nutra cuerpo y espíritu",
    "Un ajuste en la dieta podría sorprender positivamente",
    "Escucha emociones, influyen en la salud holística",
    "Suelta expectativas para fluir con ritmos naturales"
]

TIPS_FAMILY = [
    "Un diálogo abierto puede resolver tensiones latentes",
    "Permite que el tiempo cure heridas pasadas",
    "Confía en que los lazos profundos resisten pruebas",
    "Escucha perspectivas familiares con empatía",
    "Suelta control para fomentar independencia mutua",
    "Celebra tradiciones que unen generaciones",
    "No ignores gestos pequeños que nutren vínculos",
    "Un momento compartido puede revivir alegrías",
    "Permítete expresar gratitud por presencias constantes",
    "Lo que parece conflicto podría ser crecimiento disfrazado",
    "Encuentra equilibrio en roles dinámicos",
    "Confía en la resiliencia familiar innata",
    "Libera expectativas rígidas para abrazar cambios",
    "Un acto de apoyo puede fortalecer cimientos",
    "Celebra diferencias como riquezas únicas",
    "No subestimes el poder de disculpas sinceras",
    "Permite que el espacio temporal refresque conexiones",
    "Un recuerdo compartido puede iluminar el presente",
    "Escucha lo no verbal en interacciones diarias",
    "Suelta rencores para invitar armonía renovada"
]

TIPS_MONEY = [
    "Un ajuste pequeño en gastos puede abrir flujos inesperados",
    "Permite que la paciencia guíe decisiones financieras",
    "Confía en que la abundancia llega en formas sutiles",
    "Escucha consejos sabios sin apresurar acciones",
    "Suelta impulsos para priorizar estabilidad",
    "Celebra ahorros modestos como bases sólidas",
    "No ignores señales de oportunidades ocultas",
    "Un plan simple puede aclarar metas confusas",
    "Permítete invertir en ti mismo con moderación",
    "Lo que parece pérdida podría ser lección valiosa",
    "Encuentra equilibrio entre gastar y reservar",
    "Confía en intuiciones sobre riesgos calculados",
    "Libera deudas emocionales que pesan en finanzas",
    "Un gesto generoso puede retornar multiplicado",
    "Celebra progresos en independencia económica",
    "No subestimes el valor de presupuestos flexibles",
    "Permite que el flujo natural atraiga prosperidad",
    "Un cambio en hábitos podría sorprender positivamente",
    "Escucha el entorno para ideas innovadoras",
    "Suelta miedos para abrazar posibilidades"
]

TIPS_STUDIES = [
    "Un enfoque paso a paso puede desbloquear conocimientos profundos",
    "Permite que la curiosidad guíe exploraciones",
    "Confía en que el esfuerzo constante trae claridad",
    "Escucha preguntas internas para deepenar comprensión",
    "Suelta distracciones para enfocar mente",
    "Celebra descubrimientos modestos en el aprendizaje",
    "No ignores intuiciones sobre temas complejos",
    "Un pausa reflexiva puede conectar ideas dispersas",
    "Permítete experimentar con métodos nuevos",
    "Lo que parece confusión podría ser preludio a insight",
    "Encuentra equilibrio entre teoría y práctica",
    "Confía en el proceso evolutivo del saber",
    "Libera presiones para invitar inspiración",
    "Un grupo de estudio puede revelar perspectivas frescas",
    "Celebra progresos en habilidades adquiridas",
    "No subestimes el poder de repeticiones mindful",
    "Permite que el descanso recargue concentración",
    "Un cambio en el entorno podría impulsar productividad",
    "Escucha mentores para atajos valiosos",
    "Suelta perfeccionismo para fluir con el aprendizaje"
]

TIPS_CREATIVITY = [
    "Un idea fugaz podría ser semilla de algo grandioso",
    "Permite que el flujo libre inspire expresiones únicas",
    "Confía en que el bloqueo temporal precede a un breakthrough",
    "Escucha musas internas sin juzgar",
    "Suelta rutinas para invitar innovación",
    "Celebra experimentos fallidos como lecciones",
    "No ignores impulsos creativos espontáneos",
    "Un cambio de perspectiva puede transformar visiones",
    "Permítete jugar sin expectativas de resultado",
    "Lo que parece caos podría ser patrón emergente",
    "Encuentra inspiración en lo cotidiano",
    "Confía en la intuición para guiar procesos",
    "Libera críticas internas para liberar potencial",
    "Un colaboración inesperada puede enriquecer obras",
    "Celebra expresiones auténticas como triunfos",
    "No subestimes el rol de pausas en la creación",
    "Permite que la naturaleza nutra imaginaciones",
    "Un ajuste en herramientas podría desatar flujos",
    "Escucha feedback con apertura creativa",
    "Suelta control para abrazar lo impredecible"
]


# Mapeo de categoría -> pool variable
TIP_POOLS = {
    "general": TIPS_GENERAL,
    "love": TIPS_LOVE,
    "friendship": TIPS_FRIENDSHIP,
    "energy": TIPS_ENERGY,
    "work": TIPS_WORK,
    "health": TIPS_HEALTH,
    "family": TIPS_FAMILY,
    "money": TIPS_MONEY,
    "studies": TIPS_STUDIES,
    "creativity": TIPS_CREATIVITY,
}

# Fallback mínimo si no hay nada en los pools
DEFAULT_TIP = ["Haz una pausa breve y respira."]

# Ajustes operativos
secret_salt = "CHANGE_THIS_SECRET_SALT_FOR_PRODUCTION"
open_folder_after = True
write_pretty = True

# Zona horaria
try:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Argentina/Mendoza")
except Exception:
    tz = datetime.timezone.utc

now = datetime.datetime.now(tz)
date_str = now.date().isoformat()

# Determina base_path relativo: sube un nivel desde la ubicación del script y crea 'Daily'
try:
    script_dir = Path(__file__).resolve().parent
except NameError:
    script_dir = Path.cwd()
base_path = script_dir.parent / "Daily"

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

def select_deterministic_from_pool(seed_int: int, pool: list, k: int):
    """
    Selección determinística de k items desde pool.
    - Si pool tiene >= k: devuelve sample determinístico.
    - Si pool tiene < k: devuelve elementos únicos y luego completa ciclando determinísticamente.
    """
    rnd = random.Random(seed_int)
    n = len(pool)
    if n == 0:
        return []
    if n >= k:
        # sample determinístico
        return rnd.sample(pool, k)
    # n < k: tomar todos en orden determinístico y completar ciclando con otra permutación
    order = rnd.sample(pool, k=n)
    result = list(order)
    # rellenar ciclando usando otra derivada del seed para variar el orden del ciclo
    extra_seed = seed_int + 99991
    rnd2 = random.Random(extra_seed)
    cycle = rnd2.sample(pool, k=n)
    idx = 0
    while len(result) < k:
        result.append(cycle[idx % n])
        idx += 1
    return result

# Lógica principal ----------------------------------------------
def generate_for_sign(sign: str):
    seed_int = deterministic_seed(date_str, sign, secret_salt)
    rnd = random.Random(seed_int)

    # Mood por signo (único mood por signo)
    mood = rnd.choice(MOODS)

    # States por categoría (determinístico)
    category_states = {}
    for i, cat in enumerate(CATEGORIES):
        category_states[cat] = random.Random(seed_int + i * 97).choice(CATEGORY_STATES)

    # Construir categories_obj: cada categoría obtiene sus propios tips desde su pool
    categories_obj = {}
    for i, cat in enumerate(CATEGORIES):
        # número de tips por categoría (ajustable)
        n_tips = 2

        # pool específico; si vacío, fallback a TIPS_GENERAL; si también vacío, DEFAULT_TIP
        pool = TIP_POOLS.get(cat, []) or TIPS_GENERAL or DEFAULT_TIP

        # seed derivada por categoría para selecciones determinísticas distintas
        pick_seed = deterministic_seed(date_str, sign, cat, secret_salt)
        chosen = select_deterministic_from_pool(pick_seed, pool, n_tips)
        # siempre marcar placeholders para identificar que son estáticos
        chosen = [t + " [Placeholder]" for t in chosen]

        # Texto: energy usa mood como "Estado energético", el resto muestran su state legible
        if cat == "energy":
            text = f"Estado energético: {mood}. [Placeholder]"
        else:
            # texto legible para la categoría
            text = f"{cat.capitalize()}: {category_states[cat]}. [Placeholder]"

        categories_obj[cat] = {
            "state": category_states[cat],
            "text": text,
            "tips": chosen
        }

    # Flatten tips para prompt (tomamos hasta 3 primeros tips únicos)
    flat_tips = []
    for cat in CATEGORIES:
        for t in categories_obj[cat]["tips"]:
            if t not in flat_tips:
                flat_tips.append(t)
    tips_for_ai = [t.replace(" [Placeholder]", "") for t in flat_tips[:3]] or [DEFAULT_TIP[0]]

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

    # Serializar, calcular hash, guardar atómicamente
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