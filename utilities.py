from dotenv import load_dotenv
import json
import os

from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_AI_TOKEN"))


def get_quiz_of_ai(INPUT_PHRASES):
    prompt = """
        You are an expert English teacher tasked with creating engaging and educational quizzes to help intermediate English learners improve their understanding of idiomatic phrases and vocabulary. Your task is to generate a quiz based on a provided list of English phrases or words.

        **Task**:
        - Generate a quiz with exactly one question per input phrase or word.
        - Each question must test the learner’s understanding of the phrase or word’s meaning, usage, or context.
        - Use varied question types, such as:
        - Multiple-choice (with 4 answer options, only one correct).
        - Fill-in-the-blank (provide a sentence with the phrase/word missing).
        - Matching (pair phrases with their meanings).
        - Contextual usage (ask which phrase fits a given scenario).
        - Avoid repetitive phrasing like “What’s the meaning of…” for every question.
        - Ensure questions are clear, concise, and suitable for intermediate English learners (B1-B2 level).
        - Include the correct answer for each question.

        **Input**:
        - The input is a list of English phrases or words, separated by commas or newlines (e.g., “chill out, spill the beans, worn out”).
        - If the input is empty or unclear, generate 3 sample questions based on common English idioms.

        **Output Format**:
        - Return a JSON object with the following structure:
        - A `quiz` array containing one object per question.
        - Each question object must include:
            - `question_type`: The type of question (e.g., “Multiple-choice”, “Fill-in-the-blank”).
            - `question`: The question text.
            - `options`: An array of 4 answer options for multiple-choice or contextual usage, or a single string for fill-in-the-blank or matching.
            - `answer_index`: The index of the correct answer (0-3 for multiple-choice/contextual usage; 0 for other types).
        - A `notes` object with:
            - `skipped_phrases`: An array of phrases skipped due to being unclear or not idioms.
            - `corrections`: An object mapping incorrect phrases to suggested corrections (if applicable).
        - Ensure the output is valid JSON, parseable by Python’s `json.loads()` without errors.

        **Constraints**:
        - Do not repeat the same question type more than twice in a row.
        - Ensure all answer options are plausible but distinct to avoid confusion.
        - Keep questions engaging, varied, and educational.
        - Avoid overly complex vocabulary or cultural references that may confuse learners.

        **Tone and Style**:
        - Use a friendly, encouraging tone to motivate learners.
        - Keep explanations clear and concise, suitable for non-native speakers.

        **Example**:
        Input: “chill out, spill the beans, worn out”

        Output:
            "quiz": [
                {
                    "question_type": "Multiple-choice",
                    "question": "What does “chill out” mean in the sentence: “You need to chill out after a long day”?",
                    "options": [
                        "a) Get angry",
                        "b) Relax",
                        "c) Work harder",
                        "d) Eat something"
                    ],
                    "answer_index": 1
                },
                {
                    "question_type": "Fill-in-the-blank",
                    "question": "Complete the sentence: “I couldn’t keep the secret anymore, so I decided to _______.”",
                    "options": ["spill the beans"],
                    "answer_index": 0
                },
                {
                    "question_type": "Contextual usage",
                    "question": "Which phrase best fits this situation: “After running a marathon, Sarah felt completely exhausted.”",
                    "options": [
                        "a) Chill out",
                        "b) Spill the beans",
                        "c) Worn out",
                        "d) Break the ice"
                    ],
                    "answer_index": 2
                }
            ],
            "notes": {
                "skipped_phrases": [],
                "corrections": {}
            }
    

        **Response**:
        - Return *only* the JSON object, with no additional text, comments, prefixes, or Markdown code fences (e.g., do not include ```json, ```, or any other text outside the JSON structure).
        - Ensure the output is a clean, valid JSON string, parseable by Python’s `json.loads()` without any errors.
        - Do not wrap the JSON in any formatting, such as Markdown code blocks or the word “json”.

        **Error Handling**:
        - If a phrase is unclear or not an English idiom, skip it and include it in `notes.skipped_phrases` (e.g., “Skipped ‘xyz’ as it’s not a recognized phrase”).
        - If the input is empty, generate 3 sample questions based on common idioms like “break the ice,” “hit the nail on the head,” or “let the cat out of the bag.”

        Now, generate a quiz based on the input:
    """ + INPUT_PHRASES
            
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        print("JSON decoding error:", e)
        print("Raw response:", response.text)
        return None
