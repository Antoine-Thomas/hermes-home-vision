# STYLE, RHYTHM, AND RHETORIC PATTERNS

> Source: `creative/humanizer/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

### 30. Forced Metaphors and Figurative Overwriting

**Signs to watch:** original but strained metaphors, mixed metaphors, figurative substitutions where a plain word is clearer, a metaphor that gets explained right after it is used

**Problem:** Beyond the stock figurative words flagged in patterns 4 and 7, LLMs invent decorative metaphors that add imagery without adding meaning, then often explain them. Plain description is usually clearer and more honest. If the metaphor does not earn its place, cut it and say the literal thing.

**Before:**
> The codebase is a garden we must tend, pruning dead branches and planting seeds of innovation so the whole ecosystem can flourish. In other words, delete unused code and add features.

**After:**
> Delete unused code and add the features users are asking for.


### 31. Dramatic Fragmentation and Punchy Kickers

**Signs to watch:** two- or three-word subjectless sentences used for drama, staccato "X. And Y. And Z." runs, a short quotable line ending every paragraph or section, cutesy appositive fragments ("the catalog, honestly priced")

**Problem:** LLMs chop sentences into fragments for false emphasis and end sections with a quotable "mic-drop" line. It reads like ad copy or a motivational poster. If a line sounds like it belongs on a poster, cut it or fold it back into a real sentence with a subject. This is distinct from pattern 13 (which is about grammatical passive voice); here the tell is rhythm and showmanship, not a hidden actor.

**Before:**
> The catalog, honestly priced. Pay for what it does. Not promises. It just works. Every time.

**After:**
> The catalog is priced by usage, so you pay for the calls you actually make rather than a flat monthly fee.


### 32. Rhetorical Questions Answered Immediately

**Signs to watch:** "What if...?", "The question is...", "Ever wondered...?", a question immediately followed by its own answer, "Think about it."

**Problem:** LLMs pose a question only to answer it a beat later. The question adds no information and stalls the sentence. State the point directly.

**Before:**
> What makes an API good? It comes down to predictability. Think about it: developers want to know exactly what they will get back.

**After:**
> A good API is predictable, so developers know exactly what they will get back.


### 33. Sentence-Opener Tics

**Words to watch:** So..., Look,, habitual sentence-initial And/But, "I think"/"I believe" when stating a fact, adverb openers (Interestingly, Importantly, Notably, Crucially, Essentially, Ultimately)

**Problem:** LLMs lean on a small set of openers. Adverb openers tell the reader how to feel instead of earning it, and "So" or "Look" fake conversational warmth. Drop the opener and start with the substance.

**Before:**
> So, the results were mixed. Interestingly, adoption went up. Importantly, churn went up too. I think that means the feature still needs work.

**After:**
> The results were mixed: adoption rose, but churn rose alongside it, so the feature still needs work.


### 34. Reassurance Kickers

**Signs to watch:** And that's okay., And that's fine., There's nothing wrong with that., no shame in..., you're not alone, it's completely normal

**Problem:** LLMs tack on reassurance the reader never asked for. It softens the writing and assumes the reader needs comforting. Trust the reader: make the point and stop.

**Before:**
> You might not have a testing setup yet. And that's okay. Plenty of teams start without one, and there's nothing wrong with that.

**After:**
> Many teams start without a testing setup and add one once regressions begin costing real time.

---
