import requests
import json
import os
import configuration as config

def analyze_codebase(file_path_list, code_contents):
    """
    Sends the codebase to the LLM for analysis and script generation.
    file_path_list: List of file names/paths found in the directory.
    code_contents: Dict of {file_path: content_snippet}
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.AI_API_KEY}"
    }

    prompt = f"""
Analyze the following project structure and code snippets for security risks or malicious intent.
Project Files: {json.dumps(file_path_list)}

Code Snippets:
{json.dumps(code_contents, indent=2)}

Tasks:
1. Determine if the code is safe (no malware, miners, stressers).
2. If safe, generate the content for 'requirements.txt' and 'start.sh'.
3. If malicious, provide a clear reason for rejection.

Respond with a JSON object:
{{
  "safe": true/false,
  "reason": "Reason if malicious, else empty",
  "requirements_txt": "...",
  "start_sh": "..."
}}
"""

    payload = {
        "model": config.AI_MODEL,
        "messages": [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "response_format": { "type": "json_object" }
    }

    try:
        response = requests.post(config.AI_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        return json.loads(content)
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        return {
            "safe": False,
            "reason": f"System error during analysis: {str(e)}",
            "requirements_txt": "",
            "start_sh": ""
        }

def read_relevant_files(directory):
    """
    Reads small snippets of relevant files for the AI to analyze.
    """
    relevant_extensions = ('.py', '.js', '.ts', '.sh', '.json', '.txt', '.yaml', '.yml')
    code_contents = {}
    file_list = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.relpath(os.path.join(root, file), directory)
            file_list.append(file_path)
            
            if file.endswith(relevant_extensions) and len(code_contents) < 10:
                try:
                    full_path = os.path.join(root, file)
                    with open(full_path, 'r', errors='ignore') as f:
                        # Read first 1000 characters for analysis
                        code_contents[file_path] = f.read(1000)
                except Exception:
                    pass
                    
    return file_list, code_contents
