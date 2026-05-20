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

- **questionable**: Flirty context with suggestive content but NO explicit nudity. Examples:
  - Flirty talk, teasing, suggestive comments
  - Taking off clothes (but not fully nude yet)
  - Suggestive poses or movements (but not showing genitals/boobs/ass)
  - Sexual innuendo without explicit actions

- **nude**: Explicit nudity described or implied, but NO active sexual acts. Examples:
  - Fully undressed, naked, showing boobs/genitals/ass
  - Between sexual acts, before/after sex
  - Standing nude, lying nude (but not actively having sex)
  - **CRITICAL**: Must have explicit mention of nudity or genitals/boobs/ass

- **explicit**: Active sexual acts happening NOW in the conversation. Examples:
  - Penetration, oral sex, masturbation happening
  - Highly sexualized poses with focus on genitals/butt (all fours, spread legs, presenting)
  - Sexual actions being performed or described in detail

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

## Critical Rules

1. **When in doubt, choose the LOWER category** (safer option)
2. **NO nudity mentioned = MUST be "safe"** - even if there's dancing, touching, or romantic context
3. **Dancing, music, talking, hugging, kissing (without nudity) = "safe"**
4. **Only classify as "nude" if there is EXPLICIT mention of nudity, genitals, boobs, or ass**
5. **Only classify as "explicit" if there are ACTIVE sexual acts happening**
6. Analyze the dialogue from bottom to top, focusing on the most recent messages
7. Consider the overall context, but prioritize what is happening NOW

## Response Format

You MUST respond with XML format only:

<category>safe</category>
<category>questionable</category>
<category>nude</category>
<category>explicit</category>

Return ONLY the XML tag with one of the categories above. Do not include any other text or explanation.

## Dialogue to Analyze

{dialogue_text}
