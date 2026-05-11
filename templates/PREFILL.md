🔧 RECORDATORIO DE HERRAMIENTAS

Antes de responder:
1. Leer /opt/data/resumen-rapido.md
2. Si hay combate: leer /opt/data/combat_state.json y usar combat_tracker.py
3. Para tiradas: usar roll.py (nunca inventar números)
4. Después de cada escena: ejecutar generate_resumen.py + campaign_manager.py save

Comandos rápidos:
- Tirada: python3 /opt/data/scripts/roll.py roll 1d20+5
- Ataque: python3 /opt/data/scripts/roll.py attack --bonus 5 --ac 14 --damage 1d8+3
- Combate: python3 /opt/data/scripts/combat_tracker.py status
- Guardar: python3 /opt/data/scripts/generate_resumen.py
- Ayuda: cat /opt/data/SYSTEM_TOOLS.md
