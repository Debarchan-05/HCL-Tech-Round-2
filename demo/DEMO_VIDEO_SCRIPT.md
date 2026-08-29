# Demo Video — Recording Guide & Narration Script

**Important:** I (Claude) cannot generate spoken narration or a finished audio-voiced video —
I don't have a text-to-speech/voice capability. What I've provided instead:

1. `app_walkthrough_raw_clip.mp4` — a **real, unscripted screen recording** of the actual
   running application (36 seconds), captured automatically by driving a real browser against
   the live backend. It's silent and short — a proof that the flow works end-to-end, not a
   submission-ready video.
2. This script — a timed narration you can read aloud while screen-recording your own 3–5 minute
   walkthrough of the same app running locally (see README.md for setup — it takes ~2 minutes).

Recording your own is fast: the whole app is built and working, so you're narrating over something
that already runs correctly — no need to improvise or debug on camera.

## How to record (fastest option: OBS Studio / Windows Game Bar / QuickTime — all free)

1. Run the app locally per the README (`uvicorn` + `npm run dev`), open `localhost:5173`.
2. Start your screen recorder with microphone audio enabled.
3. Follow the script below — read it naturally, don't rush; the pacing already targets ~4 minutes.
4. Export as MP4 and upload to YouTube (unlisted) or Google Drive with link sharing on.

---

## Narration Script (~4 minutes)

**[0:00–0:20] Intro — Chat screen (empty)**
> "Hi, this is LearnPath AI — an AI-powered personalized learning path recommender, built for
> the hackathon. The idea: a learner describes their goal in plain English, and the system
> builds them a complete, explainable, prerequisite-ordered roadmap — then adapts it as they
> make progress. Let me show you the whole flow."

**[0:20–0:50] Conversational interface**
> "I'll type a real goal: 'I want to become a data scientist, I know some Python but I'm new
> to machine learning, and I have about 6 hours a week.'"
*(type the message, hit send, let the reply render)*
> "Notice it correctly picked up that I know Python — but NOT machine learning, even though I
> mentioned it, because I said I was 'new to' it. That negation handling was one of the trickier
> parts of the NLU layer — getting this wrong would corrupt every recommendation downstream."

**[0:50–1:40] Recommendations + explainability**
*(click Recommendations tab)*
> "Now it's scoring the entire course catalog against my skill gap. Each card shows a match
> percentage and the actual reasons behind it — not a black box."
*(click "Why this?" on a course)*
> "Tapping 'Why this?' gives a full explanation: what skills it covers, whether I already meet
> the prerequisites, how popular it is. This satisfies the brief's requirement that the assistant
> explain every recommendation, not just produce one."

**[1:40–2:40] Learning path / roadmap**
*(click Learning Path tab, scroll through steps)*
> "This is the generated roadmap. Behind the scenes it's running a topological sort over a
> prerequisite graph, so every course here is guaranteed to come after everything it depends
> on — you'll never be handed React before JavaScript, for example. It's grouped into milestones:
> Foundations, Core Skills, Applied Practice, and Mastery, ending in a real capstone project."
*(click "Mark completed" on the first step)*
> "Watch what happens when I mark a course complete — the path regenerates immediately. That
> skill moves from 'gap' to 'known', the hour estimate updates, and everything downstream
> re-sequences. This is the adaptive part of the brief — it's not a static plan."
*(type a question in the Q&A box, e.g. "why do I need SQL?", hit Ask)*
> "I can also just ask it questions directly — 'why do I need SQL?' — and it answers using the
> actual path context, not a generic FAQ."

**[2:40–3:30] Dashboard**
*(click Dashboard tab)*
> "Finally, the dashboard — completion percentage, hours invested versus remaining, skills
> acquired versus still needed, and a breakdown of hours by milestone stage. This is where a
> learner would check in regularly to see their progress and what's recommended next."

**[3:30–4:00] Close**
> "Under the hood, this is a FastAPI backend with a hybrid recommendation engine — skill-gap
> coverage, prerequisite readiness, level fit, and a popularity signal — plus a React frontend.
> Full source, architecture, and the AI/ML approach are in the submission's documentation and
> README. Thanks for watching."

---

## Tips
- If short on time, you can trim the intro/close and focus on Recommendations → Path → Dashboard,
  which covers the most heavily-weighted judging criteria (Functionality 25%, AI/ML 20%).
- Screen-record at 1280×800 or larger so text is legible.
- It's fine to pause/re-take sections — most recorders let you edit cuts together afterward.
