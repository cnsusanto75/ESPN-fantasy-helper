import ollama
import json
from league_info import get_league_info

# Define the function schema for Ollama
tools = [
    {
        'type': 'function',
        'function': {
            'name': 'get_league_info',
            'description': 'Retrieves ESPN Fantasy Basketball league information by prompting the user for league ID, year, and authentication cookies (espn_s2 and swid)',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }
    }
]

# Available functions mapping
available_functions = {
    'get_league_info': get_league_info
}

def main():
    # Initial prompt to trigger function calling
    user_message = "I need to get my ESPN fantasy basketball league information."
    
    messages = [
        {'role': 'system', 'content': 'You are an assistant that provides feedback for users on what to do for their fantasy basketball teams based on league information.'},
        {'role': 'user', 'content': user_message}]
    
    print(f"User: {user_message}\n")
    
    # First API call - Ollama should recognize it needs to call the function
    response = ollama.chat(
        model='llama3.1',  # Use a model that supports function calling
        messages=messages,
        tools=tools
    )
    
    # Check if the model wants to call a function
    if response['message'].get('tool_calls'):
        # Add the assistant's response to messages
        messages.append(response['message'])
        
        # Process each tool call
        for tool in response['message']['tool_calls']:
            function_name = tool['function']['name']
            
            print(f"Assistant wants to call: {function_name}\n")
            
            if function_name in available_functions:
                # Call the actual function
                print("Calling get_league_info()...")
                print("(This will prompt you for league details)\n")
                
                function_to_call = available_functions[function_name]
                function_response = function_to_call()
                
                # Add function response to messages
                messages.append({
                    'role': 'tool',
                    'content': json.dumps({
                        'league_id': function_response.league_id,
                        'year': function_response.year,
                        'team_count': len(function_response.teams),
                        'status': 'success'
                    })
                })
        
        # Get final response from model
        final_response = ollama.chat(
            model='llama3.1',
            messages=messages
        )
        
        print(f"\nAssistant: {final_response['message']['content']}")
    else:
        print(f"Assistant: {response['message']['content']}")

if __name__ == "__main__":
    main()