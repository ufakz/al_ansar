Al-Ansar

An agentic framework that searches real-time for problems facing muslims across the world, then performs task decomposition and then routes specific tasks to specific individuals that can help. 

- Crises Parser
- Ansar matcher
- Workspace Dashboard

Crises Parser
This is the nerve center. Three ingestion channels run in parallel: news feeds (GDELT Project for global event detection, NewsAPI for headlines, Al Jazeera + Middle East Eye RSS for regional depth), social signals (X/Twitter v2 filtered stream querying terms like "Muslim", "mosque", "refugee" combined with crisis keywords), and humanitarian feeds (Reliefweb API from the UN, OCHA alerts, and Islamic Relief situational reports). Each item hits a deduplication layer — embedding-based clustering using pgvector so the same Rafah story from 12 sources becomes one CrisisObject.
Every deduplicated event goes to Claude (claude-sonnet-4-6) with a structured extraction prompt. The output schema should be rigid: type (conflict/persecution/natural_disaster/humanitarian/economic), location with ISO country code and lat/lng centroid, severity on a 1–5 scale with reasoning, urgency (hours/days/weeks), affected_count estimated, and tags[] drawn from a controlled vocabulary (["food_insecurity", "displacement", "medical_need", "legal_aid_needed", etc]). Store this in Postgres with PostGIS for the geographic fields.

Task Decomposer
Once a CrisisObject is confirmed (severity ≥ 3 or manually escalated by a coordinator), Claude performs task decomposition via a second prompt that takes the full crisis context and returns a ranked list of TaskObjects. Each task has a required_skills[] array drawn from a controlled vocabulary that mirrors the Ansar registry's skill tags — this controlled vocabulary is the critical design decision because it's what makes matching tractable. Task types span: fundraising, logistics coordination, on-ground aid, remote research, advocacy/petition, translation, psychological support, legal aid, and medical triage. Aim for 3–8 tasks per crisis, calibrated by severity.

Ansar Matcher
The Ansar registry is a Postgres table where every helper has: skills[] (same vocabulary as tasks), location (PostGIS point), languages[], availability_hours_per_week, capacity_current (how many active tasks they can hold), and trust_tier (unverified / org-verified / background-checked). When a new task is created, the matcher runs a two-pass query: first a geospatial + skills filter (PostGIS ST_DWithin combined with array overlap on skills), then a semantic reranking pass using pgvector cosine similarity on embeddings of the task description against each candidate's profile narrative. The top 3 matches get a notification via WhatsApp (Twilio), email, and in-app alert with a 24-hour accept/decline window before cascading to the next tier.

Workspace Dashboard
Build this in Next.js 14 with Supabase Realtime for live updates. The main views are: a global crisis map (Mapbox GL JS, dots sized by severity), a Kanban task board (columns: Open → Matched → In Progress → Resolved) filterable by crisis/region/skill, an Ansar directory with trust badges and capacity indicators, and an impact metrics panel (crises responded to, tasks completed, helpers mobilized, countries covered). Coordinators get elevated permissions to manually escalate events, split or merge tasks, and override matcher suggestions. Affected communities get a lightweight submission form (Arabic/Urdu/Somali/English) to self-report situations that don't surface through automated feeds.

Tech stack
Backend: FastAPI on Python 3.12 for async performance, Celery + Redis for the task queue, Postgres (Supabase-managed) with pgvector and PostGIS extensions, Claude API for parsing/decomposition/matching, Voyage AI voyage-3-lite for ansar profile embeddings. Frontend: Next.js 14 App Router, Tailwind CSS, Supabase Auth with OAuth. Infra: Railway for the FastAPI service, Vercel for Next.js, Supabase for database + realtime. WhatsApp notifications via Twilio. Total estimated cloud cost at launch: under $100/month.


Build Phases
Phase 1 (weeks 1–4): Wire up three hardcoded data sources into a Celery beat job that runs every 15 minutes, pipe events to Claude for classification, store CrisisObjects in Postgres, and build a read-only dashboard that displays the live feed. No matching yet — coordinators manually pick tasks. This validates the signal quality of your sources.
Phase 2 (weeks 5–10): Build the Ansar onboarding flow (registration form, skill tagging, location), implement the Task Decomposer prompt chain, wire pgvector semantic matching, and launch WhatsApp/email notifications. Add the Kanban board to the dashboard. Onboard 50 beta helpers manually.
Phase 3 (weeks 11–18): Multi-language support (the submission form and notifications in Arabic, Urdu, and Somali), a trust/verification tier system (the most important trust-building feature — link an NGO ID or get vouched by two verified Ansars), a mobile PWA, and public impact reporting.
The one thing to solve before anything else

Ansar verification. A routing system that sends tasks to unverified strangers is a liability and a trust problem from day one. Build a three-tier model immediately: unverified (self-registered, can only take remote/digital tasks), org-verified (submitted proof of affiliation with a recognized Islamic organization — ISNA, Islamic Relief, local mosque committee), and trusted (vouched by two existing trusted Ansars with completed tasks). Gate on-ground and high-stakes tasks to tier 2+. Without this hierarchy, the first bad actor poisons the well for everyone.


MVP for Hackathon:

1. We will start with one data source e.g GDELT, and find how to store it.
2. We will grount it in one law/regulation etc e.g Finland, EU. We need to find how to store the law and accurately use it for grounding.
3. We will create 50 synthetic users with different skills.
4. We will populate a database with these users.
5. We will then create the matcher to match users with the current crisis.
6. We will have a simple dashboard to checkout some basic features of the Al-Ansar.

Flow:

1. We have worker that fetches for new crisis every hour and store it in our DB (for the MVP, we can just get one crisis and use it).
2. We have already created a store for the laws/regulations etc to ground the crisis in.
3. We will then use the laws/regulations to ground the crisis and ensure that there is legal support. 
4. If there is, we will then think deeply about the crisis and apply task decomposition to get the work needed and the type of people needed to solve it. 
5. Then we will have these tasks in our dashboard.
6. Then we will send notifications to the respective skilled people. (We can use Mail or Telegram, which ever is the easiet)