#!/usr/bin/env python3
"""
Merge three CSV files into a unified format for similarity analysis.
"""

import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def merge_csv_files():
    """
    Merge the three CSV files into a unified format.
    """
    logger.info("Starting CSV merge process...")
    
    try:
        # Load ChatGPT output
        logger.info("Loading ChatGPT output...")
        chatgpt_df = pd.read_csv("chatgpt_output.csv")
        chatgpt_df = chatgpt_df.rename(columns={
            'input': 'input_text',
            'output': 'gpt_generated'
        })
        # log the 12th row of chatgpt_df
        logger.info(f"12th row of chatgpt_df: {chatgpt_df.iloc[12]}")
        
        # Load system output
        logger.info("Loading system output...")
        system_df = pd.read_csv("coll_sentences.csv")
        system_df = system_df.rename(columns={
            'input_text': 'input_text',
            'output': 'system_generated'
        })
        # log the 12th row of system_df
        logger.info(f"12th row of system_df: {system_df.iloc[12]}")
        
        # Load actual data
        logger.info("Loading actual data...")
        actual_df = pd.read_csv("tamil_translation_complete.csv")
        actual_df = actual_df.rename(columns={
            'Input Sentence': 'input_text',
            'Literary Tamil Translation': 'actual_standardized'
        })
        # log the 12th row of actual_df
        logger.info(f"12th row of actual_df: {actual_df.iloc[12]}")

        # create a new df which has 3 columns from each df.
        merged_df = pd.DataFrame({
            'input_text': chatgpt_df['input_text'],
            'gpt_generated': chatgpt_df['gpt_generated'],
            'system_generated': system_df['system_generated'],
            'actual_standardized': actual_df['actual_standardized']
        })
        merged_df.to_csv("unified_tamil_data.csv", index=False, encoding='utf-8')
        logger.info(f"Successfully merged {len(merged_df)} samples")
        logger.info("Merged data saved to 'unified_tamil_data.csv'")
        return merged_df
    except Exception as e:
        logger.error(f"Error merging CSV files: {str(e)}")
        return None

if __name__ == "__main__":
    merge_csv_files() 