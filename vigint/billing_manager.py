"""Automated Weekly Billing System for Vigint

This module handles the automated billing system, including:
- Processing payment details
- Running scheduled weekly billing jobs
- Integrating with the invoice generator
- Payment processing with different payment methods
"""

import logging
import os
from datetime import datetime, timedelta
import json
import configparser
from sqlalchemy import func
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64
import traceback

from .models import db, APIKey, APIUsage, Client, PaymentDetails, PaymentMethod
from .invoice_generator import generate_invoice_html, generate_invoice_csv, send_invoice_email, create_qonto_invoice

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
config = configparser.ConfigParser()
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
server_config_path = os.environ.get('VIGINT_SERVER_CONFIG_PATH', os.path.join(script_dir, 'server_config.ini'))

if os.path.exists(server_config_path):
    config.read(server_config_path)
else:
    config_path = os.environ.get('VIGINT_CONFIG_PATH', os.path.join(script_dir, 'config.ini'))
    config.read(config_path)


def get_payment_details_for_billing():
    """Get all payment details for clients with auto-pay enabled and due for billing"""
    today = datetime.utcnow().date()
    
    # Get all payment details where:
    # 1. Auto-pay is enabled
    # 2. Next payment date is today or earlier
    eligible_payments = PaymentDetails.query.filter(
        PaymentDetails.auto_pay_enabled == True,
        PaymentDetails.next_payment_date <= today
    ).all()
    
    return eligible_payments


def calculate_client_usage(api_key_id, start_date, end_date):
    """Calculate client usage and cost for a specific period"""
    # Query total usage and cost for the period
    usage_stats = db.session.query(
        func.count(APIUsage.id).label('request_count'),
        func.sum(APIUsage.cost).label('total_cost')
    ).filter(
        APIUsage.api_key_id == api_key_id,
        APIUsage.timestamp >= start_date,
        APIUsage.timestamp <= end_date
    ).first()
    
    # Get detailed usage by endpoint for the invoice
    endpoint_stats = db.session.query(
        APIUsage.endpoint,
        func.count(APIUsage.id).label('count'),
        func.sum(APIUsage.cost).label('cost')
    ).filter(
        APIUsage.api_key_id == api_key_id,
        APIUsage.timestamp >= start_date,
        APIUsage.timestamp <= end_date
    ).group_by(APIUsage.endpoint).all()
    
    # Format endpoint stats for the invoice
    usage_details = []
    for stat in endpoint_stats:
        endpoint_name = stat.endpoint.split('/')[-1].capitalize() if stat.endpoint else 'Unknown'
        usage_details.append({
            'service': endpoint_name,
            'count': stat.count,
            'cost': float(stat.cost) if stat.cost else 0.0
        })
    
    return {
        'request_count': usage_stats.request_count if usage_stats else 0,
        'total_cost': float(usage_stats.total_cost) if usage_stats and usage_stats.total_cost else 0.0,
        'usage_details': usage_details
    }


def process_weekly_billing():
    """Process weekly billing for all eligible clients"""
    logging.info("Starting weekly billing process...")
    
    # Get all payment details eligible for billing
    eligible_payments = get_payment_details_for_billing()
    
    billing_results = {
        'success': [],
        'failed': []
    }
    
    today = datetime.utcnow().date()
    
    for payment_details in eligible_payments:
        client_name = None
        try:
            # Get the API key record
            api_key = APIKey.query.filter_by(id=payment_details.api_key_id).first()
            if not api_key:
                logging.error(f"API key not found for payment_details_id={payment_details.id}")
                billing_results['failed'].append({
                    'payment_id': payment_details.id,
                    'error': 'API key not found'
                })
                continue
            
            # Get the client record
            client = Client.query.filter_by(id=api_key.client_id).first()
            if not client:
                logging.error(f"Client not found for api_key_id={api_key.id}")
                billing_results['failed'].append({
                    'payment_id': payment_details.id,
                    'client_id': api_key.client_id,
                    'error': 'Client not found'
                })
                continue
                
            client_name = client.name
            client_email = client.email
            
            # Determine billing period
            if payment_details.payment_frequency.value == 'weekly':
                # Calculate start of previous week (Monday to Sunday)
                end_date = today - timedelta(days=today.weekday() + 1)  # Previous Sunday
                start_date = end_date - timedelta(days=6)  # Previous Monday
            elif payment_details.payment_frequency.value == 'monthly':
                # Last month
                if today.month == 1:
                    start_date = datetime(today.year - 1, 12, 1).date()
                    end_date = datetime(today.year, 1, 1).date() - timedelta(days=1)
                else:
                    start_date = datetime(today.year, today.month - 1, 1).date()
                    end_date = datetime(today.year, today.month, 1).date() - timedelta(days=1)
            else:  # quarterly
                # Last quarter
                current_quarter = (today.month - 1) // 3
                last_quarter = current_quarter - 1 if current_quarter > 0 else 3
                last_quarter_year = today.year if current_quarter > 0 else today.year - 1
                
                start_month = last_quarter * 3 + 1
                end_month = start_month + 2
                
                if end_month > 12:
                    end_month -= 12
                
                start_date = datetime(last_quarter_year, start_month, 1).date()
                if end_month == 12:
                    end_date = datetime(last_quarter_year, 12, 31).date()
                else:
                    end_date = datetime(last_quarter_year, end_month + 1, 1).date() - timedelta(days=1)
            
            # Calculate usage for the billing period
            usage_data = calculate_client_usage(api_key.id, start_date, end_date)
            
            # Only generate invoice if there's usage to bill
            if usage_data['total_cost'] > 0:
                # Generate invoice number (format: VIGINT-YYYY-XXXX)
                invoice_count = db.session.query(func.count()).select_from(PaymentDetails).filter(
                    PaymentDetails.last_invoice_number.isnot(None)
                ).scalar() or 0
                
                invoice_number = f"VIGINT-{today.year}-{invoice_count + 1:04d}"
                
                # Generate invoice HTML and CSV
                invoice_html = generate_invoice_html(
                    client_name=client_name,
                    client_email=client_email,
                    invoice_number=invoice_number,
                    start_date=start_date,
                    end_date=end_date,
                    usage_data=usage_data
                )
                
                invoice_csv = generate_invoice_csv(
                    client_name=client_name,
                    client_email=client_email,
                    invoice_number=invoice_number,
                    start_date=start_date,
                    end_date=end_date,
                    usage_data=usage_data
                )
                
                # Process payment based on payment method
                payment_result = process_payment(
                    payment_details=payment_details,
                    amount=usage_data['total_cost'],
                    invoice_number=invoice_number
                )
                
                if payment_result.get('success'):
                    # Send invoice email
                    email_result = send_invoice_email(
                        config=config,
                        client_name=client_name,
                        client_email=client_email,
                        invoice_number=invoice_number,
                        start_date=start_date,
                        end_date=end_date,
                        usage_data=usage_data,
                        invoice_html=invoice_html,
                        invoice_csv=invoice_csv,
                        payment_status="Paid Automatically"
                    )
                    
                    # Create invoice in Qonto if configured
                    try:
                        if 'Qonto' in config:
                            qonto_result = create_qonto_invoice(
                                config=config,
                                client_name=client_name,
                                client_email=client_email,
                                usage_data=usage_data,
                                invoice_number=invoice_number,
                                start_date=start_date,
                                end_date=end_date
                            )
                    except Exception as e:
                        logging.error(f"Error creating Qonto invoice: {str(e)}")
                    
                    # Update payment details with last invoice info
                    payment_details.last_invoice_number = invoice_number
                    payment_details.last_payment_date = today
                    
                    # Calculate next payment date based on frequency
                    if payment_details.payment_frequency.value == 'weekly':
                        # Next Monday
                        days_until_monday = (7 - today.weekday()) % 7
                        next_payment = today + timedelta(days=days_until_monday)
                    elif payment_details.payment_frequency.value == 'monthly':
                        # First day of next month
                        next_month = today.month + 1 if today.month < 12 else 1
                        next_year = today.year if today.month < 12 else today.year + 1
                        next_payment = datetime(next_year, next_month, 1).date()
                    else:  # quarterly
                        # First day of next quarter
                        current_quarter = (today.month - 1) // 3
                        next_quarter_month = (current_quarter * 3 + 3) % 12 + 1
                        next_quarter_year = today.year if next_quarter_month > today.month else today.year + 1
                        next_payment = datetime(next_quarter_year, next_quarter_month, 1).date()
                        
                    payment_details.next_payment_date = next_payment
                    db.session.commit()
                    
                    billing_results['success'].append({
                        'client_id': client.id,
                        'client_name': client_name,
                        'invoice_number': invoice_number,
                        'amount': usage_data['total_cost'],
                        'next_payment_date': next_payment.isoformat()
                    })
                else:
                    # Payment failed
                    # Send invoice email with payment required
                    email_result = send_invoice_email(
                        config=config,
                        client_name=client_name,
                        client_email=client_email,
                        invoice_number=invoice_number,
                        start_date=start_date,
                        end_date=end_date,
                        usage_data=usage_data,
                        invoice_html=invoice_html,
                        invoice_csv=invoice_csv,
                        payment_status="Payment Required"
                    )
                    
                    billing_results['failed'].append({
                        'client_id': client.id,
                        'client_name': client_name,
                        'invoice_number': invoice_number,
                        'amount': usage_data['total_cost'],
                        'error': payment_result.get('error', 'Unknown payment error')
                    })
            else:
                # No usage to bill, just update next payment date
                if payment_details.payment_frequency.value == 'weekly':
                    # Next Monday
                    days_until_monday = (7 - today.weekday()) % 7
                    next_payment = today + timedelta(days=days_until_monday)
                elif payment_details.payment_frequency.value == 'monthly':
                    # First day of next month
                    next_month = today.month + 1 if today.month < 12 else 1
                    next_year = today.year if today.month < 12 else today.year + 1
                    next_payment = datetime(next_year, next_month, 1).date()
                else:  # quarterly
                    # First day of next quarter
                    current_quarter = (today.month - 1) // 3
                    next_quarter_month = (current_quarter * 3 + 3) % 12 + 1
                    next_quarter_year = today.year if next_quarter_month > today.month else today.year + 1
                    next_payment = datetime(next_quarter_year, next_quarter_month, 1).date()
                    
                payment_details.next_payment_date = next_payment
                db.session.commit()
                
                billing_results['success'].append({
                    'client_id': client.id,
                    'client_name': client_name,
                    'amount': 0,
                    'message': 'No usage to bill',
                    'next_payment_date': next_payment.isoformat()
                })
                
        except Exception as e:
            logging.error(f"Error processing billing for client {client_name if client_name else 'unknown'}: {str(e)}")
            logging.error(traceback.format_exc())
            billing_results['failed'].append({
                'payment_id': payment_details.id,
                'error': str(e)
            })
    
    # Log billing results
    logging.info(f"Weekly billing completed. Successful: {len(billing_results['success'])}, Failed: {len(billing_results['failed'])}")
    
    return billing_results


def process_payment(payment_details, amount, invoice_number):
    """Process payment based on payment method"""
    if payment_details.payment_method == PaymentMethod.CREDIT_CARD:
        return process_credit_card_payment(payment_details, amount, invoice_number)
    elif payment_details.payment_method == PaymentMethod.BANK_TRANSFER:
        return process_bank_transfer(payment_details, amount, invoice_number)
    elif payment_details.payment_method == PaymentMethod.DIRECT_DEBIT:
        return process_direct_debit(payment_details, amount, invoice_number)
    else:
        return {'success': False, 'error': f"Unsupported payment method: {payment_details.payment_method}"}


def process_credit_card_payment(payment_details, amount, invoice_number):
    """Process credit card payment using a payment processor (e.g., Stripe)"""
    # In a real implementation, this would integrate with Stripe or another payment processor
    # For now, we'll simulate a successful payment
    
    try:
        # Log the payment attempt
        logging.info(f"Processing credit card payment for invoice {invoice_number}: €{amount:.2f}")
        
        # Placeholder for Stripe integration
        # If Stripe API key is configured, we could implement actual payment processing
        stripe_api_key = config.get('Stripe', 'api_key', fallback=None)
        
        if stripe_api_key:
            logging.info("Stripe API key is configured, but integration is not implemented yet")
            # In a real implementation, we would call the Stripe API to process the payment
            # For example:
            # import stripe
            # stripe.api_key = stripe_api_key
            # payment = stripe.PaymentIntent.create(
            #     amount=int(amount * 100),  # Convert to cents
            #     currency='eur',
            #     description=f"Invoice {invoice_number}",
            #     customer=payment_details.stripe_customer_id,
            #     payment_method=payment_details.stripe_payment_method_id,
            #     confirm=True,
            # )
            # return {'success': payment.status == 'succeeded'}
        
        # For testing/demo purposes, always return success
        return {'success': True, 'transaction_id': f"SIMULATED-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"}
        
    except Exception as e:
        logging.error(f"Error processing credit card payment: {str(e)}")
        return {'success': False, 'error': str(e)}


def process_bank_transfer(payment_details, amount, invoice_number):
    """Process bank transfer (this typically requires manual handling)"""
    # Bank transfers typically require manual handling or integration with banking APIs
    # For now, we'll just log that a bank transfer is required
    
    try:
        logging.info(f"Bank transfer required for invoice {invoice_number}: €{amount:.2f}")
        
        # In a real implementation, this might generate a PDF with bank transfer details
        # or integrate with a banking API to initiate a transfer request
        
        # For testing/demo purposes, mark as "pending" since bank transfers need manual processing
        return {'success': False, 'pending': True, 'message': 'Bank transfer pending manual processing'}
        
    except Exception as e:
        logging.error(f"Error processing bank transfer request: {str(e)}")
        return {'success': False, 'error': str(e)}


def process_direct_debit(payment_details, amount, invoice_number):
    """Process direct debit payment using a banking API"""
    # Direct debits typically require integration with banking APIs
    # For now, we'll simulate a successful direct debit
    
    try:
        logging.info(f"Processing direct debit for invoice {invoice_number}: €{amount:.2f}")
        
        # Placeholder for direct debit API integration
        # In a real implementation, this would integrate with a banking API
        
        # For testing/demo purposes, always return success
        return {'success': True, 'transaction_id': f"DD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"}
        
    except Exception as e:
        logging.error(f"Error processing direct debit: {str(e)}")
        return {'success': False, 'error': str(e)}
