-- ETA CRM: initiales Schema
-- Kontakte/Leads, Pipeline, Kalender, Nachrichten (WhatsApp/E-Mail Platzhalter), Vertraege
-- Nur ein internes Team-Mitglied (Ferry) fuer den Start, RLS entsprechend restriktiv:
--   - anon (Website-Formular) darf nur neue Kontakte anlegen, sonst nichts lesen/aendern
--   - authenticated (eingeloggtes CRM-Personal) darf alles

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------- contacts
create table public.contacts (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  vorname text,
  nachname text,
  email text,
  telefon_vorwahl text,
  telefon text,
  strasse text,
  plz text,
  ort text,
  geburtsdatum date,
  sprache text not null default 'de' check (sprache in ('de','en','tr','ar')),
  quelle text not null default 'formular' check (quelle in ('formular','whatsapp','email','manuell')),
  gewuenschte_behandlung text,
  nachricht text,
  notizen text,
  dsgvo_einwilligung boolean not null default false,
  dsgvo_einwilligung_at timestamptz
);

comment on table public.contacts is 'Kontakte/Interessenten der ETA-Website (Formular, WhatsApp, manuell).';

-- ------------------------------------------------------------ pipeline_stages
create table public.pipeline_stages (
  id smallint primary key,
  key text not null unique,
  label_de text not null,
  sort_order smallint not null
);

insert into public.pipeline_stages (id, key, label_de, sort_order) values
  (1, 'neue_anfrage',        'Neue Anfrage',            10),
  (2, 'kontaktiert',         'Kontaktiert',             20),
  (3, 'beratung_terminiert', 'Beratung terminiert',     30),
  (4, 'angebot_erstellt',    'Angebot erstellt',        40),
  (5, 'anzahlung_erhalten',  'Anzahlung erhalten',      50),
  (6, 'termin_bestaetigt',   'Termin bestaetigt',       60),
  (7, 'in_istanbul',         'In Istanbul',             70),
  (8, 'abgeschlossen',       'Abgeschlossen',           80),
  (9, 'nachsorge',           'Nachsorge',               90),
  (10, 'verloren',           'Verloren / abgebrochen',  100);

-- ---------------------------------------------------------------------- leads
create table public.leads (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  contact_id uuid not null references public.contacts(id) on delete cascade,
  stage_id smallint not null default 1 references public.pipeline_stages(id),
  behandlung_kategorie text,
  behandlung_slug text,
  angebotspreis numeric(10,2),
  anzahlung_erhalten boolean not null default false,
  assigned_to text not null default 'ferry',
  notizen text
);

create index leads_contact_id_idx on public.leads(contact_id);
create index leads_stage_id_idx on public.leads(stage_id);

-- Bei jedem neuen Kontakt automatisch einen Lead in Stufe 1 anlegen
create or replace function public.create_lead_for_new_contact()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.leads (contact_id, behandlung_kategorie, stage_id)
  values (new.id, new.gewuenschte_behandlung, 1);
  return new;
end;
$$;

create trigger contacts_create_lead
  after insert on public.contacts
  for each row execute function public.create_lead_for_new_contact();

-- -------------------------------------------------------------- calendar_events
create table public.calendar_events (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  contact_id uuid references public.contacts(id) on delete set null,
  lead_id uuid references public.leads(id) on delete set null,
  titel text not null,
  beschreibung text,
  start_at timestamptz not null,
  end_at timestamptz,
  ort text,
  erstellt_von text not null default 'ferry'
);

create index calendar_events_start_at_idx on public.calendar_events(start_at);

-- ------------------------------------------------------------------- messages
-- Platzhalter-Inbox fuer WhatsApp (2chat) und E-Mail (SMTP), noch nicht live angebunden.
create table public.messages (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  contact_id uuid references public.contacts(id) on delete set null,
  channel text not null check (channel in ('whatsapp','email')),
  richtung text not null check (richtung in ('eingehend','ausgehend')),
  von text,
  an text,
  betreff text,
  inhalt text,
  external_id text,
  status text not null default 'neu'
);

create index messages_contact_id_idx on public.messages(contact_id);
create index messages_channel_idx on public.messages(channel);

-- ------------------------------------------------------------------ contracts
-- Fuer den per Link ausfuellbaren Vermittlungsvertrag (Feature "kommt noch").
create table public.contracts (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  contact_id uuid not null references public.contacts(id) on delete cascade,
  lead_id uuid references public.leads(id) on delete set null,
  token uuid not null default gen_random_uuid() unique,
  status text not null default 'erstellt' check (status in ('erstellt','versendet','ausgefuellt','signiert')),
  daten jsonb not null default '{}'::jsonb,
  agb_akzeptiert boolean not null default false,
  agb_akzeptiert_at timestamptz,
  datenschutz_akzeptiert boolean not null default false,
  datenschutz_akzeptiert_at timestamptz
);

-- updated_at automatisch nachziehen
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger contacts_set_updated_at before update on public.contacts
  for each row execute function public.set_updated_at();
create trigger leads_set_updated_at before update on public.leads
  for each row execute function public.set_updated_at();
create trigger contracts_set_updated_at before update on public.contracts
  for each row execute function public.set_updated_at();

-- ------------------------------------------------------------------------ RLS
alter table public.contacts enable row level security;
alter table public.pipeline_stages enable row level security;
alter table public.leads enable row level security;
alter table public.calendar_events enable row level security;
alter table public.messages enable row level security;
alter table public.contracts enable row level security;

-- Website-Formular (anon key): darf einen neuen Kontakt anlegen, sonst nichts.
create policy contacts_anon_insert on public.contacts
  for insert to anon
  with check (true);

-- Internes Team (eingeloggt via Supabase Auth): voller Zugriff.
create policy contacts_staff_all on public.contacts
  for all to authenticated
  using (true) with check (true);

create policy pipeline_stages_staff_read on public.pipeline_stages
  for select to authenticated
  using (true);

create policy leads_staff_all on public.leads
  for all to authenticated
  using (true) with check (true);

create policy calendar_events_staff_all on public.calendar_events
  for all to authenticated
  using (true) with check (true);

create policy messages_staff_all on public.messages
  for all to authenticated
  using (true) with check (true);

create policy contracts_staff_all on public.contracts
  for all to authenticated
  using (true) with check (true);
