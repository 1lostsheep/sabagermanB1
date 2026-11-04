# sabagermanB1Saba's German B1 Coach — App Plan
4 Nov 2026 · @Pascal Schmitz
Goal and deadline
Saba can apply for citizenship from April 2027 through the spouse route (§ 9 StAG). She has already passed the Einbürgerungstest, so the only missing piece is a German B1 certificate. The app exists to get her there.
• Spouse route: 3 years of lawful residence in Germany and at least 2 years of marriage to a German citizen (§ 9 StAG). Living here since April 2024 means 3 years in April 2027. Paz is a German citizen, so this route applies.
• Not affected by the 2025 change: the 3-year "Turbo" route that was abolished in October 2025 was a separate rule needing C1 (The Local). The spouse route still stands.
• Language: B1 is required (migrando). A DTZ certificate at B1 counts.
• Einbürgerungstest: already passed. Nothing more to do here.
Honest timeline. Going from below A2 to a B1 pass usually takes several hundred hours of study. At 60–90 minutes a day, 6 days a week, Saba gets about 140–180 hours by March 2027. That is enough to reach the exam if she is consistent, and April 2027 is the target. It is the earliest date, not a deadline: if she needs longer, she takes the DTZ later and applies then. Nothing is lost by applying a few months later.
To check with BAMF / the Ausländerbehörde: whether Saba can still get a funded repeat course or a free DTZ sitting, given that she has already done two integration courses.
Saba as a learner, and what that means for the app
Saba learns best from pictures, sound and repetition, not grammar tables. So the app teaches German the way it is used in everyday life in Mönchengladbach, with English as the main help language and Amharic hints on tap.
What we know
What the app does about it
Schooling to grade 10, in Amharic
No grammar jargon. "Verb goes to position 2" shown as coloured blocks, not "V2 word order".
English learned from age 26, about B1
Short, simple English (A2 level). Every instruction also has an icon.
Mother tongue Amharic, different script
Tap-to-see Amharic hint for hard words and rules. Never on by default, so German stays the focus.
Not very academic; visual learner
Every new word comes with a picture and audio. Big buttons, few words on screen, one task at a time.
Failed DTZ below A2 once; may feel discouraged
Small daily wins, visible progress (streak, "words I know" counter), praise for effort. No red crosses; "try again" instead.
Lives in Germany with family
Topics from her real life: school letters for the children, doctor, Jobcenter, landlord, shopping, neighbours.
Design rules
1. One screen = one task. Never more than about 5 new words in a lesson.
2. Listen first, then speak, then read, then write.
3. Everything she hears can be slowed down and repeated.
4. Mistakes feed tomorrow's review automatically (spaced repetition).
5. The app speaks to her by name and keeps the tone warm and patient.
What the DTZ tests, and what the app must train
Speaking is the one part Saba can never skip: under the rules in force since 1 November 2026, she needs B1 in Speaking, B1 in one other area, and at least A2 in the third (migrando, 20 Oct 2026). Before, the third area could be anything; now a blank or very weak Writing paper fails the whole exam.
DTZ part
Format (approximate)
What the app trains
Speaking
About 16 min, in a pair with another candidate. 1: introduce yourself. 2: describe a picture and talk about your own experience. 3: plan something together (e.g. a party, a visit).
Daily speaking with an AI partner by voice; ready-made answers for "über mich"; 30 picture cards; 20 "let's plan" role plays.
Listening
About 25 min. Announcements, phone messages, radio, short conversations.
Daily 5-minute listening with slow and normal speed, then multiple-choice like the exam.
Reading
About 45 min. Signs, adverts, letters, forms, short texts. Listening + Reading = 45 questions.
Real-life texts: school letters, Jobcenter, doctor, rental, shop flyers.
Writing
About 30 min. One letter or email (choose one of two), covering 4 given points.
A letter "recipe": greeting, reason, 4 points, closing. 15 model letters to learn by heart, then fill-in, then free writing marked by AI.
The exact parts and timings should be checked against the official g.a.s.t. DTZ model test, which the app's monthly mock exam should copy.
Strategy: aim for B1 in Speaking and Writing (both very trainable with templates), and at least A2 in Listening + Reading. That passes under the new rule even if reading stays her weakest area.
How the app is built
The app is a small local web app on the Linux laptop that opens full-screen in the browser like a normal program, so Saba never sees a terminal. Claude Code is the tool Paz uses to build it and to refresh its content; Saba only uses the app.
Most of the daily work (flashcards, listening, reading, real-life tasks) runs from content prepared in advance, so it works offline and costs nothing. The app calls Claude over the internet only for the three things that need a live tutor: speaking practice, marking her letters, and the monthly check. Her voice is turned into text, and German answers into speech, by free open-source models on the laptop itself. The same setup would run on Windows if needed.
Daily lesson and monthly check
Each day is about 75 minutes, 6 days a week, split into two sittings so it fits around family life. The app builds the day's lesson itself; Saba only presses Start.
Block
Minutes
What she does
1. Review
10
Flashcards with picture + audio. Yesterday's mistakes come back first.
2. New words
10
5 words or phrases on today's life topic, each with a picture, audio and an Amharic hint on tap.
3. Listening
10
One short exam-style recording, slow then normal speed, then 2–3 questions.
4. Speaking
15
Talks by microphone with the AI partner: "about me", a picture card, or planning something. Gets 2–3 friendly corrections.
5. Writing or Reading
20
Alternating days: a letter (template first, then free) marked by AI, or a real-life text with questions.
6. Real-life task
5
One small real task: read a school note, fill in a form, or answer a short message.
Break point
—
Blocks 1–3 in the morning, 4–6 later in the day.
Weekly: Saturday is a 20-minute mini-test of the week's words and one letter. Sunday is free. Paz gets a short summary each week: time studied, words known, letters written, weak spots.
Monthly (first Saturday): a full mock DTZ in the app, about 2 hours, in the real order and timing. The AI scores each part against the B1 criteria and estimates a level per area (below A2 / A2 / B1). It then rewrites the next month's plan: more time to the weakest area, harder texts where she is strong. A one-page report shows the trend since the start, so she sees her progress.
Day 1: a placement test of about 45 minutes (vocabulary pictures, short listening, simple reading, "tell me about yourself", a 3-sentence note). This sets the starting level and the first month's plan.
Roadmap to April 2027
The plan has four phases and two checkpoints. The real exam is only booked once the mock DTZ shows she can pass.
If Gate 2 is missed at the end of February, the exam moves to a summer 2027 date and the app keeps the same daily routine with more time on the weak area. The application is then filed as soon as the B1 certificate arrives.
Build plan with Claude Code
A usable first version can run within about two weeks; Saba should not wait for it. Until then she can use free DW "Nicos Weg" (A1–B1) and the vhs-Lernportal for 30 minutes a day.
1. Week 1: set up the laptop. Ubuntu 24.04 LTS, a USB headset with microphone, Claude Code installed for Paz, a Claude API key with a monthly spending limit.
2. Weeks 1–2: first version. Placement test, picture flashcards with spaced repetition, the daily lesson screen, progress saved locally. Claude Code generates the first month of content (words, pictures, audio, model letters, reading texts, real-life tasks).
3. Weeks 3–4: AI tutor. Voice speaking partner (speech-to-text, Claude, text-to-speech) and AI marking of her letters with simple feedback in English plus Amharic hints.
4. Month 2: assessment. Full mock DTZ, monthly level estimate per area, automatic re-planning of the next month, weekly email summary to Paz.
5. Every month after: Paz runs one Claude Code command to generate the next month's content batch from her latest report.
Running costs (estimates)
Item
Cost
Linux laptop
Any recent laptop already at home, or a mid-range one; 16 GB RAM helps local speech recognition
Headset with microphone
About €25–40
Claude API for speaking, marking and monthly planning
Roughly €10–25 a month with a spending cap; to confirm after the first month of real use
Speech recognition and German voices
Free, running on the laptop (open-source models)
Claude Code for building and monthly content
Paz's existing Claude plan
DTZ exam
Free if still covered by BAMF, otherwise a fee to check
Open decisions
[ ] Ask the Einbürgerungsbehörde which documents she needs for the § 9 application
[ ] Ask BAMF / the course provider whether Saba can get a funded repeat course or DTZ sitting
[ ] Pick a DTZ exam date around March 2027 and a backup date in summer 2027
[ ] Choose the laptop
[ ] Decide who reviews her weekly progress with her (Paz, a tutor, or a German-speaking friend for speaking practice)
