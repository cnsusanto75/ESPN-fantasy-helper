import ollama
from league_info import initialize_league_info

model = "gemma3"

messages = [
    {"role": "system", "content": "You are a helpful assistant that provides information about ESPN fantasy basketball leagues and gives users feedback on potential moves."},
    {"role": "user", "content": "I need help analyzing my ESPN fantasy basketball league."}
]

def first_message():
    first_message = ollama.chat(model=model, messages=messages)
    messages.append({"role": "assistant", "content": first_message.message.content})
    print("Assistant:", first_message.message.content)

def continue_conversation(messages, user_input):
    messages.append({"role": "user", "content": user_input})
    response = ollama.chat(model=model, messages=messages)
    answer = response.message.content
    messages.append({"role": "assistant", "content": answer})
    print("Assistant:", answer)

def main():
    initialize_league_info()
    first_message()
    while True:
        user_input = input("You: ")
        continue_conversation(messages, user_input)
        print("Please enter your league information:")

main()