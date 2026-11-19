# CriticRAG AI — Sample Questions Guide

A curated set of questions to test the Multi-Agent Reasoning Loop, organized by **expected Critic confidence level** (high → low).

---

## ✅ TIER 1 — Near 100% Confidence (Direct Corpus Match)

These questions have exact answers in the local corpus. The Critic will APPROVE on the first iteration.

| # | Question | Expected Answer |
|---|----------|-----------------|
| 1 | Who designed the Eiffel Tower? | Gustave Eiffel |
| 2 | What is the boiling point of water? | 100°C / 212°F |
| 3 | What is the speed of light? | 299,792,458 m/s |
| 4 | Who painted the Mona Lisa? | Leonardo da Vinci |
| 5 | When was the United Nations founded? | 24 October 1945 |
| 6 | Who described the double helix structure of DNA? | Watson and Crick (1953) |
| 7 | What is the highest mountain on Earth? | Mount Everest (8,848.86 m) |
| 8 | Who created the Python programming language? | Guido van Rossum |
| 9 | What is the largest hot desert in the world? | Sahara Desert |
| 10 | What is the largest river by discharge in the world? | Amazon River |
| 11 | What process do plants use to convert sunlight to food? | Photosynthesis |
| 12 | Where is the Eiffel Tower located? | Paris, France |

---

## 🟡 TIER 2 — Medium Confidence (~60–85%) — Partial Corpus Match

These are partially supported by the corpus. The Critic may trigger 1–2 refinement cycles.

| # | Question | Why Medium Confidence |
|---|----------|-----------------------|
| 13 | How tall is Mount Everest in feet? | Corpus has meters; conversion needed |
| 14 | In which year did Gustave Eiffel complete the tower? | Corpus says 1889 — needs extraction |
| 15 | Who built the Great Wall of China and when? | Ming dynasty mentioned but no specific dates |
| 16 | Where exactly is the Amazon River? | Corpus says "South America" — vague location |
| 17 | What byproduct does photosynthesis produce? | Oxygen mentioned — may need rephrasing |
| 18 | Where was Leonardo da Vinci from? | Corpus says "Italian" — vague |
| 19 | What does DNA stand for? | Structure described but not the full name |
| 20 | What is the elevation of Mount Everest in meters? | Needs extraction from measurement data |

---

## 🟠 TIER 3 — Lower Confidence (~30–60%) — Inference Required

These require multi-hop reasoning or inference beyond literal corpus content.

| # | Question | Challenge |
|---|----------|-----------|
| 21 | Is the Sahara larger than the United States? | Corpus says "comparable" — not exact |
| 22 | How many seconds does light take to travel 1km? | Requires computation using speed of light |
| 23 | What year was Python created relative to the World Wide Web? | Cross-domain knowledge |
| 24 | Did Rosalind Franklin discover DNA? | Nuanced — corpus says she helped, Watson/Crick described it |
| 25 | Can the Great Wall of China be seen from space? | Common myth — not directly addressed in corpus |
| 26 | How does photosynthesis relate to climate change? | Synthesis question not covered in corpus |
| 27 | Is Mount Everest or the Amazon River older? | Not in corpus |
| 28 | What did the 1889 World Fair celebrate? | Corpus mentions it but not detail |

---

## 🔴 TIER 4 — Very Low Confidence / Out-of-Corpus

These are completely outside the local corpus. Will force REVISE cycles — great for demonstrating self-correction.

| # | Question | Reason |
|---|----------|--------|
| 29 | Who is the current Prime Minister of India? | Not in corpus (current events) |
| 30 | What is the capital of Australia? | Not in corpus |
| 31 | Who won the FIFA World Cup in 2022? | Not in corpus |
| 32 | What is the largest ocean on Earth? | Not in corpus |
| 33 | Who wrote the Harry Potter series? | Not in corpus |
| 34 | What is the boiling point of iron? | Not in corpus (different from water) |
| 35 | How does a nuclear reactor work? | Not in corpus (physics) |
| 36 | What is the GDP of India? | Not in corpus (economics) |

---

## 💡 Run in Mock Mode — 100% FREE (No API Key)

Mock mode is completely free, offline, and unlimited. Set in your `.env`:

```
AGENTICLOOPQA_MOCK=1
```

Best questions for Mock Mode:
- "Who designed the Eiffel Tower?" — shows REVISE → APPROVE in 2 iterations
- "What is the speed of light?" — shows quick Generator + Critic agreement
- "Who painted the Mona Lisa?" — best for visualizing self-correction loop

---

## 🆓 Free API Alternatives to Gemini

| Provider | Free Tier | Best Model | RPM Limit |
|----------|-----------|------------|-----------|
| **Groq** ⭐ RECOMMENDED | 14,400 req/day FREE | llama-3.3-70b-versatile | 30 RPM |
| **OpenRouter** | Free models available | meta-llama/llama-3.1-8b | Varies |
| **Ollama** (Local) | Unlimited / offline | llama3.2, mistral | Unlimited |
| **Gemini Free** | 15 RPM / 1,500/day | gemini-3.6-flash | 15 RPM |

### Setup Groq (Recommended — FREE forever):
1. Sign up at https://console.groq.com (no credit card)
2. Create an API key
3. In your `.env` file set: `GROQ_API_KEY=gsk_your_key_here`
4. Restart server — it will auto-use Groq!

### Setup Ollama (Local — Fully Offline):
```bash
# Install: https://ollama.com
ollama pull llama3.2
ollama serve
```
Set in `.env`: `OLLAMA_BASE_URL=http://localhost:11434`
