#!/usr/bin/env python3
"""
compatibles.py — versión corregida para:
 - leer compatibilidades-fijas.json con estructura {"compatibilidades": { ... }}
 - normalizar nombres (quita acentos) para que 'Géminis' coincida con 'geminis'
 - usar escala de categorías -10..10 (cada state -> -5..+5; sum -> -10..10)
 - General final sigue en 0..100: convierte -10..10 -> 0..100 antes de promediar con fixed_general
Salida: ../Daily/Compatibles/{sign}_compatibles_today.json
Ejecutar desde: horoscope-json-feed/Python/
"""
from pathlib import Path
import json, hashlib, datetime, sys, traceback, unicodedata

# ---- Config / mapas ----
SIGNS = ["aries","tauro","geminis","cancer","leo","virgo","libra","escorpio","sagitario","capricornio","acuario","piscis"]
CATEGORIES_TO_COMPARE = ["love", "friendship", "work", "energy", "creativity"]

# Nuevo mapping: cada state => -5 .. +5 (sum dará -10..+10)
STATE_SCORE = {
    "favorable": 5,
    "prometedor": 4,
    "equilibrado": 3,
    "estable": 2,
    "neutral": 0,
    "incierto": -2,
    "precaucion": -3,
    "desafiante": -4,
    "tenso": -5
}

# Paths relativos (ejecutar desde horoscope-json-feed/Python/)
BASE_DIR = Path(__file__).resolve().parent.parent
DAILY_DIR = BASE_DIR / "Daily"
COMPATIBILIDADES_FILE = BASE_DIR / "Compatibilidad" / "compatibilidades-fijas.json"
OUT_DIR = DAILY_DIR / "Compatibles"

DEFAULT_FIXED_GENERAL = 50

# ---- Helpers ----
def normalize_name(s):
    """quita acentos, baja a ascii y lower()"""
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.strip().lower()

def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def safe_write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def clamp_int_0_100(v):
    iv = int(round(v))
    if iv < 0: return 0
    if iv > 100: return 100
    return iv

# ---- Nueva función: construir mapa rápido de compatibilidades fijas ----
def build_fixed_map(compat_data):
    """
    Devuelve dict { (a,b) : value } con nombres normalizados (sin acentos, lowercase).
    Soporta:
      - dict-of-dict (como tu archivo: {"compatibilidades": { "Aries": { "Tauro": 60, ... }, ... }})
      - listas de objetos con 'a'/'b'/'general' o 'pair': [...]
      - estructuras anidadas.
    """
    pair_map = {}

    def add_pair(a, b, val):
        if a is None or b is None or val is None:
            return
        a_n = normalize_name(a)
        b_n = normalize_name(b)
        key = tuple(sorted([a_n, b_n]))
        try:
            pair_map[key] = int(round(float(val)))
        except Exception:
            # ignore non-numeric values
            return

    # If top-level dict and contains a nested dict under "compatibilidades", unwrap it
    if isinstance(compat_data, dict):
        # if there is a dedicated root key like "compatibilidades", unwrap it
        if "compatibilidades" in compat_data and isinstance(compat_data["compatibilidades"], dict):
            compat_data = compat_data["compatibilidades"]

    # If now dict-of-dict with sign keys
    if isinstance(compat_data, dict):
        for a, inner in compat_data.items():
            if isinstance(inner, dict):
                for b, v in inner.items():
                    # v can be numeric directly
                    if isinstance(v, (int, float, str)):
                        try:
                            add_pair(a, b, float(v))
                            continue
                        except Exception:
                            pass
                    # or nested dict with 'general' field
                    if isinstance(v, dict):
                        for cand in ("general","score","value"):
                            if cand in v:
                                add_pair(a, b, v[cand])
                                break
    # If it's a list: try to parse entries
    if isinstance(compat_data, list):
        for item in compat_data:
            if not isinstance(item, dict):
                continue
            a = item.get("a") or item.get("from") or item.get("sign_a")
            b = item.get("b") or item.get("to") or item.get("sign_b")
            val = None
            for cand in ("general","score","value"):
                if cand in item:
                    val = item[cand]
                    break
            if (a is None or b is None) and "pair" in item and isinstance(item["pair"], (list,tuple)) and len(item["pair"])>=2:
                a = item["pair"][0]; b = item["pair"][1]
            if a is not None and b is not None and val is not None:
                add_pair(a,b,val)
                continue
            # otherwise try recursive
            for v in item.values():
                if isinstance(v, (list, dict)):
                    sub = build_fixed_map(v)
                    pair_map.update(sub)

    return pair_map

def find_fixed_general(pair_map, a, b):
    if not pair_map:
        return DEFAULT_FIXED_GENERAL
    key = tuple(sorted([normalize_name(a), normalize_name(b)]))
    return int(pair_map.get(key, DEFAULT_FIXED_GENERAL))

# ---- Lógica de puntaje por categoría ----
def compute_category_raw(state_a, state_b):
    """
    Devuelve entero en -10..10 (sumando -5..+5 + -5..+5)
    """
    sa = STATE_SCORE.get(str(state_a).lower(), 0)
    sb = STATE_SCORE.get(str(state_b).lower(), 0)
    raw = sa + sb
    # clamp just in case
    if raw < -10: raw = -10
    if raw > 10: raw = 10
    return int(raw)

def raw_to_pct(raw):
    """Convierte raw (-10..10) a 0..100 linealmente."""
    pct = 50.0 + (raw / 10.0) * 50.0
    return clamp_int_0_100(pct)

def get_state_for_category(sign_obj: dict, category: str):
    cats = sign_obj.get("categories", {})
    cat_obj = cats.get(category, {})
    state = cat_obj.get("state")
    if state is None:
        return "neutral"
    return str(state).lower()

# ---- Loader daily (debug prints reducidos ya que pegaste fragmentos) ----
def load_all_daily():
    data = {}
    missing = []
    for s in SIGNS:
        path = DAILY_DIR / f"{s}_today.json"
        if not path.exists():
            missing.append(s)
            continue
        try:
            js = load_json(path)
            data[s] = js
        except Exception as e:
            print(f"Error leyendo {path}: {e}", file=sys.stderr)
            missing.append(s)
    return data, missing

# ---- Main ----
def main():
    print("[INFO] BASE_DIR:", BASE_DIR)
    print("[INFO] DAILY_DIR:", DAILY_DIR, "[ENCONTRADA]" if DAILY_DIR.exists() else "[NO ENCONTRADA]")
    print("[INFO] COMPATIBILIDADES_FILE:", COMPATIBILIDADES_FILE, "[ENCONTRADO]" if COMPATIBILIDADES_FILE.exists() else "[NO ENCONTRADO]")
    print("[INFO] OUT_DIR:", OUT_DIR)

    compat_raw = {}
    pair_map = {}
    if COMPATIBILIDADES_FILE.exists():
        try:
            compat_raw = load_json(COMPATIBILIDADES_FILE)
            pair_map = build_fixed_map(compat_raw)
            print(f"[DEBUG] pair_map creado con {len(pair_map)} pares. Ejemplo (hasta 10):")
            for i, (k,v) in enumerate(pair_map.items()):
                if i >= 10: break
                print("  -", k, "=>", v)
        except Exception as e:
            print("[ERROR] No pude procesar compatibilidades-fijas.json:", e, file=sys.stderr)
            compat_raw = {}
            pair_map = {}
    else:
        print("[WARN] compatibilidades-fijas.json no encontrado; usando default_general =", DEFAULT_FIXED_GENERAL, file=sys.stderr)

    daily_data, missing = load_all_daily()
    if missing:
        print("[WARN] faltan daily JSONs para:", missing, file=sys.stderr)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = []

    for sign in SIGNS:
        sign_obj = daily_data.get(sign)
        if sign_obj is None:
            print(f"[WARN] Saltando {sign}: falta daily JSON.")
            continue

        result = {"sign": sign, "generated_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z", "pairs": {}}

        for other in SIGNS:
            if other == sign:
                continue
            other_obj = daily_data.get(other)
            if other_obj is None:
                result["pairs"][other] = {"General": None, "Love": None, "Friendship": None, "Work": None, "Energy": None, "Creativity": None, "note": f"Missing daily JSON for {other}"}
                continue

            # calcular raw por categoría (-10..10)
            cat_raw = {}
            cat_pct = {}
            for cat in CATEGORIES_TO_COMPARE:
                s_a = get_state_for_category(sign_obj, cat)
                s_b = get_state_for_category(other_obj, cat)
                raw = compute_category_raw(s_a, s_b)
                pct = raw_to_pct(raw)
                cat_raw[cat.capitalize()] = raw
                cat_pct[cat.capitalize()] = pct

            # promedio porcentual de las 5 categorías (0..100)
            avg_categories_pct = sum(cat_pct[c.capitalize()] for c in CATEGORIES_TO_COMPARE) / len(CATEGORIES_TO_COMPARE)

            # fixed_general desde pair_map
            fixed_general = find_fixed_general(pair_map, sign, other)

            # formula final: ((avg_categories_pct) + fixed_general ) / 2
            general_final = int(round((avg_categories_pct + fixed_general) / 2.0))

            # construir objeto: categorías en raw (-10..10), general en 0..100
            pair_obj = {
                "General": general_final,
                "Love": cat_raw["Love"],
                "Friendship": cat_raw["Friendship"],
                "Work": cat_raw["Work"],
                "Energy": cat_raw["Energy"],
                "Creativity": cat_raw["Creativity"],
                "fixed_general_source": int(fixed_general),
                "avg_categories_pct": int(round(avg_categories_pct))
            }

            result["pairs"][other] = pair_obj

        out_path = OUT_DIR / f"{sign}_compatibles_today.json"
        safe_write_json(out_path, result)
        generated.append(out_path)
        print(f"[INFO] Archivo generado: {out_path}")

    print(f"[FIN] Generados {len(generated)} archivos en {OUT_DIR}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[FATAL] Error durante ejecución:", e, file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
