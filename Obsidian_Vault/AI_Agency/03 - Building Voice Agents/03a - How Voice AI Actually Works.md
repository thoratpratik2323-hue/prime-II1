> The AI Agency Vault | Questions? support@theaiagencyvault.com
> Educational material. No income or results guaranteed. Not legal, tax, or financial
> advice. Verify all platform details independently before relying on them.

# How Voice AI Actually Works

You do not need to build any of this, but you need to understand the pipeline, because every failure you will debug happens at one of these stages.

A call comes in. Four things happen in a loop, fast.

**1. Speech to text.** The caller's audio gets transcribed into text. This is where accents, background noise, bad cell connections, and people talking over each other cause problems. If the agent seems to "mishear" things, this stage is usually why.

**2. The language model decides.** The transcript plus your instructions plus the conversation so far go to a language model, which produces the next thing to say and decides whether to take an action like checking the calendar. This is the stage you control, entirely through the prompt. See [[03c - Writing The Agent Prompt]].

**3. Action.** If the model decided to check availability or book something, that request goes to the calendar and comes back. This adds time.

**4. Text to speech.** The response gets spoken back in the chosen voice.

Then it repeats until the call ends.

## Why Latency Is The Enemy

All four stages take time. Add them up and you get the pause between the caller finishing their sentence and the agent responding.

On a phone call, a pause over roughly a second feels broken. People start talking again, the agent starts talking at the same time, and the call falls apart. This is the number one reason a demo sounds bad.

What makes latency worse: long instructions the model has to process, calendar lookups mid sentence, and picking a slower model than the task needs.

What helps: a tight prompt that is not padded with irrelevant instructions, and letting the agent say something like "let me check that for you" before a calendar lookup so the silence is filled.

## Why It Sometimes Says Things You Did Not Tell It To

The model is generating language, not reading from a script. If your prompt does not cover a situation, it will improvise, and improvisation is where it invents prices, promises things the business does not offer, and agrees to appointment times that do not exist.

You do not fix this by hoping. You fix it by explicitly bounding what it is allowed to say. See [[03g - What The Agent Must Never Do]].

## What The Model Knows

It knows what you put in the prompt and what has been said on this call. That is it.

It does not know the client's real pricing, current promotions, staff schedule, or inventory unless you told it. It does not remember previous calls from the same person unless the platform is set up to give it that.

Every mistake in this category comes from an owner assuming the agent knows something obvious about their business. Part of your job during onboarding is extracting everything the agent needs to know, because the client will not think to tell you. See [[05a - Onboarding A New Client]].

%% Related: [[03c - Writing The Agent Prompt]] [[03g - What The Agent Must Never Do]] [[05a - Onboarding A New Client]] [[03f - Testing Before You Ship]] %%
