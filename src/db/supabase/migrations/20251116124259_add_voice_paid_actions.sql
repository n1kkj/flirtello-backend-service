-- Add paid actions for voice messages
-- SPEECH_TO_TEXT: Converting voice message to text using Deepgram API
-- TEXT_TO_SPEECH: Converting text response to voice (future feature)
INSERT INTO content.paid_actions (name, price, is_archived, description, is_public)
VALUES (
        'SPEECH_TO_TEXT',
        0.5,
        false,
        'Speech-to-text conversion for voice messages',
        false
    ),
    (
        'TEXT_TO_SPEECH',
        0.5,
        false,
        'Text-to-speech conversion for responses',
        false
    );