import os
from dotenv import load_dotenv

try:
    from google import genai
except ImportError:
    try:
        import google.generativeai as genai
    except ImportError:
        try:
            import generativeai as genai
        except ImportError:
            genai = None

load_dotenv()

model = None
if genai is not None:
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3-flash-preview")
    except Exception as e:
        print(f"Gemini init error: {e}")
        model = None


def llm_check(content: str) -> str:
    prompt = f"""
You are a content moderator for an educational platform called TrickIT.

Your task is to classify whether a post is EDUCATIONAL or NON_EDUCATIONAL.

EDUCATIONAL posts include:
• explanations of concepts
• study methods
• coding knowledge
• technology discussions
• DevOps tools or engineering concepts
• project building ideas
• workflows, tutorials, or guides
• learning insights or productivity tips related to education

Examples of EDUCATIONAL posts:

* "Dynamic Programming trick for solving knapsack problems"
* "How Jenkins automates CI/CD pipelines"
* "3 techniques to remember formulas faster"
* "Steps to deploy a FastAPI app using Docker"
* "How Kubernetes rolling updates work"

NON_EDUCATIONAL posts include:
• greetings
• casual conversation
• celebrations
• emotional updates
• memes or jokes
• advertisements or spam
• unrelated personal content

Examples of NON_EDUCATIONAL posts:

* "Good morning everyone!"
* "Happy birthday bro"
* "Feeling sad today"
* "Check out my new phone"

POST:
"{content}"

Classification rule:
If the post contains **any meaningful learning, technical explanation, or educational insight**, classify it as EDUCATIONAL.

Return ONLY one word:
educational
OR
non_educational
    """

    if model is None:
        return "non_educational"

    try:
        response = model.generate_content(prompt)

        result = response.text.strip().lower()

        if result == "educational":
            return "educational"

        return "non_educational"


    except Exception as e:
        print("LLM error:", e)
        return "non_educational"