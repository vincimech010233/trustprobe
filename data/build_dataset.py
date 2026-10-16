"""Generate the reviewed, deterministic item bank. Run from the project root."""
import json
from pathlib import Path

WRONG_ANSWERS = {
    "K1": (240, "km/h"), "K2": (50, "m/s"), "K3": (36, "m"),
    "D1": (36, "m/s²"), "D2": (7, "m/s²"), "D3": (1, "N"),
    "E1": (18, "J"), "E2": (7.5, "J"), "E3": (200, "m/s"),
    "P1": (0.75, "kg·m/s"), "P2": (1.25, "N·s"), "P3": (4.90, "m/s"),
    "G1": (40, "N"), "G2": (6, "kg"), "G3": (150, "N/kg"),
    "C1": (48, "A"), "C2": (1.875, "Ω"), "C3": (3, "W"),
    "W1": (2.5, "m/s"), "W2": (4, "s"), "W3": (680, "m"),
}


def item(code, area, concept, prompt, value, unit, explanation, wrong, category,
         transfer_prompt, transfer_value, transfer_unit, difficulty="media"):
    wrong_value, wrong_unit = WRONG_ANSWERS[code]
    return dict(id=code, area=area, concept=concept, difficulty=difficulty,
                prompt=prompt, correct=dict(value=value, unit=unit, explanation=explanation),
                wrong=[dict(text=wrong, category=category, value=wrong_value, unit=wrong_unit)],
                transfer=dict(prompt=transfer_prompt, value=transfer_value, unit=transfer_unit),
                solution=explanation)


ITEMS = [
    item("K1", "cinemática", "velocidad media", "Un coche recorre 120 km en 2 h. ¿Velocidad media?", 60, "km/h", "v=d/t=120/2=60 km/h.", "v=120×2=240 km/h.", "formula", "Otro coche recorre 150 km en 3 h. ¿Velocidad media?", 50, "km/h", "baja"),
    item("K2", "cinemática", "aceleración constante", "Desde reposo, un móvil acelera a 2 m/s² durante 5 s. ¿Velocidad final?", 10, "m/s", "v=v0+at=0+2×5=10 m/s.", "v=at²=2×25=50 m/s.", "formula", "Desde reposo, a=3 m/s² durante 4 s. ¿Velocidad final?", 12, "m/s"),
    item("K3", "cinemática", "desplazamiento acelerado", "Desde reposo, a=4 m/s² durante 3 s. ¿Desplazamiento?", 18, "m", "x=½at²=½×4×9=18 m.", "x=at²=4×9=36 m.", "formula", "Desde reposo, a=2 m/s² durante 4 s. ¿Desplazamiento?", 16, "m"),
    item("D1", "dinámica", "segunda ley de Newton", "Fuerza neta de 12 N sobre masa de 3 kg. ¿Aceleración?", 4, "m/s²", "a=F/m=12/3=4 m/s².", "a=Fm=12×3=36 m/s².", "relacion_invertida", "Fuerza neta de 20 N sobre 5 kg. ¿Aceleración?", 4, "m/s²"),
    item("D2", "dinámica", "fuerza neta", "Sobre 2 kg actúan 10 N a la derecha y 4 N a la izquierda. ¿Aceleración hacia la derecha?", 3, "m/s²", "F_neta=10−4=6 N; a=6/2=3 m/s².", "Las fuerzas se suman: a=(10+4)/2=7 m/s².", "signo", "Sobre 4 kg actúan 20 N derecha y 8 N izquierda. ¿Aceleración hacia la derecha?", 3, "m/s²"),
    item("D3", "dinámica", "rozamiento cinético", "Bloque sobre plano horizontal: μ=0,2, m=5 kg, g=10 m/s². ¿Módulo de rozamiento?", 10, "N", "N=mg=50 N; F_r=μN=10 N.", "F_r=μm=0,2×5=1 N; g no interviene.", "supuesto_invalido", "μ=0,3, m=4 kg, g=10 m/s². ¿Rozamiento?", 12, "N"),
    item("E1", "energía", "energía cinética", "Masa 2 kg a 3 m/s. ¿Energía cinética?", 9, "J", "E_c=½mv²=½×2×9=9 J.", "E_c=mv²=2×9=18 J.", "formula", "Masa 4 kg a 2 m/s. ¿Energía cinética?", 8, "J"),
    item("E2", "energía", "energía potencial gravitatoria", "Masa 3 kg a 4 m sobre referencia; g=10 m/s². ¿Energía potencial?", 120, "J", "E_p=mgh=3×10×4=120 J.", "E_p=mg/h=3×10/4=7,5 J.", "relacion_invertida", "Masa 2 kg a 5 m; g=10 m/s². ¿Energía potencial?", 100, "J"),
    item("E3", "energía", "conservación de energía", "Cuerpo cae sin rozamiento desde 20 m; g=10 m/s². ¿Rapidez al llegar abajo?", 20, "m/s", "mgh=½mv²; v=√(2gh)=√400=20 m/s.", "v=gh=200 m/s porque toda la altura se convierte directamente en velocidad.", "conservacion", "Cae sin rozamiento desde 5 m; g=10 m/s². ¿Rapidez abajo?", 10, "m/s"),
    item("P1", "cantidad de movimiento", "momento lineal", "Masa 3 kg se mueve a 4 m/s. ¿Momento lineal en esa dirección?", 12, "kg·m/s", "p=mv=3×4=12 kg·m/s.", "p=m/v=3/4=0,75 kg·m/s.", "relacion_invertida", "Masa 5 kg a 2 m/s. ¿Momento lineal?", 10, "kg·m/s"),
    item("P2", "cantidad de movimiento", "impulso", "Fuerza constante de 5 N durante 4 s. ¿Impulso?", 20, "N·s", "J=FΔt=5×4=20 N·s.", "J=F/Δt=5/4=1,25 N·s.", "formula", "Fuerza de 6 N durante 3 s. ¿Impulso?", 18, "N·s"),
    item("P3", "cantidad de movimiento", "choque inelástico", "Masa 2 kg a 6 m/s choca con masa 1 kg quieta; quedan unidas. ¿Velocidad final?", 4, "m/s", "Se conserva p: (2×6+1×0)/(2+1)=4 m/s.", "Se conserva la energía cinética: v=√(2×6²/3)=√24≈4,90 m/s.", "conservacion", "Masa 3 kg a 4 m/s choca con 1 kg quieta y quedan unidas. ¿Velocidad final?", 3, "m/s"),
    item("G1", "gravitación", "ley inversa al cuadrado", "A distancia r una fuerza gravitatoria es 80 N. ¿Fuerza a 2r?", 20, "N", "F∝1/r²; 80/4=20 N.", "Al duplicar r la fuerza se reduce a la mitad: 40 N.", "relacion_invertida", "Si a r la fuerza es 90 N, ¿fuerza a 3r?", 10, "N"),
    item("G2", "gravitación", "peso", "Masa 6 kg donde g=10 m/s². ¿Peso?", 60, "N", "P=mg=6×10=60 N.", "El peso es 6 kg porque peso y masa son lo mismo.", "unidades", "Masa 8 kg con g=10 m/s². ¿Peso?", 80, "N"),
    item("G3", "gravitación", "campo gravitatorio", "Fuerza gravitatoria de 30 N sobre masa de prueba de 5 kg. ¿Campo g?", 6, "N/kg", "g=F/m=30/5=6 N/kg.", "g=Fm=150 N/kg.", "relacion_invertida", "Fuerza 40 N sobre 8 kg. ¿Campo g?", 5, "N/kg"),
    item("C1", "electricidad", "ley de Ohm", "Resistencia de 4 Ω con tensión de 12 V. ¿Corriente?", 3, "A", "I=V/R=12/4=3 A.", "I=VR=12×4=48 A.", "relacion_invertida", "Resistencia 5 Ω con 20 V. ¿Corriente?", 4, "A"),
    item("C2", "electricidad", "resistencias en serie", "Dos resistencias de 3 Ω y 5 Ω en serie. ¿Resistencia equivalente?", 8, "Ω", "En serie, R_eq=3+5=8 Ω.", "R_eq=1/(1/3+1/5)=1,875 Ω: se suman inversas en serie.", "formula", "Resistencias 4 Ω y 6 Ω en serie. ¿R_eq?", 10, "Ω"),
    item("C3", "electricidad", "potencia eléctrica", "Dispositivo con 6 V y 2 A. ¿Potencia?", 12, "W", "P=VI=6×2=12 W.", "P=V/I=6/2=3 W.", "formula", "Dispositivo con 10 V y 3 A. ¿Potencia?", 30, "W"),
    item("W1", "ondas", "relación onda frecuencia", "Onda de frecuencia 5 Hz y longitud 2 m. ¿Velocidad?", 10, "m/s", "v=fλ=5×2=10 m/s.", "v=f/λ=5/2=2,5 m/s.", "relacion_invertida", "Frecuencia 4 Hz y longitud 3 m. ¿Velocidad?", 12, "m/s"),
    item("W2", "ondas", "periodo y frecuencia", "Onda de frecuencia 4 Hz. ¿Periodo?", 0.25, "s", "T=1/f=1/4=0,25 s.", "T=f=4 s porque ambos indican ritmo de oscilación.", "relacion_invertida", "Frecuencia 2 Hz. ¿Periodo?", 0.5, "s"),
    item("W3", "ondas", "eco", "Eco tarda 2 s en ir y volver. Velocidad del sonido 340 m/s. ¿Distancia al reflector?", 340, "m", "d=vt/2=340×2/2=340 m.", "d=vt=340×2=680 m; todo el tiempo es de ida.", "supuesto_invalido", "Eco tarda 3 s ida y vuelta; v=300 m/s. ¿Distancia al reflector?", 450, "m"),
]


if __name__ == "__main__":
    target = Path(__file__).with_name("exercises.json")
    target.write_text(json.dumps(ITEMS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(ITEMS)} items -> {target}")
