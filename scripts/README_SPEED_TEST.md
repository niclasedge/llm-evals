# 128k Token Speed Test

Dieses Skript führt einen Speed-Test mit 128k Token durch und vergleicht die Performance von Ollama vs MLX-LM mit dem gpt-oss Modell.

## Überblick

Das Speed-Test-System besteht aus mehreren Komponenten:

1. **Token-Generator**: Erstellt ~128k Token Content aus der Simon Willison LLM Archiv-Datei
2. **Ollama Client**: Testet gpt-oss über Ollama API
3. **MLX Client**: Testet gpt-oss über MLX-LM (Server + Direct Mode)
4. **Performance Vergleich**: Analysiert Response-Zeiten und Durchsatz

## Voraussetzungen

### System Requirements
- macOS mit Apple Silicon (für MLX-LM)
- Python 3.8+
- Ollama installiert
- Mindestens 16GB RAM (empfohlen: 32GB für große Modelle)

### Software Installation

```bash
# 1. MLX-LM installieren
pip install mlx-lm

# 2. Ollama installieren (falls noch nicht vorhanden)
curl -fsSL https://ollama.ai/install.sh | sh
# oder: brew install ollama

# 3. Ollama starten
ollama serve
```

## Setup und Ausführung

### 1. Automatisches Setup

```bash
# Setup MLX-LM mit gpt-oss Modell
python scripts/setup_mlx_gpt_oss.py
```

Das Setup-Skript:
- Installiert MLX-LM falls nötig
- Lädt das gpt-oss Modell herunter
- Startet MLX-LM Server (falls möglich)
- Testet Ollama gpt-oss Setup
- Führt Basis-Tests durch

### 2. Speed-Test ausführen

```bash
# Standard Speed-Test (3 Iterationen)
python scripts/speed_test_128k_tokens.py

# Mit benutzerdefinierten Parametern
python scripts/speed_test_128k_tokens.py --iterations 5 --output results.json

# Mit anderer Quelldatei
python scripts/speed_test_128k_tokens.py --source-file andere_datei.md
```

### 3. Makefile Targets

```bash
# Setup
make setup-mlx-gpt-oss

# Speed-Tests
make test-speed-128k              # Standard Test
make test-speed-128k-custom       # Interaktiver Test mit Parametern
```

## Modell-Konfiguration

### Unterstützte gpt-oss Modelle

**MLX-LM kompatible Modelle:**
- `halley-ai/gpt-oss-20b-MLX-5bit-gs32` (Standard, ~12GB)
- `halley-ai/gpt-oss-20b-MLX-4bit-gs32` (~10GB)
- `halley-ai/gpt-oss-120b-MLX-8bit-gs32` (~120GB, nur für High-End Systeme)

**Ollama Modelle:**
- `gpt-oss` (falls verfügbar im Ollama Registry)
- Alternative: Andere kompatible Modelle für Vergleichstests

### Modell-Auswahl ändern

```python
# Im Speed-Test-Skript
mlx_client = MLXClient("halley-ai/gpt-oss-20b-MLX-4bit-gs32")
ollama_client = OllamaClient()  # Verwendet "gpt-oss" als Standard
```

## Test-Konfiguration

### Token-Generierung

Das Skript generiert automatisch ~128k Token durch:
1. Laden der Simon Willison LLM Archiv-Datei (~1.6k Wörter)
2. Wiederholung des Inhalts bis 128k Token erreicht sind
3. Hinzufügung von Iterationsmarkern für Struktur

### Test-Parameter

```python
# Anpassbare Parameter
iterations = 3              # Anzahl Test-Durchläufe
target_tokens = 128_000     # Ziel Token-Anzahl
max_response_tokens = 100   # Begrenzte Antwort für Speed-Test
temperature = 0.1           # Niedrige Temperatur für Konsistenz
```

## Ergebnisse und Metriken

### Gemessene Werte

- **Response Time**: Zeit für komplette Antwort-Generierung
- **Tokens per Second**: Durchsatz-Berechnung
- **Success Rate**: Erfolgsquote der Requests
- **Memory Usage**: Speicherverbrauch (wenn verfügbar)

### Ausgabe-Format

```json
{
  "test_config": {
    "iterations": 3,
    "content_tokens": 128000,
    "prompt_tokens": 128100
  },
  "ollama_results": [...],
  "mlx_results": [...],
  "comparison": {
    "ollama": {
      "mean_time": 45.2,
      "median_time": 44.8,
      "success_rate": 1.0
    },
    "mlx": {
      "mean_time": 32.1,
      "median_time": 31.9,
      "success_rate": 1.0
    },
    "relative_performance": {
      "mlx_speedup": 1.41,
      "mlx_faster": true,
      "performance_difference_pct": 29.0
    }
  }
}
```

## Troubleshooting

### Häufige Probleme

**1. MLX-LM Modell nicht gefunden**
```bash
# Lösung: Modell manuell herunterladen
python -c "from mlx_lm import load; load('halley-ai/gpt-oss-20b-MLX-5bit-gs32')"
```

**2. Ollama gpt-oss nicht verfügbar**
```bash
# Alternative: Anderes Modell verwenden
ollama pull llama3.3:8b
# Dann im Skript: OllamaClient() mit anderem Modell
```

**3. Speicher-Probleme**
```bash
# Kleineres Modell verwenden
python scripts/speed_test_128k_tokens.py --model halley-ai/gpt-oss-20b-MLX-4bit-gs32

# Oder Token-Anzahl reduzieren (für Tests)
# Im Skript: target_tokens = 64_000
```

**4. MLX Server startet nicht**
```bash
# Direct Mode verwenden (automatisches Fallback)
# Das Skript erkennt Server-Probleme und wechselt automatisch zu Direct Mode
```

### Debug-Modus

```bash
# Verbose Ausgabe
export LOG_LEVEL=DEBUG
python scripts/speed_test_128k_tokens.py

# Einzelne Komponenten testen
python -c "from scripts.speed_test_128k_tokens import TokenCounter; print(TokenCounter.count_tokens('test'))"
```

## Performance-Optimierung

### MLX-LM Optimierungen

```bash
# Speicher-Limit erhöhen (macOS 15+)
sudo sysctl iogpu.wired_limit_mb=16384

# Quantisierung für bessere Performance
python -m mlx_lm.convert --hf-path openai/gpt-oss-20b -q --upload-repo my-gpt-oss-4bit
```

### Ollama Optimierungen

```bash
# Ollama Konfiguration
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_FLASH_ATTENTION=1
```

## Erweiterte Nutzung

### Batch-Tests

```bash
# Mehrere Modelle testen
for model in "halley-ai/gpt-oss-20b-MLX-4bit-gs32" "halley-ai/gpt-oss-20b-MLX-5bit-gs32"; do
    python scripts/speed_test_128k_tokens.py --model $model --output "results_${model//\//_}.json"
done
```

### Integration in CI/CD

```yaml
# GitHub Actions Beispiel
- name: Run Speed Test
  run: |
    python scripts/setup_mlx_gpt_oss.py
    python scripts/speed_test_128k_tokens.py --iterations 1 --output ci_results.json
```

## Weitere Informationen

- **MLX-LM Dokumentation**: https://github.com/ml-explore/mlx-lm
- **Ollama Dokumentation**: https://ollama.ai/docs
- **gpt-oss Modelle**: https://huggingface.co/halley-ai
- **Simon Willison LLM CLI**: https://llm.datasette.io/

## Support

Bei Problemen oder Fragen:
1. Prüfen Sie die Troubleshooting-Sektion
2. Überprüfen Sie die Logs in `logs/`
3. Testen Sie einzelne Komponenten isoliert
4. Erstellen Sie ein Issue mit detaillierten Logs
