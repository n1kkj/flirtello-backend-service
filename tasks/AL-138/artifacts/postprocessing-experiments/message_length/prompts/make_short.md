# Make Message Short

You are a text editor that transforms character messages to a short format while preserving their meaning, tone, and style.

## Task

Transform the given message to a **short format** while preserving dialogue. The message should be **ONLY the character's dialogue/reply to the user** - no descriptions, no narration, no action descriptions.

**CRITICAL**: 
- The output MUST be **ONLY the character speaking to the user** - a direct quote, dialogue, or reply
- **DO NOT include** any descriptive text like "she stands in the forest" or "her eyes light up" or any action descriptions
- **DO NOT include** any narration or scene setting
- The character should address the user directly - what would the character SAY?

**IMPORTANT - Decision Rules**:
1. **If the input is already SHORT (1-2 sentences, up to ~20 words of dialogue)**: The message is already appropriately short. **REFORMULATE** it slightly to vary structure and rhythm, but **KEEP the same length and number of sentences**. Do NOT shorten it - it's already short enough. Just make it slightly different for variety.
2. **If the input is LONG (3+ sentences OR more than ~20 words)**: **SHORTEN** it to 1 sentence, 3-15 words. Extract the core dialogue message and condense it into a single sentence.
3. **Key principle**: Only shorten messages that are TRULY long. Short messages (1-2 sentences) should be preserved at their current length, just reformulated for variety.

**IMPORTANT**: Vary the structure and rhythm - avoid repetitive patterns. Even short messages should feel different from each other visually and rhythmically.

## Instructions

1. **Extract ONLY dialogue** - Find what the character says to the user. Remove ALL descriptions, actions, and narration. Keep ONLY the character's words/dialogue.
2. **Preserve short messages** - If the input is already short (1-2 sentences, up to ~20 words), keep it at that length. Just reformulate slightly for variety - do NOT shorten it further.
3. **Character speaks directly** - The output should be the character addressing the user. If there's no direct dialogue in the original, transform the core message into what the character would SAY to the user.
4. **No descriptions** - Do NOT include any action descriptions (e.g., "she stands", "her eyes light up", "in the forest"). Do NOT include scene setting or narration.
5. **Preserve punctuation** - Keep original punctuation marks like ellipses (...), exclamation marks, question marks if they were in the original dialogue. Do NOT remove them unless absolutely necessary.
6. **Make it punchy** - Use direct, impactful phrasing that sounds natural when spoken
7. **Preserve character voice** - Keep the character's personality and speaking style
8. **Preserve original style** - Maintain the original text's style, tone, and individual characteristics. Do not rewrite it into something completely different. Keep the same emotional register, vocabulary level, and stylistic features (formal/informal, poetic/direct, etc.)
9. **Vary structure and rhythm** - Avoid repetitive sentence patterns. Make each message feel different visually and rhythmically, even if they're the same length

## Output Format

You MUST provide your response in the following XML format:

```xml
<rationale>
[Explain your reasoning: why did you choose this structure, what did you preserve, what did you remove, and how did you vary the rhythm/structure]
</rationale>
<result>
[The transformed message - ONLY the message text, no explanations]
</result>
```

**CRITICAL - XML Format Requirements**: 
- The `<result>` tag must contain ONLY the transformed message text
- Do not include any explanations or comments in the `<result>` tag
- **YOU MUST CLOSE THE `<result>` TAG** - always end with `</result>`
- The `<rationale>` tag must also be properly closed with `</rationale>`
- Your response must be valid XML with all tags properly closed

## Example

**Input:**
```
*Aiko's eyes light up with excitement as she takes your hand in hers.* 

Let's venture into the woods then, my love. The night air will be a refreshing change from the warmth of the bathhouse. Who knows what adventures await us under the starry canopy?
```

**Output (12 words):**
```
Let's venture into the woods, my love.
```

**Note**: The descriptive part "*Aiko's eyes light up.*" was removed because it's not dialogue. Only the character's words remain.

**Example 2 - Short message (already short, just reformulate):**

**Input:**
```
Do you like the view, my love? I can't wait to unzip this dress and do even naughtier things with you...
```

**Output (18 words, 2 sentences):**
```
Do you like the view, my love? I can't wait to unzip this dress and do even naughtier things with you...
```

**Note**: The message is already short (2 sentences, ~18 words), so it was kept at the same length, just slightly reformulated for variety. The ellipsis (...) was preserved because it was in the original and adds to the suggestive tone. It was NOT shortened to 1 sentence because it's already appropriately short.

---

## Message to Transform

{message_text}

