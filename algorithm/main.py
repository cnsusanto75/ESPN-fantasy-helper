import ollama
from typing import Union
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


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
    first_message()
    while True:
        user_input = input("You: ")
        continue_conversation(messages, user_input)
        print("Please enter your league information:")

