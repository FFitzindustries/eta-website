# Lead-Erfassung: Umgebungsvariablen und Livegang

Das Anfrage-Formular schreibt nicht mehr aus dem Browser in die Datenbank.
Jede Anfrage läuft jetzt über die Vercel Function `api/lead.mjs`. Der
Datenbank-Schlüssel liegt ausschliesslich auf dem Server.

**Warum der Umbau:** Bisher stand der Supabase-Schlüssel im Quelltext von
`main.js`, und die Regel `contacts_anon_insert ... with check (true)` liess
damit jeden beliebig viele Einträge anlegen. Wer die Seite öffnete, konnte die
Tabelle vollschreiben.

---

## 1. Umgebungsvariablen in Vercel

Projekt → Settings → Environment Variables. Für **Production** *und*
**Preview** setzen, sonst funktioniert das Formular in der Vorschau nicht.

### Pflicht

| Name | Wert | Wozu |
| --- | --- | --- |
| `ETA_SUPABASE_URL` | `https://awhqwahhdhlbdgmrmfxv.supabase.co` | Adresse des Supabase-Projekts `eta-agency`. Alternativ `SUPABASE_URL` – die Function nimmt `ETA_SUPABASE_URL` zuerst und fällt auf `SUPABASE_URL` zurück. |
| `SUPABASE_SERVICE_ROLE_KEY` | der Service-Role-Key | Schreibt nach `public.contacts`. Zu finden unter Supabase → Project Settings → API → `service_role`. |

> **Der Service-Role-Key umgeht sämtliche RLS-Regeln.** Er gehört nie in eine
> Datei im Repo, nie in den Browser und nie in eine Chat-Nachricht. Nur ins
> Vercel-Formular tippen. Falls er je irgendwo auftaucht: in Supabase unter
> Project Settings → API neu erzeugen.

### Optional

| Name | Wert | Wirkung wenn nicht gesetzt |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Token vom BotFather | Keine Benachrichtigung. Der Lead wird trotzdem gespeichert. |
| `TELEGRAM_CHAT_ID` | Chat- oder Gruppen-ID | dito – die Benachrichtigung braucht **beide** Werte. |
| `TURNSTILE_SECRET` | Secret Key von Cloudflare Turnstile | Die Spam-Prüfung wird übersprungen. Ohne Cloudflare-Konto läuft alles ganz normal. |

Zur Telegram-Benachrichtigung: Sie ist in `try/catch` gekapselt und bricht nach
vier Sekunden ab. Ein Fehler dort kann einen Lead nicht verlieren.

Zu Turnstile: Der serverseitige Teil ist fertig. Sobald `TURNSTILE_SECRET`
gesetzt wird, greift die Prüfung sofort – **dann muss aber auch das Widget in
die Formulare eingebaut werden** (`scripts/build_site.py`, Feldname
`cf-turnstile-response`), sonst lehnt die Function jede Anfrage ab. Also
entweder beides oder keines.

---

## 2. Reihenfolge beim Livegang

Die Reihenfolge ist wichtig. Die Migration entfernt den alten Schreibweg – wer
sie zu früh einspielt, legt das Formular lahm, bis die Function läuft.

**Schritt 1 – Function deployen.**
Den aktuellen Stand nach Vercel bringen (Push auf `main` oder `vercel --prod`).
Dabei entstehen aus `static/` und `data/` die Seiten in `docs/`, und Vercel
erkennt `api/lead.mjs` von allein. Eine `package.json` braucht es nicht, die
Function hat keine Abhängigkeiten. Vor dem Deploy prüfen:

    python3 scripts/build_site.py
    grep -c "name=\"website\"" docs/kontakt.html      # muss 1 sein
    grep -c "supabase" docs/assets/js/main.js         # muss 0 sein

**Schritt 2 – testen, bevor die Migration kommt.**
Auf der Live- oder Preview-Seite eine echte Testanfrage abschicken und danach
in Supabase im Table Editor nachsehen, ob unter `contacts` eine neue Zeile
steht und unter `leads` der zugehörige Eintrag in Stufe 1.

Gegenprobe ohne Browser:

    curl -i -X POST https://<domain>/api/lead \
      -H 'Content-Type: application/json' \
      -d '{"email":"test@example.com","telefon":"+41 79 000 00 00","einwilligung":"ja","name":"Test Test"}'

Erwartet: `201` und `{"ok":true,"id":"..."}`.

Zwei Proben, die fehlschlagen müssen:

    # ohne Einwilligung -> 400
    curl -s -X POST https://<domain>/api/lead -H 'Content-Type: application/json' \
      -d '{"email":"test@example.com","telefon":"+41 79 000 00 00"}'

    # Honigtopf gefüllt -> 200, aber es entsteht KEINE Zeile in contacts
    curl -s -X POST https://<domain>/api/lead -H 'Content-Type: application/json' \
      -d '{"email":"bot@example.com","telefon":"+41 79 000 00 00","einwilligung":"ja","website":"http://spam.test"}'

Beim zweiten Fall danach in Supabase nachsehen: `bot@example.com` darf dort
nicht auftauchen.

In dieser Phase schreibt die Function noch ohne die Spalten `quelle_url` und
`einwilligungstext_version` – sie merkt, dass es sie noch nicht gibt, und
wiederholt den Schreibvorgang ohne diese Felder. Der Lead geht nicht verloren,
nur die Herkunfts-URL fehlt noch.

**Schritt 3 – erst jetzt die Migration einspielen.**

    supabase/migrations/20260920120000_lead_absicherung.sql

Über Supabase → SQL Editor einfügen und ausführen, oder mit der CLI
(`supabase db push`). Die Migration entfernt `contacts_anon_insert`, ergänzt
`einwilligungstext_version` und `quelle_url` und begrenzt die Länge von
`nachricht` auf 4000 Zeichen.

**Schritt 4 – nachkontrollieren.**
Noch eine Testanfrage abschicken. Jetzt muss in der neuen Zeile auch
`quelle_url` gefüllt sein und `einwilligungstext_version` auf `v1` stehen. Die
Testzeilen anschliessend löschen (in `contacts`; die zugehörigen `leads`
verschwinden per `on delete cascade` mit).

**Schritt 5 – den alten Schlüssel aus der Welt schaffen.**
Der bisherige publishable Key steht in der Git-Historie und ist damit nicht
geheim. Er kann nach dem Umbau nichts mehr schreiben (die Policy ist weg), aber
sauber ist es, ihn in Supabase zu rotieren.

---

## 3. Was die Function prüft

| Prüfung | Verhalten |
| --- | --- |
| Methode | Nur `POST`, sonst `405`. |
| Honigtopf `website` | Gefüllt → `200 {"ok":true}`, aber nichts wird gespeichert. Der Bot merkt nichts. |
| Ratenbegrenzung | 5 Anfragen pro IP je 10 Minuten → sonst `429`. **Nur im Arbeitsspeicher der jeweiligen Instanz**, also nur eine grobe Bremse; Vercel betreibt mehrere Instanzen parallel. Für eine belastbare Grenze braucht es Turnstile oder einen gemeinsamen Speicher. |
| Einwilligung | Feld `einwilligung` muss gesetzt sein, sonst `400`. |
| E-Mail, Telefon | Pflicht, grobe Formatprüfung, sonst `400`. |
| Feldlängen | Werden gekürzt, nicht abgelehnt (Nachricht max. 4000 Zeichen). |
| Geburtsdatum | `TT.MM.JJJJ` → ISO. Unsinniges Datum (z. B. `31.02.1990`) landet als Rohtext in `notizen`. |
| Turnstile | Nur wenn `TURNSTILE_SECRET` gesetzt ist. |

Die Antwort ist ehrlich: Nur bei `201` zeigt das Formular eine Bestätigung. Bei
jedem Fehler erscheint eine Fehlermeldung mit WhatsApp als Ausweichweg – und
das WhatsApp-Fenster öffnet sich erst, **nachdem** gespeichert wurde.

---

## 4. Geänderte Dateien

| Datei | Was |
| --- | --- |
| `api/lead.mjs` | neu – die Function |
| `supabase/migrations/20260920120000_lead_absicherung.sql` | neu – **noch nicht eingespielt** |
| `scripts/build_site.py` | Honigtopf, `name="einwilligung"`, `einwilligung_version`, leerer Wert bei „Bitte wählen“ |
| `static/assets/css/style.css` | `.hp` (Honigtopf), `.form-status.fehler` |
| `static/assets/js/main.js` | Supabase-Schlüssel entfernt, POST auf `/api/lead`, Doppelklick-Sperre |
| `docs/` | Build-Ausgabe, entsteht aus `python3 scripts/build_site.py` – **nie von Hand ändern** |
