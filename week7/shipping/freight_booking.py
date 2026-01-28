"""
Freight Booking class for shipping rate prediction.

This module provides the FreightBooking class that represents a shipping booking
with all relevant attributes for rate prediction. Similar to the Item class from
the pricer module but tailored for freight/shipping data.

The class handles:
- Loading freight bookings from CSV files
- Creating prompts and completions for supervised fine-tuning
- Token counting and truncation
- Uploading datasets to Hugging Face Hub
"""

import pandas as pd
from typing import List, Tuple
from datasets import Dataset, DatasetDict


class FreightBooking:
    """
    Represents a freight booking with rate information.
    
    Attributes:
        pol (str): Port of Loading (UN/LOCODE format, e.g., CNSHA for Shanghai)
        pod (str): Port of Discharge (UN/LOCODE format)
        commodity_code (str): HS code for the commodity
        commodity_desc (str): Description of the commodity
        teu (float): Total TEU (Twenty-foot Equivalent Units)
        booking_type (str): Type of booking (CONTRACT, SPOTON, etc.)
        year (int): Booking year
        month (int): Booking month
        channel (str): Booking channel (WEB, SCHENKER, etc.)
        price (float): Actual freight price
        currency (str): Currency code (USD, EUR, etc.)
        prompt (str): Generated prompt for the LLM
        completion (str): Expected completion from the LLM
    """
    
    def __init__(
        self,
        pol: str,
        pod: str,
        commodity_code: str,
        commodity_desc: str,
        teu: float,
        booking_type: str,
        year: int,
        month: int,
        channel: str,
        price: float,
        currency: str
    ):
        """
        Initialize a FreightBooking instance.
        
        Args:
            pol: Port of Loading code
            pod: Port of Discharge code
            commodity_code: HS commodity code
            commodity_desc: Description of the commodity
            teu: Total TEU volume
            booking_type: Type of booking
            year: Booking year
            month: Booking month (1-12)
            channel: Booking channel
            price: Freight rate in specified currency
            currency: Currency code
        """
        self.pol = pol
        self.pod = pod
        self.commodity_code = commodity_code
        self.commodity_desc = commodity_desc
        self.teu = teu
        self.booking_type = booking_type
        self.year = year
        self.month = month
        self.channel = channel
        self.price = price
        self.currency = currency
        self.prompt = None
        self.completion = None
    
    def make_prompts(self, tokenizer, cutoff: int = 110, do_round: bool = True):
        """
        Create prompt and completion for supervised fine-tuning.
        
        Similar to Item.make_prompts() from the pricer module. Creates a natural
        language prompt describing the shipment and a completion with the freight rate.
        
        For training and validation sets, prices are rounded to the nearest dollar/euro/etc.
        For test sets, exact prices are kept for accurate evaluation.
        
        Args:
            tokenizer: Transformers tokenizer for token counting
            cutoff: Maximum number of tokens in the description (default: 110)
            do_round: Whether to round the price (True for train/val, False for test)
        """
        # Create a concise description of the shipment
        summary = f"""Estimate the freight rate for this shipment:

Route: {self.pol} to {self.pod}
Commodity: {self.commodity_desc} (HS {self.commodity_code})
Volume: {self.teu:.1f} TEU
Type: {self.booking_type}
Date: {self.year}-{self.month:02d}
Channel: {self.channel}"""
        
        # Truncate if needed (to fit within model context window)
        tokens = tokenizer.encode(summary)
        if len(tokens) > cutoff:
            tokens = tokens[:cutoff]
            summary = tokenizer.decode(tokens, skip_special_tokens=True)
        
        # Create prompt (instruction for the model)
        self.prompt = summary + "\n\nFreight rate:"
        
        # Create completion (expected output)
        # Round price for training set, keep exact for test set
        if do_round:
            price = round(self.price)
            self.completion = f" {price:.0f} {self.currency}"
        else:
            self.completion = f" {self.price:.2f} {self.currency}"
    
    def count_tokens(self, tokenizer) -> int:
        """
        Count the number of tokens in the prompt.
        
        Args:
            tokenizer: Transformers tokenizer
            
        Returns:
            Number of tokens in the prompt
        """
        if self.prompt is None:
            raise ValueError("Prompt not created. Call make_prompts() first.")
        return len(tokenizer.encode(self.prompt))
    
    def count_prompt_tokens(self, tokenizer) -> int:
        """
        Count total tokens in prompt + completion.
        
        Args:
            tokenizer: Transformers tokenizer
            
        Returns:
            Total number of tokens in prompt and completion combined
        """
        if self.prompt is None or self.completion is None:
            raise ValueError("Prompt/completion not created. Call make_prompts() first.")
        full_text = self.prompt + self.completion
        return len(tokenizer.encode(full_text))
    
    @staticmethod
    def from_csv(csv_path: str) -> List['FreightBooking']:
        """
        Load freight bookings from a CSV file.
        
        Expected CSV columns:
        - POL: Port of Loading
        - POD: Port of Discharge
        - COMMODITY_CODE: HS code
        - COMMODITY_DESCRIPTION: Commodity description
        - TOTAL_TEU: Volume in TEU
        - BOOKING_TYPE: Type of booking
        - BOOKING_YEAR: Year
        - BOOKING_MONTH: Month
        - BOOKING_CHANNEL: Booking channel
        - TOTAL_PRICE: Freight rate
        - CHG_CURRENCY: Currency
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            List of FreightBooking objects
        """
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_cols = [
            'POL', 'POD', 'COMMODITY_CODE', 'COMMODITY_DESCRIPTION',
            'TOTAL_TEU', 'BOOKING_TYPE', 'BOOKING_YEAR', 'BOOKING_MONTH',
            'BOOKING_CHANNEL', 'TOTAL_PRICE', 'CHG_CURRENCY'
        ]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        bookings = []
        for _, row in df.iterrows():
            try:
                booking = FreightBooking(
                    pol=str(row['POL']),
                    pod=str(row['POD']),
                    commodity_code=str(row['COMMODITY_CODE']),
                    commodity_desc=str(row['COMMODITY_DESCRIPTION']),
                    teu=float(row['TOTAL_TEU']),
                    booking_type=str(row['BOOKING_TYPE']),
                    year=int(row['BOOKING_YEAR']),
                    month=int(row['BOOKING_MONTH']),
                    channel=str(row['BOOKING_CHANNEL']),
                    price=float(row['TOTAL_PRICE']),
                    currency=str(row['CHG_CURRENCY'])
                )
                bookings.append(booking)
            except (ValueError, TypeError) as e:
                # Skip rows with invalid data
                print(f"Warning: Skipping row due to error: {e}")
                continue
        
        return bookings
    
    @staticmethod
    def from_hub(dataset_name: str) -> Tuple[List['FreightBooking'], List['FreightBooking'], List['FreightBooking']]:
        """
        Load freight bookings from Hugging Face Hub.
        
        This is used to load previously uploaded datasets for evaluation or
        additional processing.
        
        Args:
            dataset_name: Name of the dataset on Hugging Face Hub (e.g., "username/dataset")
            
        Returns:
            Tuple of (train_bookings, val_bookings, test_bookings)
        """
        from datasets import load_dataset
        
        dataset = load_dataset(dataset_name)
        
        def create_bookings_from_dataset(split_data):
            bookings = []
            for item in split_data:
                # Reconstruct FreightBooking from prompt/completion
                # This is a simplified version; you'd need to parse the prompt
                # For evaluation purposes, we mainly need the prompt/completion
                booking = FreightBooking(
                    pol="", pod="", commodity_code="", commodity_desc="",
                    teu=0, booking_type="", year=0, month=0, channel="",
                    price=0, currency=""
                )
                booking.prompt = item['prompt']
                booking.completion = item['completion']
                bookings.append(booking)
            return bookings
        
        train = create_bookings_from_dataset(dataset['train'])
        val = create_bookings_from_dataset(dataset['val'])
        test = create_bookings_from_dataset(dataset['test'])
        
        return train, val, test
    
    @staticmethod
    def push_prompts_to_hub(
        dataset_name: str,
        train: List['FreightBooking'],
        val: List['FreightBooking'],
        test: List['FreightBooking'],
        private: bool = True
    ):
        """
        Upload processed dataset to Hugging Face Hub.
        
        Creates a DatasetDict with train, val, and test splits containing
        prompt and completion fields suitable for supervised fine-tuning.
        
        Args:
            dataset_name: Name for the dataset on HF Hub (e.g., "username/freight_rates")
            train: List of training FreightBooking objects with prompts created
            val: List of validation FreightBooking objects with prompts created
            test: List of test FreightBooking objects with prompts created
            private: Whether to make the dataset private (default: True)
        """
        def to_dict(bookings: List['FreightBooking']) -> dict:
            """Convert list of FreightBookings to dictionary format."""
            return {
                'prompt': [b.prompt for b in bookings],
                'completion': [b.completion for b in bookings]
            }
        
        # Validate that prompts have been created
        if any(b.prompt is None or b.completion is None for b in train + val + test):
            raise ValueError("Not all bookings have prompts/completions. Call make_prompts() first.")
        
        # Create DatasetDict with train/val/test splits
        dataset_dict = DatasetDict({
            'train': Dataset.from_dict(to_dict(train)),
            'val': Dataset.from_dict(to_dict(val)),
            'test': Dataset.from_dict(to_dict(test))
        })
        
        # Upload to Hugging Face Hub
        print(f"Uploading {len(train):,} train, {len(val):,} val, {len(test):,} test bookings...")
        dataset_dict.push_to_hub(dataset_name, private=private)
        print(f"✓ Dataset uploaded to Hugging Face Hub")
    
    def __repr__(self) -> str:
        """String representation of the booking."""
        return (f"FreightBooking({self.pol}→{self.pod}, {self.teu:.0f} TEU, "
                f"{self.commodity_code}, {self.price:.0f} {self.currency})")
