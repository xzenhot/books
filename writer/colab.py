import requests

url = "https://travesty-putdown-skinny.ngrok-free.dev/api/generate"
payload = {
    "model": "parable/fable:latest",
    "prompt": "why sky is blue?",
    "stream": False
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if 'response' in data:
                print("Response:", data['response'])
            else:
                print("Response key not found in JSON")
                print("Full JSON:", data)
        except Exception as json_err:
            print(f"Failed to parse JSON: {json_err}")
            print("Raw response text:", response.text[:200])
    else:
        print(f"Request failed with status {response.status_code}")
        print("Response text (first 500 chars):", response.text[:500])

except requests.exceptions.RequestException as e:
    print(f"Request error: {e}")
    sys.exit(1)


#export OLLAMA_HOST="https://travesty-putdown-skinny.ngrok-free.dev"
#$env:OLLAMA_HOST="https://travesty-putdown-skinny.ngrok-free.dev"

#$env:OLLAMA_HOST="http://localhost:11434"