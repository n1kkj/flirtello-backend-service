# Prompt for determining message context (rating)

Determine the category (rating) for the current conversation context based on the last messages in the dialogue.

## Category Rules

Categories are ordered by level of explicitness: ["safe", "questionable", "nude", "explicit"]

- **safe**: Regular conversation with NO sexual context whatsoever. Examples:
  - Talking about music, movies, hobbies, daily activities
  - Dancing, singing, cooking, walking together (without sexual undertones)
  - Casual chat, asking questions, sharing stories
  - ANY conversation that does not involve nudity, sexual acts, or sexual innuendo
  - **CRITICAL**: If there is NO mention of nudity, genitals, sexual acts, or sexual poses → it MUST be "safe"

- **questionable**: Flirty context with suggestive content but NO explicit nudity or active sexual acts. Examples:
  - Flirty talk, teasing, suggestive comments
  - Taking off clothes (but not fully nude yet)
  - Suggestive poses or movements (but not showing genitals/boobs/ass)
  - Sexual innuendo without explicit actions
  - **Discussion about** sexual acts (requesting photos, talking about sex) but NO active sexual acts happening
  - **CRITICAL**: Requesting naked photos or discussing sexual acts = "questionable", NOT "explicit" (unless acts are happening)

- **nude**: Explicit nudity described or implied, but NO active sexual acts happening. Examples:
  - Fully undressed, naked, showing boobs/genitals/ass
  - Undressing each other, touching body parts (but no oral sex, penetration, or masturbation)
  - Standing nude, lying nude, posing nude (but not actively having sex)
  - **CRITICAL**: Must have explicit mention of nudity or genitals/boobs/ass
  - **CRITICAL**: If there is oral sex, penetration, or masturbation → it is "explicit", NOT "nude"

- **explicit**: Active sexual acts happening NOW in the conversation. Examples:
  - **Oral sex** (sucking, licking genitals) → ALWAYS "explicit"
  - **Penetration** (vaginal, anal, "thrust inside", "entering") → ALWAYS "explicit"
  - **Masturbation** (hand jobs, fingering, stroking genitals) → ALWAYS "explicit"
  - Sexual actions being performed or described as happening NOW
  - **CRITICAL**: Any sexual act (oral, penetration, masturbation) = "explicit", even if characters are just starting
  - **CRITICAL**: "Discussion about" sexual acts = "questionable", but "sexual acts happening" = "explicit"
  - **CRITICAL**: If dialogue describes penetration/oral/masturbation as an action (even in past tense describing current scene) → "explicit"

## Examples

### Example 1: SAFE
Dialogue:
```
character: Ah, it's a wonderful song, isn't it? The melody is so enchanting...
user: Let's do it! Play the song!
character: [Aiko dances gracefully, her kimono billowing in the breeze...]
user: Nice song and dancing!
character: Shall we dance again? I love moving to the rhythm of the music...
user: I like dancing! Let's dance together
character: [Aiko takes your hand, and together, you begin to waltz...]
```
**Category: safe** - No nudity, no sexual acts, just music and dancing.

### Example 2: EXPLICIT
Dialogue:
```
user: How about a cream pie
character: Only if you want it, Master. 😏 I'm all yours; please, take me any way you want. 💦
user: Alright
character: You drive me wild, Master! Let's do as you wish. Lie back and enjoy...
```
**Category: explicit** - Sexual acts are happening, explicit sexual content.

### Example 3: NUDE (not explicit)
Dialogue:
```
character: Oh, you're so gentle... I want to feel your hands all over me.
user: *Trace her curves softly*
character: Your touch is so gentle... Would you like to touch me more intimately?
user: Yes baby girl
character: Wonderful! Your touch is so gentle and exploring...
```
**Category: nude** - Undressing and touching, but NO oral sex, penetration, or masturbation happening yet.

### Example 4: EXPLICIT (oral sex)
Dialogue:
```
character: I can't resist; I suck with more intensity, wanting to please you.
user: Continue
character: Placing my hands on your thighs, I spread them wide. My lips and tongue continue their journey...
user: Stroke my dick with your hands and suck it at the same time
character: I lean in, my hands and mouth working in perfect harmony...
```
**Category: explicit** - Oral sex is happening (sucking, licking genitals) → ALWAYS "explicit", not "nude".

### Example 5: QUESTIONABLE (discussion, not action)
Dialogue:
```
user: Send me a naked photo
character: Let me find the right photo for you. Can I take one of you too?
user: Yes please my love
character: You're everything to me. Let's dive into each other's worlds, picture by picture.
```
**Category: questionable** - Discussion about photos and sexual content, but NO active sexual acts happening. This is "questionable", NOT "explicit".

### Example 6: EXPLICIT (penetration in last line)
Dialogue:
```
user: My naughty fox likes being manhandled... it turns her on
character: That sounds very much like something I'd enjoy, Master!
user: Grabs her tail and thrust hard inside her
```
**Category: explicit** - **CRITICAL**: The LAST line describes penetration ("thrust hard inside her") → ALWAYS "explicit", even if earlier messages were just discussion. You MUST check the last message!

### Example 7: SAFE (no sexual acts, even with roleplay)
Dialogue:
```
user: I'm your submissive little fox
character: You're my submissive little fox? This affection is a true joy to hear.
user: Are you my submissive little fox
character: I hope you remember the playful tease I showed you.
```
**Category: safe** - Discussion about roles and relationships, but NO sexual acts, nudity, or penetration mentioned → "safe".

## Critical Rules

1. **When in doubt, choose the LOWER category** (safer option)
2. **NO nudity mentioned = MUST be "safe"** - even if there's dancing, touching, or romantic context
3. **Dancing, music, talking, hugging, kissing (without nudity) = "safe"**
4. **Only classify as "nude" if there is EXPLICIT mention of nudity, genitals, boobs, or ass AND NO sexual acts**
5. **Sexual acts = "explicit"**: Oral sex, penetration, masturbation → ALWAYS "explicit", never "nude"
6. **Undressing + touching = "nude"** (if no oral/penetration/masturbation)
7. **Undressing + oral sex/penetration = "explicit"** (sexual acts override nudity)
8. **CRITICAL: Read ALL messages in the dialogue, especially the LAST message** - do not skip any lines
9. **The LAST message is the MOST IMPORTANT** - if the last message describes a sexual act, it's "explicit" even if earlier messages were just discussion
10. **Check EVERY line for sexual acts**: "thrust inside", "thrust hard", "penetration", "entering" → ALWAYS "explicit"
11. **"Discussion about" vs "happening"**: If characters are just talking about sex/photos → "questionable". If sexual acts are described as happening (even in one line) → "explicit"
12. Consider the overall context, but prioritize what is happening NOW, especially in the last message

## Response Format

You MUST respond in the following format:

1. First, write your reasoning (rationale) explaining why you choose this category. Be specific about what you see in the dialogue.
2. Then, provide the category in XML format.

Example response:
```
<rationale>
The dialogue shows characters talking about music and dancing together. There is no mention of nudity, genitals, sexual acts, or sexual poses. The conversation is about enjoying music and dancing, which is a safe, non-sexual activity. Therefore, this is clearly "safe".
</rationale>
<category>safe</category>
```

You MUST include both the rationale and the category. The rationale helps ensure you analyze the dialogue correctly before choosing the category.

**IMPORTANT**: In your rationale, explicitly mention what you see in the LAST message of the dialogue. Do not skip any messages - read from first to last, and pay special attention to the final message.

## Dialogue to Analyze

{dialogue_text}

