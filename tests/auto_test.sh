#!/usr/bin/env bash
# =============================================================================
#  Prueba dinámica automática - IEEE/ISO/IEC 29119 (Software Testing)
# -----------------------------------------------------------------------------
#  Test item      : servicio de Búsqueda (Main.py Buscar)
#  Test type      : prueba dinámica de caja negra, basada en datos aleatorios
#  Test design    : se generan N casos (campo, operador, valor) aleatorios y se
#                   ejecuta el parser; se clasifica cada salida en:
#                     PASS  -> la consulta es válida (imprime probabilidad)
#                     WARN  -> baja probabilidad (el sistema advierte y sugiere rango)
#                     FAIL  -> error inesperado
#  Test data      : campos {Likes, Views, Duracion, Comentarios};
#                   operadores {>, <, >=, <=}; valores en [0, 2000)
#  Test result    : se vuelca TODA la corrida a tests/results.out (artefacto .out)
#  Uso            : bash tests/auto_test.sh [N]      (por defecto N=1000)
# =============================================================================
set -u

HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$HERE/tests/results.out"
N="${1:-1000}"
PY="${PYTHON:-python}"
export PYTHONIOENCODING=utf-8

FIELDS=(Likes Views Duracion Comentarios)
OPS=(">" "<" ">=" "<=")

: > "$OUT"
echo "==== IEEE 29119 - Prueba dinámica automática ====" >> "$OUT"
echo "Fecha: $(date)" >> "$OUT"
echo "Casos de prueba: N=$N sobre el servicio 'Buscar'" >> "$OUT"
echo "=================================================" >> "$OUT"

pass=0; warn=0; fail=0
for ((i=1; i<=N; i++)); do
  f=${FIELDS[$RANDOM % ${#FIELDS[@]}]}
  o=${OPS[$RANDOM % ${#OPS[@]}]}
  v=$(( (RANDOM * RANDOM) % 2000 ))
  q="$f $o $v"
  echo "" >> "$OUT"
  echo "---- Caso $i / $N : Buscar --Query \"$q\" ----" >> "$OUT"
  res="$("$PY" "$HERE/Main.py" Buscar --Query "$q" --Path "$HERE/data" 2>&1)"
  echo "$res" >> "$OUT"
  if   echo "$res" | grep -q "La probabilidad de tu búsqueda es"; then warn=$((warn+1))
  elif echo "$res" | grep -q "Probabilidad de la búsqueda";       then pass=$((pass+1))
  else fail=$((fail+1)); fi
  if (( i % 100 == 0 )); then echo "[auto_test] $i/$N (PASS=$pass WARN=$warn FAIL=$fail)"; fi
done

summary="==== Resumen: PASS=$pass  WARN=$warn  FAIL=$fail  TOTAL=$N ===="
echo "" >> "$OUT"; echo "$summary" >> "$OUT"
echo "$summary"
