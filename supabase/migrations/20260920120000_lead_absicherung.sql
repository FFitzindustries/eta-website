-- ETA CRM: Lead-Erfassung absichern
--
-- Vorher schrieb die Website mit dem publishable Key direkt nach
-- public.contacts. Die Policy contacts_anon_insert erlaubte das jedem, der den
-- Key aus dem Quelltext liest (with check (true), also ohne jede Bedingung).
-- Ab jetzt laeuft jede Anfrage ueber die Vercel Function /api/lead, die mit dem
-- Service-Role-Key schreibt. Der Service-Role-Key umgeht RLS, deshalb kann der
-- offene Schreibweg fuer anon ersatzlos entfallen.
--
-- REIHENFOLGE BEIM LIVEGANG (siehe LIESMICH-lead.md):
--   1. Function deployen und testen
--   2. ERST DANN diese Migration einspielen
-- Andersherum ist das Formular in der Zwischenzeit kaputt.

-- ------------------------------------------------- offener Schreibweg entfernen
drop policy if exists contacts_anon_insert on public.contacts;

-- ------------------------------------------------------------ neue Spalten
-- Welcher Einwilligungstext stand beim Absenden auf der Seite. Wird spaeter
-- gebraucht, um belegen zu koennen, wozu genau eingewilligt wurde.
alter table public.contacts
  add column if not exists einwilligungstext_version text;

-- Von welcher Seite kam die Anfrage (z. B. die Behandlungsseite mit dem
-- Mini-Formular). Hilft bei der Frage, welche Behandlungen tatsaechlich ziehen.
alter table public.contacts
  add column if not exists quelle_url text;

comment on column public.contacts.einwilligungstext_version is
  'Version des Einwilligungstextes, dem beim Absenden zugestimmt wurde (z. B. v1).';
comment on column public.contacts.quelle_url is
  'URL der Seite, von der die Anfrage abgeschickt wurde.';

-- ------------------------------------------------------- Laengenbegrenzungen
-- Die Function kuerzt bereits, die Datenbank zieht die Grenze aber selbst noch
-- einmal – falls je ein anderer Weg nach contacts schreibt.
-- NOT VALID: bestehende Zeilen werden nicht geprueft, damit die Migration auch
-- dann durchlaeuft, wenn frueher etwas Laengeres gespeichert wurde. Sobald die
-- Altdaten geprueft sind, kann die Constraint mit
--   alter table public.contacts validate constraint contacts_nachricht_laenge;
-- nachtraeglich bestaetigt werden.
alter table public.contacts
  drop constraint if exists contacts_nachricht_laenge;
alter table public.contacts
  add constraint contacts_nachricht_laenge
  check (nachricht is null or char_length(nachricht) <= 4000) not valid;

alter table public.contacts
  drop constraint if exists contacts_quelle_url_laenge;
alter table public.contacts
  add constraint contacts_quelle_url_laenge
  check (quelle_url is null or char_length(quelle_url) <= 500) not valid;

alter table public.contacts
  drop constraint if exists contacts_einwilligungstext_version_laenge;
alter table public.contacts
  add constraint contacts_einwilligungstext_version_laenge
  check (einwilligungstext_version is null or char_length(einwilligungstext_version) <= 20) not valid;
