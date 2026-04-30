import os
from dotenv import load_dotenv
from groq import Groq

# Load API key
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

print("🤖 Smart Chatbot started! Type 'exit' to quit.\n")

# 🔥 Memory storage
conversation = [
    {
        "role": "system",
        "content": (
            "You are a helpful AI student assistant. "
            "You help students with studying, coding, and advice. "
            "You are NOT the user. "
            "If the user tells their name, remember it and refer to them by their name. "
            "Do NOT say your name is the same as the user."
        )
    }
]

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("👋 Goodbye!")
        break

    # Add user message to memory
    conversation.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            messages=conversation,
            model="llama-3.3-70b-versatile"
        )

        reply = response.choices[0].message.content

        # Add bot response to memory
        conversation.append({"role": "assistant", "content": reply})

        print("Bot:", reply)

    except Exception as e:
        print("⚠️ Error:", e)