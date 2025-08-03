#!/usr/bin/env python3
"""
Manual ChatGPT Tamil Converter

This script helps you use ChatGPT manually to convert colloquial Tamil to standardized Tamil.
It generates prompts that you can copy-paste into ChatGPT and then processes the results.
"""

import pandas as pd
import json
import os
from typing import List, Dict
import logging

# Set up logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('manual_chatgpt.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ManualChatGPTConverter:
    """
    A class to help with manual ChatGPT usage for Tamil conversion.
    """
    
    def __init__(self):
        self.prompts_file = "chatgpt_prompts.txt"
        self.results_file = "chatgpt_results.json"
    
    def create_prompt(self, colloquial_text: str) -> str:
        """
        Create a prompt for ChatGPT to convert colloquial Tamil to standard Tamil.
        
        Args:
            colloquial_text (str): The colloquial Tamil text
            
        Returns:
            str: Formatted prompt for ChatGPT
        """
        prompt = f"""Please convert the following colloquial Tamil text to standardized Tamil. 
        Maintain the meaning and context while making it more formal and grammatically correct.
        Only provide the converted text, no explanations.

        Colloquial Tamil: "{colloquial_text}"
        
        Standardized Tamil:"""
        
        return prompt
    
    def generate_prompts_from_csv(self, input_file: str) -> None:
        """
        Generate prompts from a CSV file for manual ChatGPT usage.
        
        Args:
            input_file (str): Path to input CSV file
        """
        try:
            # Read the CSV file
            logger.info(f"Reading CSV file: {input_file}")
            df = pd.read_csv(input_file)
            
            # Check if required columns exist
            input_column = None
            for col in ['input', 'input_text', 'text']:
                if col in df.columns:
                    input_column = col
                    break
            
            if input_column is None:
                logger.error("No input column found. Expected one of: 'input', 'input_text', 'text'")
                return
            
            # Generate prompts
            prompts = []
            for index, row in df.iterrows():
                input_text = str(row[input_column]).strip()
                
                if input_text and input_text.lower() != 'nan':
                    prompt = self.create_prompt(input_text)
                    prompts.append({
                        'id': index,
                        'input': input_text,
                        'prompt': prompt
                    })
            
            # Save prompts to file
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                f.write("=== CHATGPT PROMPTS FOR TAMIL CONVERSION ===\n\n")
                f.write("Instructions:\n")
                f.write("1. Copy each prompt below\n")
                f.write("2. Paste it into ChatGPT\n")
                f.write("3. Copy the response\n")
                f.write("4. Add it to the results file\n\n")
                f.write("=" * 50 + "\n\n")
                
                for item in prompts:
                    f.write(f"PROMPT {item['id'] + 1}:\n")
                    f.write(f"Input: {item['input']}\n")
                    f.write(f"Prompt: {item['prompt']}\n")
                    f.write("-" * 30 + "\n\n")
            
            # Save structured data
            with open('prompts_data.json', 'w', encoding='utf-8') as f:
                json.dump(prompts, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Generated {len(prompts)} prompts in {self.prompts_file}")
            logger.info("Please use ChatGPT to get responses and then run process_results()")
            
        except Exception as e:
            logger.error(f"Error generating prompts: {str(e)}")
    
    def process_results(self, results_file: str = None) -> None:
        """
        Process ChatGPT results and create output CSV.
        
        Args:
            results_file (str): Path to results file (optional)
        """
        if results_file is None:
            results_file = self.results_file
        
        try:
            # Load prompts data
            with open('prompts_data.json', 'r', encoding='utf-8') as f:
                prompts_data = json.load(f)
            
            # Load results
            if os.path.exists(results_file):
                with open(results_file, 'r', encoding='utf-8') as f:
                    results_data = json.load(f)
            else:
                logger.error(f"Results file {results_file} not found!")
                logger.info("Please create the results file with ChatGPT responses")
                return
            
            # Create output data
            output_data = []
            for prompt_item in prompts_data:
                prompt_id = prompt_item['id']
                
                # Find corresponding result
                result_item = None
                for result in results_data:
                    if result.get('id') == prompt_id:
                        result_item = result
                        break
                
                if result_item:
                    output_data.append({
                        'input': prompt_item['input'],
                        'output': result_item.get('response', ''),
                        'prompt_id': prompt_id
                    })
                else:
                    output_data.append({
                        'input': prompt_item['input'],
                        'output': 'NO_RESPONSE',
                        'prompt_id': prompt_id
                    })
            
            # Save to CSV
            df = pd.DataFrame(output_data)
            output_csv = "chatgpt_output.csv"
            df.to_csv(output_csv, index=False, encoding='utf-8')
            
            logger.info(f"Results saved to {output_csv}")
            
        except Exception as e:
            logger.error(f"Error processing results: {str(e)}")
    
    def create_results_template(self) -> None:
        """
        Create a template results file for manual entry.
        """
        try:
            # Load prompts data
            with open('prompts_data.json', 'r', encoding='utf-8') as f:
                prompts_data = json.load(f)
            
            # Create template
            template = []
            for item in prompts_data:
                template.append({
                    'id': item['id'],
                    'input': item['input'],
                    'response': ''  # To be filled manually
                })
            
            # Save template
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Created results template: {self.results_file}")
            logger.info("Please fill in the 'response' field for each item with ChatGPT's output")
            
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")

def main():
    """
    Main function to run the manual ChatGPT converter.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Manual ChatGPT Tamil Converter")
    parser.add_argument("--input", "-i", help="Input CSV file path (required for generate action)")
    parser.add_argument("--action", "-a", choices=["generate", "template", "process"], 
                       default="generate", help="Action to perform")
    parser.add_argument("--results", "-r", help="Results file path (for process action)")
    
    args = parser.parse_args()
    
    converter = ManualChatGPTConverter()
    
    if args.action == "generate":
        if not args.input:
            logger.error("Input file is required for generate action")
            return
        converter.generate_prompts_from_csv(args.input)
    elif args.action == "template":
        converter.create_results_template()
    elif args.action == "process":
        converter.process_results(args.results)

if __name__ == "__main__":
    main() 