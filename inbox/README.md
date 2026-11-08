# 📥 Kids' Own Stories — Audio & Transcript Inbox

Questo folder raccoglie i messaggi vocali grezzi e le sbobinature delle storie inviate via Telegram o registrate al volo da Alessandro e Sebastian, in attesa di essere elaborate e pubblicate con illustrazioni, video e audiolibri da computer.

## 🔄 Flusso di Lavoro (Intake Workflow)
1. **Intake da Mobile / Telegram:** L'agente AI (Ermete) salva l'audio (`.ogg` e `.mp3`) in `inbox/<YYYY-MM-DD>-<autore>-<slug>/`, sbobina il testo fedele in `transcript.md` e apre una GitHub Issue ("gita biscio") sul repository con label `story-intake`.
2. **Elaborazione da Computer:** Riccardo (o l'agente via workstation) crea le illustrazioni 16:9, il film da 40s, gli audiolibri e aggiorna `stories.yaml`.
3. **Completamento & Archiviazione:** La cartella viene promossa in `stories/<autore>/<slug>/` e l'Issue viene chiusa!
