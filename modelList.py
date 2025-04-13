import google.generativeai as genai

# Replace with your actual Gemini API key
GOOGLE_API_KEY = "AIzaSyAP349xdo8xgbrBHyBxwIReiFnhFV946Rc"

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

for m in genai.list_models():
    print(f"Model: {m.name}")
    for method in m.supported_generation_methods:
        print(f"- {method}")