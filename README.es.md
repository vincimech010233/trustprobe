# TrustProbe

**Prototipo local para estudiar cómo el alumnado evalúa y cambia respuestas de física después de ver comentarios simulados de una IA.**

[English](README.md)

TrustProbe registra la respuesta y la confianza inicial de una persona, su valoración de una respuesta preparada como si fuera de una IA, y su respuesta y confianza finales. También registra una explicación y la respuesta a un ejercicio paralelo. El prototipo usa respuestas preparadas: no se conecta a un modelo de IA ni a servicios externos.

## Estado

**Verificado como prototipo de software. No validado como herramienta educativa de medición.** Las comprobaciones sintéticas muestran cómo se comporta el programa en ciertos casos. No demuestran que TrustProbe mejore el aprendizaje, mida la confianza de forma fiable ni funcione con estudiantes reales.

## Ejecutar en local

Requiere Python 3.10 o posterior. La aplicación usa solo la biblioteca estándar de Python.

```bash
python3 -m trustprobe.web --port 8765
```

Abre <http://127.0.0.1:8765>. La base local se guarda en `var/`. No introduzcas datos personales. El proyecto no tiene cuentas ni conexión a servicios externos.

## Comprobar

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 scripts/simulate.py
python3 data/build_dataset.py  # regenera data/exercises.json; revisa el diff
```

Los ejercicios de muestra y los resultados generados son sintéticos. Consulta [`results/`](results/) y las notas de diseño y límites en [`docs/`](docs/).

## Investigación y límites

TrustProbe puede registrar cambios entre una respuesta inicial y otra posterior a comentarios simulados. Ese cambio, por sí solo, no demuestra que los comentarios lo hayan causado. Antes de sacar conclusiones educativas harían falta pruebas con estudiantes, revisión ética y evidencia de que la medición es válida.

Este repositorio incluye el prototipo, sus pruebas, ejercicios sintéticos y algunas notas de diseño. No afirma que el proyecto mejore la enseñanza ni que exista demanda comercial.
