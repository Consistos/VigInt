"""Invoice generation and email functionality for Vigint billing system"""

import logging
import os
import smtplib
import requests
import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import csv
import io
import base64


def generate_invoice_html(client_name, client_email, invoice_number, start_date, end_date, usage_data):
    """Generate HTML invoice content"""
    
    total_cost = usage_data.get('total_cost', 0.0)
    request_count = usage_data.get('request_count', 0)
    usage_details = usage_data.get('usage_details', [])
    
    # Calculate VAT (assuming 21% VAT rate)
    vat_rate = 0.21
    subtotal = total_cost / (1 + vat_rate)
    vat_amount = total_cost - subtotal
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Invoice {invoice_number}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .company-info {{ margin-bottom: 30px; }}
            .invoice-info {{ margin-bottom: 30px; }}
            .client-info {{ margin-bottom: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .total-row {{ font-weight: bold; background-color: #f9f9f9; }}
            .footer {{ margin-top: 40px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>INVOICE</h1>
            <h2>Vigint API Services</h2>
        </div>
        
        <div class="company-info">
            <strong>Vigint Technologies</strong><br>
            API Services Division<br>
            Email: billing@vigint.com<br>
            Website: https://vigint.com
        </div>
        
        <div class="invoice-info">
            <table style="width: 50%;">
                <tr>
                    <td><strong>Invoice Number:</strong></td>
                    <td>{invoice_number}</td>
                </tr>
                <tr>
                    <td><strong>Invoice Date:</strong></td>
                    <td>{datetime.now().strftime('%Y-%m-%d')}</td>
                </tr>
                <tr>
                    <td><strong>Billing Period:</strong></td>
                    <td>{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</td>
                </tr>
            </table>
        </div>
        
        <div class="client-info">
            <strong>Bill To:</strong><br>
            {client_name}<br>
            {client_email}
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Quantity</th>
                    <th>Unit Price</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Add usage details
    for detail in usage_details:
        service_name = detail.get('service', 'API Call')
        count = detail.get('count', 0)
        cost = detail.get('cost', 0.0)
        unit_price = cost / count if count > 0 else 0.0
        
        html_content += f"""
                <tr>
                    <td>{service_name}</td>
                    <td>{count}</td>
                    <td>€{unit_price:.4f}</td>
                    <td>€{cost:.2f}</td>
                </tr>
        """
    
    html_content += f"""
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="3"><strong>Subtotal (excl. VAT)</strong></td>
                    <td><strong>€{subtotal:.2f}</strong></td>
                </tr>
                <tr>
                    <td colspan="3"><strong>VAT (21%)</strong></td>
                    <td><strong>€{vat_amount:.2f}</strong></td>
                </tr>
                <tr class="total-row">
                    <td colspan="3"><strong>Total Amount</strong></td>
                    <td><strong>€{total_cost:.2f}</strong></td>
                </tr>
            </tfoot>
        </table>
        
        <div class="footer">
            <p><strong>Payment Terms:</strong> Payment due within 30 days of invoice date.</p>
            <p><strong>Total API Requests:</strong> {request_count:,}</p>
            <p>Thank you for using Vigint API Services!</p>
        </div>
    </body>
    </html>
    """
    
    return html_content


def generate_invoice_csv(client_name, client_email, invoice_number, start_date, end_date, usage_data):
    """Generate CSV invoice data"""
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header information
    writer.writerow(['Invoice Number', invoice_number])
    writer.writerow(['Client Name', client_name])
    writer.writerow(['Client Email', client_email])
    writer.writerow(['Billing Period', f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"])
    writer.writerow(['Invoice Date', datetime.now().strftime('%Y-%m-%d')])
    writer.writerow([])  # Empty row
    
    # Usage details header
    writer.writerow(['Service', 'Quantity', 'Unit Price (EUR)', 'Total (EUR)'])
    
    total_cost = usage_data.get('total_cost', 0.0)
    usage_details = usage_data.get('usage_details', [])
    
    # Add usage details
    for detail in usage_details:
        service_name = detail.get('service', 'API Call')
        count = detail.get('count', 0)
        cost = detail.get('cost', 0.0)
        unit_price = cost / count if count > 0 else 0.0
        
        writer.writerow([service_name, count, f"{unit_price:.4f}", f"{cost:.2f}"])
    
    # Calculate VAT
    vat_rate = 0.21
    subtotal = total_cost / (1 + vat_rate)
    vat_amount = total_cost - subtotal
    
    # Totals
    writer.writerow([])  # Empty row
    writer.writerow(['Subtotal (excl. VAT)', '', '', f"{subtotal:.2f}"])
    writer.writerow(['VAT (21%)', '', '', f"{vat_amount:.2f}"])
    writer.writerow(['Total Amount', '', '', f"{total_cost:.2f}"])
    
    csv_content = output.getvalue()
    output.close()
    
    return csv_content


def send_invoice_email(config, client_name, client_email, invoice_number, start_date, end_date, usage_data, invoice_html, invoice_csv, payment_status="Paid"):
    """Send invoice email to client"""
    
    try:
        # Email configuration
        smtp_server = config.get('Email', 'smtp_server', fallback='smtp.gmail.com')
        smtp_port = config.getint('Email', 'smtp_port', fallback=587)
        sender_email = config.get('Email', 'sender_email', fallback='billing@vigint.com')
        sender_password = config.get('Email', 'sender_password', fallback='')
        
        if not sender_password:
            logging.warning("No email password configured, skipping email send")
            return {'success': False, 'error': 'No email password configured'}
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = client_email
        msg['Subject'] = f"Invoice {invoice_number} - Vigint API Services"
        
        # Email body
        total_cost = usage_data.get('total_cost', 0.0)
        request_count = usage_data.get('request_count', 0)
        
        text_body = f"""
Dear {client_name},

Thank you for using Vigint API Services. Please find your invoice details below:

Invoice Number: {invoice_number}
Billing Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
Total API Requests: {request_count:,}
Total Amount: €{total_cost:.2f}
Payment Status: {payment_status}

The detailed invoice is attached as both HTML and CSV files.

If you have any questions about this invoice, please contact our billing department.

Best regards,
Vigint Billing Team
billing@vigint.com
        """
        
        # Attach text and HTML parts
        text_part = MIMEText(text_body, 'plain')
        html_part = MIMEText(invoice_html, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Attach HTML invoice
        html_attachment = MIMEBase('application', 'octet-stream')
        html_attachment.set_payload(invoice_html.encode('utf-8'))
        encoders.encode_base64(html_attachment)
        html_attachment.add_header(
            'Content-Disposition',
            f'attachment; filename="invoice_{invoice_number}.html"'
        )
        msg.attach(html_attachment)
        
        # Attach CSV invoice
        csv_attachment = MIMEBase('application', 'octet-stream')
        csv_attachment.set_payload(invoice_csv.encode('utf-8'))
        encoders.encode_base64(csv_attachment)
        csv_attachment.add_header(
            'Content-Disposition',
            f'attachment; filename="invoice_{invoice_number}.csv"'
        )
        msg.attach(csv_attachment)
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Invoice email sent successfully to {client_email}")
        return {'success': True}
        
    except Exception as e:
        logging.error(f"Error sending invoice email: {str(e)}")
        return {'success': False, 'error': str(e)}


def create_qonto_invoice(config, client_name, client_email, usage_data, invoice_number, start_date, end_date):
    """Create invoice in Qonto banking system"""
    
    try:
        # Qonto API configuration
        qonto_api_key = config.get('Qonto', 'api_key', fallback=None)
        qonto_organization_slug = config.get('Qonto', 'organization_slug', fallback=None)
        
        if not qonto_api_key or not qonto_organization_slug:
            logging.warning("Qonto API credentials not configured")
            return {'success': False, 'error': 'Qonto API credentials not configured'}
        
        # Prepare invoice data
        total_cost = usage_data.get('total_cost', 0.0)
        usage_details = usage_data.get('usage_details', [])
        
        # Calculate VAT
        vat_rate = 0.21
        subtotal = total_cost / (1 + vat_rate)
        vat_amount = total_cost - subtotal
        
        # Prepare line items
        line_items = []
        for detail in usage_details:
            service_name = detail.get('service', 'API Call')
            count = detail.get('count', 0)
            cost = detail.get('cost', 0.0)
            unit_price = cost / count if count > 0 else 0.0
            
            line_items.append({
                'description': service_name,
                'quantity': count,
                'unit_price': round(unit_price * 100),  # Qonto expects cents
                'vat_rate': vat_rate
            })
        
        # Qonto API request
        headers = {
            'Authorization': f'Bearer {qonto_api_key}',
            'Content-Type': 'application/json'
        }
        
        invoice_data = {
            'invoice': {
                'external_id': invoice_number,
                'invoice_number': invoice_number,
                'issued_at': datetime.now().isoformat(),
                'due_at': (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).isoformat(),  # Next month
                'customer': {
                    'name': client_name,
                    'email': client_email
                },
                'line_items': line_items,
                'currency': 'EUR'
            }
        }
        
        response = requests.post(
            f'https://thirdparty.qonto.com/v2/{qonto_organization_slug}/invoices',
            headers=headers,
            json=invoice_data,
            timeout=30
        )
        
        if response.status_code == 201:
            logging.info(f"Qonto invoice created successfully: {invoice_number}")
            return {'success': True, 'qonto_invoice_id': response.json().get('invoice', {}).get('id')}
        else:
            logging.error(f"Qonto API error: {response.status_code} - {response.text}")
            return {'success': False, 'error': f"Qonto API error: {response.status_code}"}
            
    except Exception as e:
        logging.error(f"Error creating Qonto invoice: {str(e)}")
        return {'success': False, 'error': str(e)}