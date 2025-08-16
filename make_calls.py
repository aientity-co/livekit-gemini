#!/usr/bin/env python3
"""
Simple script to initiate outbound calls using the OutboundCaller class.
This script provides a CLI interface for making single or bulk outbound calls.
"""

import asyncio
import argparse
import json
import csv
import sys
from typing import List
from outbound_caller import OutboundCaller, CallRecipient
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_contacts_from_csv(file_path: str) -> List[CallRecipient]:
    """
    Load contacts from a CSV file.
    Expected CSV format: name,phone,company,notes
    """
    contacts = []
    try:
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                contact = CallRecipient(
                    name=row.get('name', '').strip(),
                    phone_number=row.get('phone', '').strip(),
                    company=row.get('company', '').strip() or None,
                    notes=row.get('notes', '').strip() or None
                )
                if contact.name and contact.phone_number:
                    contacts.append(contact)
                else:
                    logger.warning(f"Skipping invalid contact: {row}")
    except FileNotFoundError:
        logger.error(f"CSV file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        sys.exit(1)
    
    return contacts


def load_contacts_from_json(file_path: str) -> List[CallRecipient]:
    """
    Load contacts from a JSON file.
    Expected JSON format: [{"name": "...", "phone": "...", "company": "...", "notes": "..."}]
    """
    contacts = []
    try:
        with open(file_path, 'r') as jsonfile:
            data = json.load(jsonfile)
            for item in data:
                contact = CallRecipient(
                    name=item.get('name', '').strip(),
                    phone_number=item.get('phone', '').strip(),
                    company=item.get('company', '').strip() or None,
                    notes=item.get('notes', '').strip() or None
                )
                if contact.name and contact.phone_number:
                    contacts.append(contact)
                else:
                    logger.warning(f"Skipping invalid contact: {item}")
    except FileNotFoundError:
        logger.error(f"JSON file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading JSON file: {e}")
        sys.exit(1)
    
    return contacts


def create_sample_contacts_csv():
    """Create a sample contacts CSV file for reference."""
    sample_data = [
        ['name', 'phone', 'company', 'notes'],
        ['John Smith', '+1234567890', 'Tech Corp', 'Potential lead from website'],
        ['Jane Doe', '+1234567891', 'Marketing Inc', 'Interested in AI solutions'],
        ['Bob Johnson', '+1234567892', 'Sales LLC', 'Follow up on demo request']
    ]
    
    with open('sample_contacts.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(sample_data)
    
    print("Created sample_contacts.csv with example data")


def create_sample_contacts_json():
    """Create a sample contacts JSON file for reference."""
    sample_data = [
        {
            "name": "John Smith",
            "phone": "+1234567890",
            "company": "Tech Corp",
            "notes": "Potential lead from website"
        },
        {
            "name": "Jane Doe",
            "phone": "+1234567891",
            "company": "Marketing Inc",
            "notes": "Interested in AI solutions"
        },
        {
            "name": "Bob Johnson",
            "phone": "+1234567892",
            "company": "Sales LLC",
            "notes": "Follow up on demo request"
        }
    ]
    
    with open('sample_contacts.json', 'w') as jsonfile:
        json.dump(sample_data, jsonfile, indent=2)
    
    print("Created sample_contacts.json with example data")


async def make_single_call(name: str, phone: str, company: str = None, notes: str = None):
    """Make a single outbound call."""
    caller = OutboundCaller()
    
    recipient = CallRecipient(
        name=name,
        phone_number=phone,
        company=company,
        notes=notes
    )
    
    print(f"\n🔄 Initiating call to {name} at {phone}")
    if company:
        print(f"   Company: {company}")
    if notes:
        print(f"   Notes: {notes}")
    
    result = await caller.make_outbound_call(recipient)
    
    print(f"\n📞 Call Result:")
    print(f"   Name: {result.recipient.name}")
    print(f"   Phone: {result.recipient.phone_number}")
    print(f"   Status: {result.status}")
    print(f"   Call SID: {result.call_sid}")
    print(f"   Initiated: {result.initiated_at}")
    
    if result.error:
        print(f"   Error: {result.error}")
    
    return result


async def make_bulk_calls(contacts: List[CallRecipient], delay: int = 30):
    """Make bulk outbound calls."""
    caller = OutboundCaller()
    
    print(f"\n🚀 Starting bulk calling campaign")
    print(f"   Total contacts: {len(contacts)}")
    print(f"   Delay between calls: {delay} seconds")
    print(f"   Estimated duration: {(len(contacts) * delay) / 60:.1f} minutes")
    
    # Show contact list
    print(f"\n📋 Contact List:")
    for i, contact in enumerate(contacts, 1):
        print(f"   {i}. {contact.name} - {contact.phone_number}")
        if contact.company:
            print(f"      Company: {contact.company}")
    
    # Confirm before proceeding
    confirm = input(f"\n❓ Proceed with calling {len(contacts)} contacts? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Campaign cancelled")
        return
    
    print(f"\n▶️  Starting calls...")
    results = await caller.make_bulk_calls(contacts, delay_between_calls=delay)
    
    # Display results
    print(f"\n✅ Campaign completed!")
    summary = caller.get_campaign_summary()
    
    print(f"\n📊 Campaign Summary:")
    print(f"   Total calls: {summary['total_calls']}")
    print(f"   Success rate: {summary['success_rate']}")
    print(f"   Successful calls: {summary['successful_calls']}")
    
    if summary.get('status_breakdown'):
        print(f"\n📈 Status Breakdown:")
        for status, count in summary['status_breakdown'].items():
            print(f"   {status}: {count}")
    
    # Save results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"call_results_{timestamp}.json"
    
    results_data = []
    for result in results:
        results_data.append({
            'name': result.recipient.name,
            'phone': result.recipient.phone_number,
            'company': result.recipient.company,
            'call_sid': result.call_sid,
            'status': result.status,
            'initiated_at': result.initiated_at.isoformat(),
            'error': result.error
        })
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"💾 Results saved to: {results_file}")


def main():
    parser = argparse.ArgumentParser(description='Make outbound calls using LiveKit and Twilio')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Single call command
    single_parser = subparsers.add_parser('single', help='Make a single call')
    single_parser.add_argument('--name', required=True, help='Contact name')
    single_parser.add_argument('--phone', required=True, help='Phone number')
    single_parser.add_argument('--company', help='Company name (optional)')
    single_parser.add_argument('--notes', help='Notes about the contact (optional)')
    
    # Bulk call command
    bulk_parser = subparsers.add_parser('bulk', help='Make bulk calls from file')
    bulk_parser.add_argument('--file', required=True, help='CSV or JSON file with contacts')
    bulk_parser.add_argument('--delay', type=int, default=30, help='Seconds between calls (default: 30)')
    
    # Sample file generation commands
    subparsers.add_parser('sample-csv', help='Create sample contacts CSV file')
    subparsers.add_parser('sample-json', help='Create sample contacts JSON file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Handle sample file creation
    if args.command == 'sample-csv':
        create_sample_contacts_csv()
        return
    elif args.command == 'sample-json':
        create_sample_contacts_json()
        return
    
    # Validate environment variables
    try:
        caller = OutboundCaller()
        logger.info("✅ Environment configuration validated")
    except ValueError as e:
        logger.error(f"❌ Environment configuration error: {e}")
        logger.error("Please check your .env file and ensure all required variables are set")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Initialization error: {e}")
        sys.exit(1)
    
    # Execute commands
    if args.command == 'single':
        asyncio.run(make_single_call(args.name, args.phone, args.company, args.notes))
    
    elif args.command == 'bulk':
        # Load contacts based on file extension
        if args.file.endswith('.csv'):
            contacts = load_contacts_from_csv(args.file)
        elif args.file.endswith('.json'):
            contacts = load_contacts_from_json(args.file)
        else:
            logger.error("Unsupported file format. Use .csv or .json files")
            sys.exit(1)
        
        if not contacts:
            logger.error("No valid contacts found in file")
            sys.exit(1)
        
        asyncio.run(make_bulk_calls(contacts, args.delay))


if __name__ == '__main__':
    main()
