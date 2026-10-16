# Métricas implementadas

**VERIFIED (código):** `B` es la respuesta propia inicial, `J` el juicio sobre la solución IA y `F` la respuesta propia final al mismo problema. `pre_ai_confidence` y `post_ai_confidence` son certeza en B y F; `ai_judgment_confidence` es certeza en J. Todas usan 0–100, pero se refieren a objetos distintos. No se las intercambia. El scoring numérico acepta ±1 % relativo o 0,01 absoluto y exige unidad literal. Respuesta vacía queda faltante; no se trata como incorrecta en transiciones.

| Métrica | Denominador | Lectura |
|---|---|---|
| `physics_knowledge_score` | todos los ensayos | Fracción de B correctas; descriptor de acierto inicial, no conocimiento latente validado. |
| `final_answer_accuracy` | F observadas | Fracción de F correctas. |
| `decision_accuracy` | ensayos con IA | J correcto; duda cuenta como no acierto. |
| `abstention_rate` | ensayos con IA | J = «no seguro». |
| `error_detection_rate` / `false_rejection_rate` | IA erróneas / correctas | Rechazo acertado / rechazo falso. |
| `brier` y `confidence_gap` | J comprometidos | Calibración de la confianza **en J**, excluyendo duda. |
| `correction_score` | IA erróneas | Cadena de rechazo, categoría y valor/unidad correctos. |
| `parallel_item_accuracy` | todos los ensayos | Acierto en segundo problema del mismo procedimiento. |
| `parallel_item_after_correction_accuracy` | IA erróneas corregidas | Acierto del segundo ítem condicionado a corrección válida. |
| cuatro `*_to_*_rate` y sus `*_n` | pares B,F completos | C→I, I→C, C→C, I→I; las cuatro tasas suman 1 si hay pares. |
| `correct_to_incorrect_rate_given_initial_correct` | B correcta y F observada | Riesgo descriptivo de deterioro entre inicialmente correctas. |
| `incorrect_to_correct_rate_given_initial_incorrect` | B incorrecta y F observada | Mejora descriptiva entre inicialmente incorrectas. |
| `observed_answer_switch_rate` | pares B,F numéricos completos | Respuesta final distinta de B con tolerancia/unidad del corrector. |
| `wrong_ai_adoption_rate` / `correct_ai_adoption_rate` | A de cada veracidad, B distinta de A y F comparable | F coincide con A tras desacuerdo inicial. «Adopción» operacional, sin prueba de copia o causalidad. |
| `rair` / `rsr` | casos estrictos B≠A con F igual a B o A | Adaptación numérica de [Schemmer et al.](https://arxiv.org/html/2204.06916v1); terceros valores excluidos. |
| `mean_confidence_change` | pares de confianzas pre/post presentes | Diferencia media `post − pre` en puntos porcentuales; no es calibración ni efecto de IA. |

Las tasas vacías devuelven `null`. `complete_pair_n`, `missing_pair_n`, `final_observed_n`, `rair_eligible_n`, `rsr_eligible_n` y exclusiones de terceros/faltantes hacen visibles los denominadores. `J=duda` no elimina una transición B→F. La coincidencia numérica con IA puede deberse a cálculo propio. Un estudio causal requeriría asignación de condición y comparación sin IA; el campo `no_ai_control` existe en el modelo pero no hay flujo experimental para él. [Definiciones y casos límite](ai-influence-metrics.md), [diseño](transition-design.md).

**NOT_VERIFIED:** validez psicométrica, fiabilidad de siete ítems, aprendizaje o efecto causal. El segundo ítem no demuestra transferencia amplia ni retención.
