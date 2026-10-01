> The AI Agency Vault | Questions? support@theaiagencyvault.com
> Educational material. No income or results guaranteed. Not legal, tax, or financial
> advice. Verify all platform details independently before relying on them.

# Creating Your First Agent

> VERIFY throughout. GoHighLevel moves menus and renames features regularly. What follows is what you are configuring and why. Confirm the current location of each setting in your own account.

Voice agents live inside a sub account, not at the agency level. Open the sub account for the business you are building, and look for AI Agents or Voice AI in the navigation.

## The Configuration Checklist

The dated, field by field version of this list, with the agency level enable step and the number routing, is in [[03h - GoHighLevel Voice AI Screen By Screen]]. Read that with the platform open. This is the why.

Whatever the interface looks like when you open it, you are setting these things.

**The number it answers.** Which phone number routes to this agent. See [[02c - Phone Numbers And A2P]] for how to choose.

**The voice.** Listen to every option before choosing, on an actual phone call rather than through your laptop speakers. They sound different over a phone line. Some that sound fine in preview have artifacts on a real call. Pick for clarity over personality.

**The greeting.** The first line the caller hears. Keep it short and identify the business immediately. "Thanks for calling Riverside Family Dental, this is Ava, how can I help you?" Long greetings get talked over.

**The instructions.** The prompt. This is the whole craft and it has its own lesson. See [[03c - Writing The Agent Prompt]].

**Calendar connection.** Which calendar it books into. See [[02e - Calendars And Booking]].

**Business hours behavior.** What it does during hours versus after hours. Usually: during hours it can transfer to a human, after hours it handles the call itself and books for the next business day. See [[03e - Routing And Human Handoff]].

**Transfer destination.** Where it sends calls it cannot handle.

**Call recording and transcription.** Whether calls are recorded, and whether a disclosure is spoken. Get the client's decision in writing. See [[02c - Phone Numbers And A2P]].

**End of call actions.** What happens after: send a confirmation text, create a contact record, notify the owner, tag the lead.

## Build Order That Saves Time

Do it in this sequence. Each step depends on the one before.

1. Calendar first, fully configured and tested manually.
2. Phone number attached.
3. Agent created with a basic greeting and a minimal prompt. Minimal means this, and nothing more:

```
You are Ava, the receptionist for Riverside Family Dental.
Your job is to book the caller for an appointment.
Keep every response to one or two sentences.
Ask one question at a time and wait for the answer.
If asked whether you are a person, say you are an AI assistant for the office.
```
4. Call it. Confirm it answers and speaks. Do not proceed until this works.
5. Expand the prompt in passes, testing after each.
6. Connect booking. Test a real booking end to end.
7. Add transfers, then after hours behavior.
8. Add the post call actions.

The reason for this order is debugging. If you configure everything at once and the call fails, you have twelve possible causes. If you add one thing at a time, the cause is whatever you just changed.

## The First Call Will Be Bad

Expect it. It will talk too long, miss the point, or pause awkwardly. That is normal and it is fixable in the prompt.

What you are checking on the first call is only this: does it answer, does it speak, does it hear you. Everything after that is tuning. See [[03f - Testing Before You Ship]].

%% Related: [[03h - GoHighLevel Voice AI Screen By Screen]] [[03c - Writing The Agent Prompt]] [[02e - Calendars And Booking]] [[03e - Routing And Human Handoff]] [[03f - Testing Before You Ship]] %%
