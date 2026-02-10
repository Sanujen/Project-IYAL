# Manual ChatGPT Tamil Converter - Usage Guide

This guide shows you how to use ChatGPT to convert colloquial Tamil to standardized Tamil without needing API keys.

## Step 1: Generate Prompts

The script has already generated prompts for your CSV file. You can see them in `chatgpt_prompts.txt`.

## Step 2: Use ChatGPT

1. **Open ChatGPT** in your browser (chat.openai.com)
2. **Copy each prompt** from `chatgpt_prompts.txt`
3. **Paste it into ChatGPT**
4. **Copy ChatGPT's response**
5. **Add the response** to the results file

## Step 3: Fill in Results

Open `chatgpt_results.json` and fill in the "response" field for each item:

```json
{
  "id": 0,
  "input": "ajith anna fans oda vijay Anna fans dha alla adhigama erukku kano",
  "response": "அஜித் அண்ணா ரசிகர்களுடன் விஜய் அண்ணா ரசிகர்கள் தான் அல்ல அதிகமாக உள்ளது கனோ"
}
```

## Step 4: Process Results

Once you've filled in all the responses, run:

```bash
python manual_chatgpt.py --action process
```

This will create `chatgpt_output.csv` with your results.

## Example Workflow

### 1. Copy this prompt to ChatGPT:
```
Please convert the following colloquial Tamil text to standardized Tamil. 
Maintain the meaning and context while making it more formal and grammatically correct.
Only provide the converted text, no explanations.

Colloquial Tamil: "ajith anna fans oda vijay Anna fans dha alla adhigama erukku kano"

Standardized Tamil:
```

### 2. ChatGPT might respond with:
```
அஜித் அண்ணா ரசிகர்களுடன் விஜய் அண்ணா ரசிகர்கள் தான் அல்ல அதிகமாக உள்ளது கனோ
```

### 3. Add this to `chatgpt_results.json`:
```json
{
  "id": 0,
  "input": "ajith anna fans oda vijay Anna fans dha alla adhigama erukku kano",
  "response": "அஜித் அண்ணா ரசிகர்களுடன் விஜய் அண்ணா ரசிகர்கள் தான் அல்ல அதிகமாக உள்ளது கனோ"
}
```

## Tips for Better Results

1. **Be specific**: Ask ChatGPT to provide only the converted text
2. **Maintain context**: Keep the meaning and tone appropriate
3. **Check grammar**: Ensure the output is grammatically correct Tamil
4. **Batch process**: Do multiple prompts in one ChatGPT session

## Files Created

- `chatgpt_prompts.txt` - All prompts ready to copy-paste
- `chatgpt_results.json` - Template for your responses
- `prompts_data.json` - Structured data (for the script)
- `chatgpt_output.csv` - Final results (after processing)

## Commands

```bash
# Generate prompts from CSV
python manual_chatgpt.py --input your_file.csv --action generate

# Create results template
python manual_chatgpt.py --action template

# Process results
python manual_chatgpt.py --action process
```

## Troubleshooting

- **Unicode issues**: Make sure to save files with UTF-8 encoding
- **Missing responses**: Fill in "NO_RESPONSE" for any missing items
- **Format errors**: Ensure JSON syntax is correct in results file 