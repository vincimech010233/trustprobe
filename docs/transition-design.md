# Diseño previo de transiciones B→F (29-09-2026)

**VERIFIED (fuente):** [Schemmer et al.](https://arxiv.org/html/2204.06916v1) calculan RAIR/RSR en decisiones iniciales y finales de clasificación, distinguiendo consejo que contradice la decisión inicial. En Física numérica una respuesta final puede ser una **tercera** opción; no se debe llamarla adopción de IA ni persistencia propia.

## Flujo definido antes de modificar código

`problema → B(valor, unidad, confianza propia pre-IA) → A(solución visible, condition) → J(veredicto, confianza en J) → F(valor, unidad, confianza propia post-IA, razón opcional) → diagnóstico/corrección → ítem paralelo inmediato`.

El servidor persistirá cada fase y marcará tiempo desde que se presentó. La solución IA sigue visible en las pantallas J y F; no se muestra veredicto ni feedback antes de F. Diagnóstico/corrección se separa para que la tarea de reconstruir no contamine la respuesta final. `J=incorrecta` y `F=valor IA` serán posibles y se registrarán como discordancia, no se forzará consistencia.

## Variables y comparabilidad

- `baseline_value/unit`, `pre_ai_confidence` (0–100 si hay respuesta), `baseline_seconds`.
- `condition∈{ai_correct,ai_incorrect,no_ai_control}` por ensayo. El flujo actual selecciona solo las dos condiciones IA; la tercera queda reservada en esquema y vocabulario, sin experimento ni interfaz de control.
- `judgment`, `ai_judgment_confidence`, `judgment_seconds`; la columna histórica `confidence` se conserva solo para migración.
- `final_value/unit`, `post_ai_confidence`, `final_reason`, `final_seconds`. Ausencia de ambos valor/unidad significa abstención; confianza propia ausente entonces es `null`. Valor/unidad parcial se rechaza.
- Diagnóstico y corrección (`category`, `correction_value/unit`, `explanation`, `diagnosis_seconds`); respuesta paralela (`transfer_*` como nombre interno legado).
- La variante IA incorrecta tendrá **valor y unidad explícitos en el banco** además del texto, para reconocer adopción sin extraer números con expresiones regulares. El emparejamiento usa la misma tolerancia y unidad exacta que el corrector; no demuestra que se haya copiado de IA.

## Estados calculables

`baseline_correct` y `final_correct` son `None` si faltan valor/unidad, si no booleanos. Solo pares completos entran en `correct_to_incorrect`, `incorrect_to_correct`, `correct_to_correct` o `incorrect_to_incorrect`; los demás quedan `unclassified_missing`. Para persistencia incorrecta se reportan por separado `F=respuesta B`, `F=respuesta IA` y `F=tercera respuesta` cuando la comparación numérica es válida. `observed_answer_switch` compara respuestas propias exactas dentro de tolerancia, con unidad. Cualquier transición observada tras IA es **asociación secuencial**, no efecto causal.

## Denominadores estrictos

- Tasas de cada transición = conteo de esa transición / pares B,F completos. Se reporta además `complete_pair_n`, `missing_pair_n` y conteos.
- `correct_to_incorrect_rate_given_initial_correct` = C→I / `#{B=correcta,F observada}`; `incorrect_to_correct_rate_given_initial_incorrect` = I→C / `#{B=incorrecta,F observada}`.
- `observed_answer_switch_rate` = `#{B,F completos y diferentes}` / `#{B,F completos con respuesta numérica válida}`.
- `wrong_ai_adoption_rate` = `#{A errónea,B≠IA,F=IA}` / `#{A errónea,B≠IA,F observada y comparable}`; análogo para IA correcta. Se excluyen confirmaciones en las que B ya coincidía con IA. El nombre «adopción» es operacional: coincidencia final tras desacuerdo, no prueba de copiar ni causalidad.
- RAIR estricto = `#{B incorrecta,A correcta,F=IA}` / `#{B incorrecta,A correcta,F∈{B,IA}}`. RSR estricto = `#{B correcta,A incorrecta,F=B}` / `#{B correcta,A incorrecta,F∈{B,IA}}`. Excluir B/F faltantes, no numéricos o una tercera respuesta; denominador cero → `null`. En el caso B incorrecta y A correcta, `F=IA` equivale a F correcta solo en el banco y tolerancia actual. Las exclusiones se cuentan. RAIR/RSR se denominan **adaptación estricta a respuesta numérica** de [Schemmer et al.](https://arxiv.org/html/2204.06916v1), no equivalencia plena con su tarea binaria.
- Dudas de J no invalidan B→F, pero se cuentan por separado. Confianza pre/post compara certeza en la **respuesta propia**, mientras `ai_judgment_confidence` se refiere al juicio sobre IA.

**NOT_VERIFIED:** validez de ítems, comportamiento de estudiantes, aprendizaje, causalidad y funcionamiento de un brazo sin IA. Las sesiones completadas antes de esta versión conservarán B/J/P; su F y nuevas métricas serán faltantes, nunca reconstruidas.
